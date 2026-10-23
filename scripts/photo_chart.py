"""照片 → 拼豆图纸（忠实还原，不是原创）。

和 `pindou-original` 的原创流程分工不同：
- 原创：只学风格，画面由代码从零画，不还原具体的人/物；
- 本脚本：**忠实还原**用户给的这一张图（人脸、宠物、照片），是"照图转图纸"。

流程：抠背景 → 裁到主体 → 面积平均降采样到 52/78 格 → k-means 选色 →
每个色心映射到真实 MARD 色号（CIEDE2000）→ 出网格 + 色号图 + 效果图 + 像素原画。

用法：
    python scripts/photo_chart.py 照片.jpg --out out/宝宝 --width 52 --colors 14
    python scripts/photo_chart.py 照片.jpg --out out/x --no-cutout      # 保留原背景
"""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pindou import analyze, beadify, chartkit, palette  # noqa: E402


def enhance(a, contrast=1.0, sat=1.0):
    """自动对比拉伸 + 饱和度微调：手机暗光照直接转图纸会糊成灰。"""
    out = a.copy()
    lum = out @ np.array([0.299, 0.587, 0.114], np.float32)
    lo, hi = np.percentile(lum, 2), np.percentile(lum, 98)
    if hi - lo > 8:
        out = (out - lo) * (255.0 / (hi - lo)) * contrast + (255 - 255 * contrast) / 2
    if sat != 1.0:
        g = out @ np.array([0.299, 0.587, 0.114], np.float32)
        out = g[..., None] + (out - g[..., None]) * sat
    return np.clip(out, 0, 255)


def load_rgb(path, max_side=1400):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    s = max_side / max(w, h)
    if s < 1:
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    return np.asarray(im).astype(np.float32)


def cutout(a, tol=14, bg_clusters=4, ellipse=True):
    """抠背景：外圈像素聚成几簇（墙、地面、光斑），和任一簇接近就算背景；
    再从边缘漫水填充，只保留最大的主体块，最后用居中椭圆先验去掉地上的阴影。"""
    h, w = a.shape[:2]
    band = max(3, int(min(h, w) * 0.02))
    outer = np.concatenate([a[:band].reshape(-1, 3), a[-band:].reshape(-1, 3),
                            a[:, :band].reshape(-1, 3), a[:, -band:].reshape(-1, 3)])
    C, _ = analyze.kmeans(outer, bg_clusters)
    d = np.min(np.abs(a[:, :, None, :] - C[None, None, :, :]).sum(-1), axis=2)
    near = d < tol * 3
    lab, n = ndimage.label(near)
    edge_ids = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    edge_ids.discard(0)
    subj = ~np.isin(lab, list(edge_ids))
    subj = ndimage.binary_opening(subj, np.ones((3, 3), bool))
    subj = ndimage.binary_closing(subj, np.ones((7, 7), bool))
    subj = ndimage.binary_fill_holes(subj)
    lab2, n2 = ndimage.label(subj)
    if n2 > 1:
        sizes = ndimage.sum(subj, lab2, range(1, n2 + 1))
        subj = lab2 == (int(np.argmax(sizes)) + 1)
    if ellipse:
        yy, xx = np.mgrid[0:h, 0:w]
        ell = (((xx - w / 2) / (w * 0.54)) ** 2 + ((yy - h * 0.53) / (h * 0.56)) ** 2) <= 1.0
        subj &= ell
    return subj, C[0]


def crop_to_subject(a, mask, pad=0.06):
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return a, mask
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
    half = max(y1 - y0, x1 - x0) * (0.5 + pad)
    y0 = int(max(0, cy - half)); y1 = int(min(a.shape[0], cy + half))
    x0 = int(max(0, cx - half)); x1 = int(min(a.shape[1], cx + half))
    return a[y0:y1, x0:x1], mask[y0:y1, x0:x1]


def downsample(a, mask, gw):
    """面积平均降采样；主体外的格子记为空。"""
    h, w = a.shape[:2]
    gh = max(1, int(round(gw * h / w)))
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    m = Image.fromarray((mask * 255).astype(np.uint8))
    small = np.asarray(img.resize((gw, gh), Image.BOX)).astype(np.float32)
    cover = np.asarray(m.resize((gw, gh), Image.BOX)).astype(np.float32) / 255.0
    return small, cover


def pick_palette(rgb, cover, codes, k=14, seed=0, min_share=0.004):
    """在主体像素上做 k-means，再把每个色心映射到真实色号。"""
    px = rgb[cover > 0.5]
    if len(px) < k:
        px = rgb.reshape(-1, 3)
    idx = np.random.default_rng(seed).choice(len(px), min(20000, len(px)), replace=False)
    C, w = analyze.kmeans(px[idx], k)
    order = np.argsort(-w)
    C, w = C[order], w[order]
    card = palette.card()
    chosen = []
    for c, share in zip(C, w):
        if share < min_share and chosen:
            continue
        code, de = palette.nearest(tuple(int(v) for v in np.clip(c, 0, 255)), codes)
        if code not in [x[0] for x in chosen]:
            chosen.append((code, share, de))
    return chosen


def to_grid(rgb, cover, chosen, white_code):
    """每格按最近的色心落色号。"""
    card = palette.card()
    centers = np.array([card[c]['rgb'] for c, _, _ in chosen], np.float32)
    h, w = rgb.shape[:2]
    flat = rgb.reshape(-1, 3)
    d = ((flat[:, None, :] - centers[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1).reshape(h, w)
    g = np.zeros((h, w), np.int8)
    for i in range(len(chosen)):
        g[lab == i] = i + 1
    g[cover <= 0.5] = 0
    return g


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('image')
    ap.add_argument('--out', required=True)
    ap.add_argument('--width', type=int, default=52, help='网格宽（52=1块板，78=4块板）')
    ap.add_argument('--colors', type=int, default=14)
    ap.add_argument('--color-set', default='mard72')
    ap.add_argument('--no-cutout', action='store_true')
    ap.add_argument('--crop', default='', help='手动取景 x0,y0,x1,y1（0–1 相对坐标）')
    ap.add_argument('--tol', type=float, default=14, help='抠图容差（越小越保守）')
    ap.add_argument('--bg', default='flat', choices=['flat', 'keep'])
    ap.add_argument('--contrast', type=float, default=1.08)
    ap.add_argument('--sat', type=float, default=1.12)
    ap.add_argument('--title', default='')
    ap.add_argument('--cs', type=int, default=30)
    ap.add_argument('--seed', type=int, default=0)
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    rgb = load_rgb(a.image)
    if a.crop:
        x0, y0, x1, y1 = [float(v) for v in a.crop.split(',')]
        h, w = rgb.shape[:2]
        rgb = rgb[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    rgb = enhance(rgb, contrast=a.contrast, sat=a.sat)
    mask = np.ones(rgb.shape[:2], bool)
    if not a.no_cutout:
        m2, _ = cutout(rgb, tol=a.tol)
        share = float(m2.mean())
        if 0.12 < share < 0.92:                 # 抠得像才用，否则保留背景
            mask = m2
    rgb, mask = crop_to_subject(rgb, mask, pad=0.02 if a.no_cutout else 0.06)
    if not a.no_cutout and mask.mean() < 0.999 and a.bg == 'flat':
        bgc = np.array([246, 243, 238], np.float32)   # 奶白底，主体更突出
        rgb = np.where(mask[..., None], rgb, bgc)
    small, cover = downsample(rgb, mask, a.width)
    codes = palette.resolve_set(a.color_set)
    chosen = pick_palette(small, cover, codes, k=a.colors, seed=a.seed)
    white_code = palette.nearest('#FFFFFF', codes)[0]
    g = to_grid(small, cover, chosen, white_code)

    pal = palette.Palette.from_codes([c for c, _, _ in chosen] + [white_code])
    # 让网格索引和 Palette 对齐
    remap = np.zeros(32, np.int8)
    for i, (code, _, _) in enumerate(chosen):
        remap[i + 1] = pal.index_of_code(code)
    g = remap[g]
    g = beadify.finalize(g, border=1, close=1, min_island=12, hole=8,
                         white=pal.index_of_code(white_code))

    pat = chartkit.Pattern(g, pal)
    meta = dict(Title=a.title or os.path.basename(a.image), Author='拼豆原创工坊',
                Description=f'照片转图纸 · {pat.total} 颗 {pat.ncol} 色',
                CreationTime=__import__('time').strftime('%Y-%m-%d %H:%M:%S'))
    name = a.title or os.path.splitext(os.path.basename(a.image))[0]
    chartkit.color_chart(pat, os.path.join(a.out, f'{name}_色号图.png'), meta, CS=a.cs,
                         title=name,
                         subtitle=f'照片转图纸 · {g.shape[1]}×{g.shape[0]} · {pat.ncol} 色 / {pat.total} 颗',
                         footer=['按图还原：由照片量化而成，非原创设计，商用请确认肖像授权',
                                 '图纸仅供个人手工制作'],
                         legend_note='红实线 = 每 10 格   灰虚线 = 每 5 格   格内为色号   空白格不放豆')
    chartkit.bead_mockup(pat, os.path.join(a.out, f'{name}_效果图.png'), meta, B=14, title=name)
    # 像素原画：网格色块放大
    B = 14
    art = np.zeros((g.shape[0] * B, g.shape[1] * B, 3), np.uint8)
    for i in range(len(pal)):
        m = np.kron((g == i).astype(np.uint8), np.ones((B, B), np.uint8)).astype(bool)
        art[m] = pal.tone_rgb(i) if i else (255, 255, 255)
    Image.fromarray(art).save(os.path.join(a.out, f'{name}_像素原画.png'))

    rows = ['# 作品：' + name,
            f'# 来源：照片转图纸 {a.image}  网格 {g.shape[1]}x{g.shape[0]}',
            '# 图例：. = 不放豆   ' + ' '.join(f'{pal.code(r)}' for r in pal.used())]
    ch = {pal.index_of_code(pal.code(r)): chr(65 + i) for i, r in enumerate(pal.used())}
    for row in g:
        rows.append(''.join(ch.get(int(v), '.') for v in row))
    open(os.path.join(a.out, f'{name}_网格.txt'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')

    info = dict(image=os.path.abspath(a.image), grid=[int(g.shape[1]), int(g.shape[0])],
                beads=pat.total, colors=pat.ncol, palette=[dict(code=c, share=round(float(s), 3),
                dE=round(float(de), 2)) for c, s, de in chosen], color_set=a.color_set,
                cutout=not a.no_cutout)
    open(os.path.join(a.out, f'{name}_信息.json'), 'w', encoding='utf-8').write(
        json.dumps(info, ensure_ascii=False, indent=2))
    print(f'{name}: {g.shape[1]}×{g.shape[0]}  {pat.ncol} 色  {pat.total} 颗  → {a.out}')
    for c, s, de in chosen:
        print(f'  {c}  {palette.card()[c]["hex"]}  占比 {s*100:4.1f}%  ΔE {de:.1f}')
    return info


if __name__ == '__main__':
    main()
