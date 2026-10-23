"""参考图 → 风格 DNA：只统计"规律"，不取任何像素进交付物。

量化的东西：主色与占比、明暗分布、饱和度、对比度、边缘密度与线宽、对称性、画幅比例、
背景是否铺满、直接缩成 52 格时的糊格率、推荐的纹理与画幅配比、以及一套可直接用的配色角色。
"""
import json
import copy
import hashlib
import os
import re
from collections import Counter

import numpy as np
from PIL import Image, ImageOps

from . import palette

EXTS = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff')


def _image_rgb(path):
    """按查看器方向读取，并把透明区域合成到白纸上；退出后关闭源文件。"""
    with Image.open(path) as source:
        im = ImageOps.exif_transpose(source).convert('RGBA')
        paper = Image.new('RGBA', im.size, (255, 255, 255, 255))
        return Image.alpha_composite(paper, im).convert('RGB')


def _sample_rgb(im, maxside=640):
    if isinstance(maxside, bool) or not isinstance(maxside, (int, np.integer)) or maxside < 1:
        raise ValueError('分析采样边长必须是正整数')
    w, h = im.size
    s = maxside / max(w, h)
    if s < 1:
        im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.BOX)
    return np.asarray(im).astype(np.float32)


def _load(path, maxside=640):
    return _sample_rgb(_image_rgb(path), maxside)


def scan_images(refs_dir, transform=None):
    """稳定扫描可见图像；仅返回文件名标识，不把本地目录写进结果。"""
    exists = bool(refs_dir is not None and os.path.isdir(refs_dir))
    files = []
    if exists:
        for root, dirs, names in os.walk(refs_dir):
            dirs.sort(key=lambda s: (s.casefold(), s))
            files.extend(os.path.join(root, n) for n in names if n.lower().endswith(EXTS))
        files.sort(key=lambda p: (os.path.relpath(p, refs_dir).replace('\\', '/').casefold(),
                                  os.path.relpath(p, refs_dir).replace('\\', '/')))
    totals = Counter(os.path.basename(p).casefold() for p in files)
    used = Counter()
    images, seen = [], {}
    scan = dict(requested=refs_dir is not None, exists=exists, discovered_count=len(files),
                loaded_count=0, failed_count=0, duplicates_count=0, failures=[], duplicates=[])
    for path in files:
        name = os.path.basename(path)
        used[name.casefold()] += 1
        label = f'{name} [{used[name.casefold()]}]' if totals[name.casefold()] > 1 else name
        try:
            im = _image_rgb(path)
            fingerprint = hashlib.sha256(str(im.size).encode('ascii') + im.tobytes()).hexdigest()
            if fingerprint in seen:
                scan['duplicates'].append(dict(file=label, duplicate_of=seen[fingerprint]))
                scan['duplicates_count'] += 1
                continue
            seen[fingerprint] = label
            images.append((label, transform(im, label) if transform else im))
        except (OSError, ValueError, Image.DecompressionBombError) as exc:
            # Pillow 的原始异常可能带绝对路径，报告只保留错误类别。
            scan['failures'].append(dict(file=label, error=type(exc).__name__))
            scan['failed_count'] += 1
    scan['loaded_count'] = len(images)
    return images, scan


def _lum(a):
    return 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]


def _sat(a):
    mx = a.max(-1)
    mn = a.min(-1)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)


def kmeans(X, k=8, iters=14, seed=0):
    try:
        X = np.asarray(X, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError('主色样本必须是RGB数值矩阵') from exc
    if X.ndim != 2 or X.shape[1] != 3 or not len(X) or not np.isfinite(X).all() or np.any((X < 0) | (X > 255)):
        raise ValueError('主色样本必须是非空、有限且在0到255内的RGB矩阵')
    for key, value, lower in (('k', k, 1), ('iters', iters, 1), ('seed', seed, 0)):
        if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < lower:
            raise ValueError(f'{key}必须是至少为{lower}的整数')
    rng = np.random.default_rng(seed)
    X, counts = np.unique(X, axis=0, return_counts=True)
    C = X[rng.choice(len(X), min(k, len(X)), replace=False, p=counts / counts.sum())].copy()
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        lab = d.argmin(1)
        for i in range(len(C)):
            m = lab == i
            if m.any():
                C[i] = np.average(X[m], axis=0, weights=counts[m])
    d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    w = np.bincount(lab, weights=counts, minlength=len(C)).astype(float)
    active = w > 0
    return C[active], w[active] / w.sum()


def _edges(a):
    L = _lum(a)
    gx = np.zeros_like(L)
    gy = np.zeros_like(L)
    gx[:, 1:-1] = L[:, 2:] - L[:, :-2]
    gy[1:-1, :] = L[2:, :] - L[:-2, :]
    if L.shape[1] > 1:
        gx[:, 0] = L[:, 1] - L[:, 0]
        gx[:, -1] = L[:, -1] - L[:, -2]
    if L.shape[0] > 1:
        gy[0, :] = L[1, :] - L[0, :]
        gy[-1, :] = L[-1, :] - L[-2, :]
    g = np.hypot(gx, gy)
    return g


def analyze_image(path):
    return _analyze_rgb(_image_rgb(path), os.path.basename(path))


def _analyze_rgb(im, filename):
    original_w, original_h = im.size
    a = _sample_rgb(im)
    H, W = a.shape[:2]
    L = _lum(a)
    S = _sat(a)
    g = _edges(a)
    # 边缘密度用"相对对比度的固定阈值"，不能按分位数取（那样永远等于分位比例）
    hi = float(np.percentile(g, 99.5))
    thr = max(12.0, 0.30 * hi)
    strong = g > thr
    edge_density = float(strong.mean())
    # 线宽估计：边缘像素到非边缘的平均距离 × 2
    if strong.any():
        from scipy import ndimage
        d = ndimage.distance_transform_edt(strong)
        line_w = float(np.clip(np.percentile(d[strong], 60) * 2.0, 0.8, 4.0))
    else:
        line_w = 1.0
    # 主色
    px = a.reshape(-1, 3)
    idx = np.random.default_rng(0).choice(len(px), min(40000, len(px)), replace=False)
    C, w = kmeans(px[idx], 8)
    order = sorted(range(len(w)), key=lambda i: (-w[i], *C[i]))
    C, w = C[order], w[order]
    cols = [dict(rgb=[int(v) for v in c], hex='#%02X%02X%02X' % tuple(int(v) for v in c), share=round(float(ww), 4))
            for c, ww in zip(C, w)]
    # 明暗分布（5 档）
    tones = np.histogram(L, bins=[0, 60, 110, 160, 215, 256], weights=None)[0] / L.size
    # 背景：四边像素的中位色，以及"背景是否铺满"
    border_mask = np.zeros((H, W), dtype=bool)
    border_mask[[0, -1], :] = True
    border_mask[:, [0, -1]] = True
    border = a[border_mask]
    bg = np.median(border, 0)
    bg_share = float((np.abs(a - bg).sum(-1) < 40).mean())
    # 对称性
    Lm = L[:, ::-1]
    x, y = L.astype(np.float64).ravel(), Lm.astype(np.float64).ravel()
    x, y = x - x.mean(), y - y.mean()
    norm = np.linalg.norm(x) * np.linalg.norm(y)
    sym = float(np.clip(np.dot(x, y) / norm, -1, 1)) if norm > 0 else 1.0
    # 缩成 52 格后的糊格率（"直接缩图"会烂掉多少格）
    small = Image.fromarray(a.astype(np.uint8)).resize((52, max(1, min(4096, int(52 * H / W)))), Image.BOX)
    sL = _lum(np.asarray(small).astype(np.float32))
    q = np.round(sL / 42.5) * 42.5
    from scipy.ndimage import maximum_filter, minimum_filter
    rng_local = np.maximum(maximum_filter(q, size=3, mode='nearest') - q,
                           q - minimum_filter(q, size=3, mode='nearest'))
    mud = float(((rng_local > 45) & (q > 60) & (q < 210)).mean())
    flat = bool(L.std() < 1.5)                 # 纯色图：没有可学的规律
    tiny = bool(min(original_w, original_h) < 32)
    return dict(file=filename, size=[original_w, original_h], analysis_size=[W, H], flat=flat, tiny=tiny,
                aspect=round(original_w / original_h, 3),
                saturation=round(float(S.mean()), 3), contrast=round(float(L.std() / 128), 3),
                colorfulness=round(float(S.std()), 3), edge_density=round(edge_density, 4),
                line_weight=round(line_w, 2), symmetry=round(max(0.0, sym), 3),
                tones=[round(float(t), 3) for t in tones],
                dark_ratio=round(float((L < 90).mean()), 3), light_ratio=round(float((L > 200).mean()), 3),
                bg=dict(hex='#%02X%02X%02X' % tuple(int(round(v)) for v in bg), share=round(bg_share, 3)),
                colors=cols, bead_mud=round(mud, 3))


def _hue(rgb):
    import colorsys
    h, s, v = colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])
    return h * 360.0, s


def _role_palette(colors, bg_hex, colorful=None):
    """分配角色。
    - 黑白稿（饱和低）：按亮度阶梯 line/dark/mid/light/white，缺档插值补；
    - 彩色稿（照片、插画）：按"面积 × 色相差异"挑 3 个真正不同的颜色，不要一路灰下去。"""
    lum = lambda c: (0.299 * c['rgb'][0] + 0.587 * c['rgb'][1] + 0.114 * c['rgb'][2]) / 255.0
    cs = [dict(c) for c in colors]
    if not cs:
        cs = [dict(rgb=[255, 255, 255], hex='#FFFFFF', share=1.0)]
    cs.sort(key=lum)
    if colorful is None:
        colorful = max((max(c['rgb']) - min(c['rgb']) for c in cs), default=0) > 45
    dark, light = cs[0], cs[-1]

    def synth(t):
        rgb = [int(round(dark['rgb'][i] + (light['rgb'][i] - dark['rgb'][i]) * t)) for i in range(3)]
        return dict(rgb=rgb, hex='#%02X%02X%02X' % tuple(rgb), share=0.02)

    pal, used = {}, set()
    if colorful:
        by_area = sorted(cs, key=lambda c: -c['share'])
        pal['line'] = dark['hex'] if lum(dark) < 0.25 else synth(0.06)['hex']
        used.add(pal['line'])
        pal['white'] = light['hex']
        used.add(pal['white'])
        picked = []
        for c in by_area:                       # 面积优先，同时要求色相拉开
            if c['hex'] in used or lum(c) < 0.10 or lum(c) > 0.95:
                continue
            h, s = _hue(c['rgb'])
            if all(min(abs(h - _hue(p['rgb'])[0]), 360 - abs(h - _hue(p['rgb'])[0])) > 22 for p in picked):
                picked.append(c)
            if len(picked) == 3:
                break
        while len(picked) < 3:                  # 色相不够就按亮度补
            picked.append(synth(0.3 + 0.3 * len(picked)))
        picked.sort(key=lum)
        pal['dark'], pal['mid'], pal['light'] = picked[0]['hex'], picked[1]['hex'], picked[2]['hex']
        vivid = max(cs, key=lambda c: (_hue(c['rgb'])[1], c['share']))
        if _hue(vivid['rgb'])[1] > 0.35 and vivid['hex'] not in (pal['line'], pal['white']):
            pal['accent'] = vivid['hex']
    else:
        for name, t in (('line', 0.04), ('dark', 0.22), ('mid', 0.48), ('light', 0.72), ('white', 0.97)):
            best = min(cs, key=lambda c: abs(lum(c) - t))
            c = best if abs(lum(best) - t) < 0.13 and best['hex'] not in used else synth(t)
            pal[name] = c['hex']
            used.add(c['hex'])
        vivid = sorted(cs, key=lambda c: -(max(c['rgb']) - min(c['rgb'])))
        if vivid and max(vivid[0]['rgb']) - min(vivid[0]['rgb']) > 40:
            pal['accent'] = vivid[0]['hex']
    pal['bg'] = bg_hex
    return pal


def _validated_dna(dna_list):
    """外部DNA也要先核对，避免NaN或缺字段被写成可用风格。"""
    data = copy.deepcopy(list(dna_list))
    for d in data:
        try:
            for key in ('saturation', 'contrast', 'edge_density', 'line_weight', 'symmetry',
                        'aspect', 'dark_ratio', 'light_ratio', 'bead_mud'):
                value = d[key]
                if isinstance(value, bool) or not np.isfinite(value) or value < 0:
                    raise ValueError(f'{key}必须是非负有限数值')
                if key in ('aspect', 'line_weight') and value <= 0:
                    raise ValueError(f'{key}必须大于0')
                if key in ('saturation', 'edge_density', 'symmetry', 'dark_ratio', 'light_ratio', 'bead_mud') and value > 1:
                    raise ValueError(f'{key}不能超过1')
            tones = np.asarray(d['tones'], dtype=float)
            if tones.shape != (5,) or not np.isfinite(tones).all() or np.any(tones < 0) or not np.isclose(tones.sum(), 1, atol=.01):
                raise ValueError('明暗分布必须是和为1的5档比例')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', d['bg']['hex']):
                raise ValueError('背景颜色不是六位十六进制颜色')
            bg_share = float(d['bg']['share'])
            if not np.isfinite(bg_share) or not 0 <= bg_share <= 1:
                raise ValueError('背景比例必须在0到1内')
            if not d['colors']:
                raise ValueError('主色列表不能为空')
            total_share = 0.0
            for c in d['colors']:
                rgb = np.asarray(c['rgb'], dtype=float)
                share = float(c['share'])
                if rgb.shape != (3,) or not np.isfinite(rgb).all() or np.any((rgb < 0) | (rgb > 255)):
                    raise ValueError('主色必须是0到255的RGB三元组')
                if not np.isfinite(share) or not 0 <= share <= 1:
                    raise ValueError('主色比例必须在0到1内')
                total_share += share
            if not 0 < total_share <= 1.01:
                raise ValueError('主色总比例必须大于0且不超过1')
        except (KeyError, TypeError, OverflowError) as exc:
            raise ValueError('参考图DNA缺字段或字段类型错误') from exc
    return data


def aggregate(dna_list, name=None):
    dna_list = _validated_dna(dna_list)
    if not dna_list:
        raise SystemExit('没有可分析的参考图')
    n = len(dna_list)
    med = lambda k: float(np.median([d[k] for d in dna_list]))
    aspects = [d['aspect'] for d in dna_list]
    sat, contrast, edge = med('saturation'), med('contrast'), med('edge_density')
    tones = np.mean([d['tones'] for d in dna_list], axis=0)
    # 汇总主色（按出现次数加权）
    bag = {}
    for d in dna_list:
        present = set()
        for c in d['colors']:
            k = tuple(int(v) // 12 for v in c['rgb'])
            if k not in bag:
                bag[k] = dict(rgb=np.zeros(3, np.float64), share=0.0, n=0)
            bag[k]['rgb'] += np.asarray(c['rgb']) * c['share']
            bag[k]['share'] += c['share']
            if k not in present and c['share'] > 0:
                bag[k]['n'] += 1
                present.add(k)
    colors = sorted((c for c in bag.values() if c['share'] > 0),
                    key=lambda c: (-(c['share'] * min(c['n'], 3)), *list(c['rgb'] / c['share'])))
    for c in colors:
        c['rgb'] = np.rint(c['rgb'] / c['share']).astype(int).tolist()
        c['hex'] = '#%02X%02X%02X' % tuple(int(v) for v in c['rgb'])
        c['share'] = round(c['share'] / n, 4)
    colors = colors[:8]
    bg_hex = max(colors, key=lambda c: c['share'])['hex'] if colors else '#FFFFFF'
    pal = _role_palette(colors, bg_hex)
    # 纹理推断
    if edge > 0.22:
        tex = 'hatch'
    elif edge > 0.12:
        tex = 'stipple'
    elif sat > 0.18:
        tex = 'gradient'                     # 照片/水彩：边缘柔和、颜色连续 → 用抖动渐变
    else:
        tex = 'solid'
    # 照片类（边缘柔和 + 有色）：整幅铺底更像照片，不留白边
    photo_like = bool(edge < 0.10 and sat > 0.15)
    # 画幅配比：竖图多 → V 多
    vert = sum(1 for a in aspects if a < 0.75)
    wide = sum(1 for a in aspects if a > 1.25)
    if vert > n / 2:
        formats = {'S': 0.25, 'M': 0.2, 'V': 0.55}
    elif wide > n / 2:
        formats = {'S': 0.6, 'M': 0.3, 'V': 0.1}
    else:
        formats = {'S': 0.4, 'M': 0.35, 'V': 0.25}
    bg_is_filled = float(np.median([d['bg']['share'] for d in dna_list])) > 0.45
    # 白/米色纸底不算"满底铺色"，只有深色或有色底才算
    bg_lum = float(np.mean([0.299 * int(d['bg']['hex'][1:3], 16) + 0.587 * int(d['bg']['hex'][3:5], 16)
                            + 0.114 * int(d['bg']['hex'][5:7], 16) for d in dna_list])) / 255.0
    bg_is_filled = bool((bg_is_filled and bg_lum < 0.86) or photo_like)
    out = dict(name=name or 'refs', count=n,
               saturation=round(float(sat), 3), contrast=round(float(contrast), 3),
               edge_density=round(float(edge), 4), line_weight=round(med('line_weight'), 2),
               symmetry=round(med('symmetry'), 3), aspect=round(float(np.median(aspects)), 3),
               dark_ratio=round(med('dark_ratio'), 3), light_ratio=round(med('light_ratio'), 3),
               tones=[round(float(t), 3) for t in tones],
               bead_mud=round(med('bead_mud'), 3), bg_is_filled=bool(bg_is_filled),
               photo_like=bool(photo_like),
               palette_roles=pal, colors=colors, texture=tex, formats=formats,
               subjects=None, images=dna_list)
    # 配色可用性：角色解析到真实色号，报告 ΔE
    try:
        from .stylepack import normalize
        p = palette.Palette.from_style(dict(palette=pal, color_set='mard72'))
        out['palette_resolved'] = p.to_dict()['report']
    except Exception:
        out['palette_resolved'] = []
    return out


def run(refs_dir, out_json=None, name=None, verbose=True):
    images, scan = scan_images(refs_dir, transform=_analyze_rgb)
    if not scan['discovered_count']:
        raise SystemExit(f'{refs_dir} 里没有图片（支持 {", ".join(EXTS)}）')
    dna, skipped, seen = [], [], set()
    for label, d in images:
        # 纯色 / 尺寸过小的图不参与统计（会把配色和纹理带偏）
        if d.get('flat'):
            skipped.append(dict(file=d['file'], reason='纯色图'))
            continue
        if d.get('tiny'):
            skipped.append(dict(file=d['file'], reason='尺寸过小'))
            continue
        sig = (tuple(d['size']), d['bead_mud'], d['saturation'], d['edge_density'], d['line_weight'])
        if sig in seen:                        # 同一张图放了两次，只算一次
            skipped.append(dict(file=d['file'], reason='重复'))
            continue
        seen.add(sig)
        dna.append(d)
        if verbose:
            print(f'  {d["file"]}: 饱和 {d["saturation"]} 对比 {d["contrast"]} 边缘 {d["edge_density"]} '
                  f'线宽 {d["line_weight"]} 糊格 {d["bead_mud"]}')
    if verbose:
        for failure in scan['failures']:
            print(f'  跳过 {failure["file"]}：{failure["error"]}')
        for item in skipped:
            print(f'  跳过 {item["file"]}：{item["reason"]}')
    if not dna:
        # 过滤太狠（全是小图或纯色）→ 退回用全部，宁可统计粗一点也不能没结果
        dna = [d for _, d in images]
        skipped = []
    if not dna:
        raise SystemExit(f'没有可用的参考图（{scan["failed_count"]} 张读取失败）')
    agg = aggregate(dna, name or os.path.basename(os.path.abspath(refs_dir)))
    agg['scan'] = scan
    agg['skipped'] = skipped
    if out_json:
        with open(out_json, 'w', encoding='utf-8') as f:
            json.dump(agg, f, ensure_ascii=False, indent=2, allow_nan=False)
    return agg
