"""原创性核查：和参考图比、款与款之间比。

方法（沿用墨纹项目的校准结论）
- 把成品网格换算成"墨量图"（按色号亮度），裁到内容包围盒，拉伸成 32×32；
- NCC：零均值单位向量的余弦相似度（镜像也算，取较大的）；
- dHash：9×8 差分哈希 64 位指纹，取汉明距离最小值（含镜像）；
- 参考图先转成"照搬版"（直接缩到 52 格 + 量化），两边在同一尺度上比。

判定：与任何参考图 NCC < 0.75 且 dHash ≥ 10；款与款之间 NCC < 0.92。
超过就重画，不许为了通过去调阈值。
"""
import json
import os
import html

import numpy as np
from PIL import Image

from .palette import PAPER

NCC_REF_MAX = 0.75
DHASH_REF_MIN = 10
NCC_PAIR_MAX = 0.92


def _positive_size(size):
    if isinstance(size, bool) or not isinstance(size, (int, np.integer)) or size < 1:
        raise ValueError('比较图边长必须是正整数')
    return int(size)


def _map_array(value, unit=False):
    raw = np.asarray(value)
    if raw.dtype.kind not in 'fiu':
        raise ValueError('墨量图必须是实数矩阵')
    a = raw.astype(np.float64)
    if a.ndim != 2 or not a.size or not np.isfinite(a).all():
        raise ValueError('墨量图必须是非空有限二维矩阵')
    if unit and np.any((a < 0) | (a > 1)):
        raise ValueError('墨量必须在0到1之间')
    return a


def ink_map(grid, pal, size=32):
    """网格 → 墨量图（0=空/白，1=最黑）。"""
    size = _positive_size(size)
    g = _map_array(grid)
    if np.any(g != np.floor(g)) or np.any((g < 0) | (g >= len(pal))):
        raise ValueError('网格必须使用色卡范围内的整数索引')
    ink = np.zeros(g.shape, np.float32)
    for i in range(1, len(pal)):
        rgb = np.asarray(pal.tone_rgb(i), dtype=float)
        if rgb.shape != (3,) or not np.isfinite(rgb).all() or np.any((rgb < 0) | (rgb > 255)):
            raise ValueError('色卡RGB必须是0到255的三元组')
        lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0
        ink[g == i] = float(np.clip(1.0 - lum, 0, 1))
    ys, xs = np.nonzero(g != PAPER)
    if len(xs) == 0:
        return np.zeros((size, size), np.float32)
    crop = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    im = Image.fromarray((crop * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR)
    return np.asarray(im).astype(np.float32) / 255.0


def ncc(a, b):
    """含镜像的最大 NCC。"""
    a, b = _map_array(a), _map_array(b)
    if a.shape != b.shape:
        raise ValueError('比较的墨量图尺寸必须相同')

    def one(x, y):
        # 先按绝对幅值缩放，再转零均值，避免float32平方溢出。
        same = np.array_equal(x, y)
        x = x / max(float(np.max(np.abs(x))), 1.0)
        y = y / max(float(np.max(np.abs(y))), 1.0)
        x = x - x.mean()
        y = y - y.mean()
        d = np.linalg.norm(x) * np.linalg.norm(y)
        if d == 0:
            # 两个相同常量也是重复作品；不同常量仍无结构相关性。
            return 1.0 if same else 0.0
        return float(np.clip(np.dot(x.ravel(), y.ravel()) / d, -1, 1))
    return max(one(a, b), one(a, b[:, ::-1]))


def dhash(a, size=8):
    a = _map_array(a, unit=True)
    size = _positive_size(size)
    im = Image.fromarray((a * 255).astype(np.uint8)).resize((size + 1, size), Image.BILINEAR)
    x = np.asarray(im).astype(np.int16)
    bits = (x[:, 1:] > x[:, :-1]).ravel()
    return int(''.join('1' if v else '0' for v in bits), 2)


def ham(a, b):
    return bin(a ^ b).count('1')


def dhash_min(a, b):
    a, b = _map_array(a, unit=True), _map_array(b, unit=True)
    return min(ham(dhash(a), dhash(b)), ham(dhash(a), dhash(b[:, ::-1])))


def naive_bead(path, size=32):
    """参考图"照搬版"：直接缩到 52 格再量化 —— 如果抄，就长这样。"""
    from .analyze import _image_rgb
    return _naive_rgb(_image_rgb(path), size)


def _naive_rgb(im, size=32):
    size = _positive_size(size)
    w, h = im.size
    nw = 52
    nh = max(1, min(4096, int(round(52 * h / w))))
    small = im.resize((nw, nh), Image.BOX)
    a = np.asarray(small).astype(np.float32)
    lum = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) / 255.0
    q = np.round(lum * 4) / 4.0
    return np.asarray(Image.fromarray(((1 - q) * 255).astype(np.uint8)).resize((size, size), Image.BILINEAR),
                      np.float32) / 255.0


def refs_maps(refs_dir):
    return _refs_maps_with_scan(refs_dir)[0]


def _refs_maps_with_scan(refs_dir):
    from .analyze import scan_images
    return scan_images(refs_dir, transform=lambda im, label: _naive_rgb(im))


def _too_similar(ncc_v, dh):
    """判定"太像"：NCC 高，或者 dHash 很近且 NCC 已经偏高。
    单看 dHash 会误报：拼豆图很稀疏，两件完全不同的作品也可能落在同一档哈希上。"""
    return ncc_v >= NCC_REF_MAX or (dh < DHASH_REF_MIN and ncc_v >= 0.60)


def check(designs, refs_dir=None):
    """designs: [(id, grid, pal)]；返回报告 dict。"""
    designs = list(designs)
    if not designs:
        raise ValueError('至少需要一款作品才能核查')
    maps, ids = [], set()
    for did, grid, pal in designs:
        if not isinstance(did, str) or not did.strip() or did in ids:
            raise ValueError('作品编号必须是非空且不重复的字符串')
        m = ink_map(grid, pal)
        if not np.any(np.asarray(grid) != PAPER):
            raise ValueError('空白作品不能进行原创性核查')
        ids.add(did)
        maps.append((did, m))
    refs, scan = _refs_maps_with_scan(refs_dir)
    rows = []
    worst_ref = None
    min_dh = None
    bad = []
    for did, m in maps:
        best = None
        closest_hash = None
        hit = None
        for rn, rm in refs:
            v = ncc(m, rm)
            dh = dhash_min(m, rm)
            if best is None or v > best[1]:
                best = (rn, v, dh)
            if closest_hash is None or dh < closest_hash[2]:
                closest_hash = (rn, v, dh)
            if _too_similar(v, dh) and (hit is None or v > hit[1]):
                hit = (rn, v, dh)
        if refs:
            worst_ref = best[1] if worst_ref is None else max(worst_ref, best[1])
            min_dh = closest_hash[2] if min_dh is None else min(min_dh, closest_hash[2])
            if hit:
                bad.append(dict(id=did, ref=hit[0], ncc=round(hit[1], 3), dhash=hit[2]))
        rows.append(dict(id=did, nearest_ref=best[0] if best else None,
                         ncc=round(best[1], 3) if best else None, dhash=best[2] if best else None,
                         min_dhash=closest_hash[2] if closest_hash else None,
                         nearest_hash_ref=closest_hash[0] if closest_hash else None))
    pairs = []
    worst_pair = (None, None, None)
    for i in range(len(maps)):
        for j in range(i + 1, len(maps)):
            v = ncc(maps[i][1], maps[j][1])
            pairs.append((maps[i][0], maps[j][0], round(v, 3)))
            if worst_pair[2] is None or v > worst_pair[2]:
                worst_pair = (maps[i][0], maps[j][0], v)
    pairs.sort(key=lambda t: -t[2])
    incomplete = bool(scan['requested'] and (not scan['exists'] or not refs or scan['failed_count']))
    ok_ref = not bad and not incomplete
    ok_pair = worst_pair[2] is None or worst_pair[2] < NCC_PAIR_MAX
    passed = bool(ok_ref and ok_pair)
    status = 'incomplete' if incomplete else ('failed' if not passed else ('passed' if refs else 'limited'))
    return dict(pass_=passed, status=status, has_refs=bool(refs), scan=scan,
                scope='reference_and_pair' if refs else 'pair_only',
                ref_status='incomplete' if incomplete else ('passed' if refs and not bad else ('failed' if bad else 'not_checked')),
                pair_status='passed' if len(maps) > 1 and ok_pair else ('failed' if not ok_pair else 'not_applicable'),
                refs_count=len(refs), designs=len(maps),
                worst_ref_ncc=round(worst_ref, 3) if worst_ref is not None else None, min_ref_dhash=min_dh,
                flagged=bad,
                worst_pair=dict(a=worst_pair[0], b=worst_pair[1], ncc=round(worst_pair[2], 3) if worst_pair[2] is not None else None),
                thresholds=dict(ncc_ref_max=NCC_REF_MAX, dhash_ref_min=DHASH_REF_MIN, ncc_pair_max=NCC_PAIR_MAX),
                rows=rows, pairs=pairs[:20])


def report_md(res, series='', style=''):
    def cell(value):
        if value is None:
            return '—（未核查）'
        text = html.escape(str(value), quote=True).replace('\r', ' ').replace('\n', ' / ')
        for char in ('\\', '|', '*', '_', '[', ']', '`', '#'):
            text = text.replace(char, '\\' + char)
        return text

    thresholds = res.get('thresholds', {})
    ref_max = thresholds.get('ncc_ref_max', NCC_REF_MAX)
    hash_min = thresholds.get('dhash_ref_min', DHASH_REF_MIN)
    pair_max = thresholds.get('ncc_pair_max', NCC_PAIR_MAX)
    L = [f'# 原创性核查报告{(" · " + cell(series)) if series else ""}', '']
    L.append(f'- 风格：{cell(style)}')
    L.append(f'- 作品数：{res["designs"]}')
    L.append(f'- 参考图：{res["refs_count"]} 张' if res['has_refs'] else '- 参考图：无（仅做款间查重）')
    if res.get('status') == 'incomplete':
        conclusion = '核查未完成：参考图缺失或读取失败'
    elif not res['has_refs']:
        if res.get('pair_status') == 'not_applicable':
            conclusion = '检查范围有限：仅款间查重；单款无可比较对，参考图未核查'
        else:
            conclusion = f'仅款间查重{"通过" if res["pass_"] else "未通过"}；参考图未核查'
    else:
        conclusion = '本次数值检查通过' if res['pass_'] else '本次数值检查未通过'
    L.append(f'- 结论：**{conclusion}**')
    scan = res.get('scan', {})
    if scan.get('requested'):
        L.append(f'- 读取情况：发现 {scan.get("discovered_count", 0)} 张，'
                 f'成功 {scan.get("loaded_count", 0)} 张，去重 {scan.get("duplicates_count", 0)} 张，'
                 f'读取失败 {scan.get("failed_count", 0)} 张。')
        for failed in scan.get('failures', []):
            L.append(f'  - {cell(failed["file"])}：{cell(failed["error"])}')
    L.append('')
    L.append('## 判定标准')
    L.append('| 项 | 阈值 | 本次 |')
    L.append('|---|---|---|')
    L.append(f'| 与参考图最大 NCC | < {ref_max} | {cell(res["worst_ref_ncc"])} |')
    L.append(f'| 与参考图最小 dHash 距离 | ≥ {hash_min}（同一对图的 NCC ≥ 0.60 时才参与判定） | {cell(res["min_ref_dhash"])} |')
    L.append(f'| 款与款最大 NCC | < {pair_max} | {cell(res["worst_pair"]["ncc"])} |')
    L.append('')
    L.append('参考图逐对判定：NCC ≥ 阈值，或 dHash 小于阈值且同一对 NCC ≥ 0.60，均需复核重画。最小dHash汇总可能来自另一张参考图。')
    L.append('')
    if res.get('flagged'):
        L.append('## 需要重画的款')
        L.append('| 编号 | 最像的参考图 | NCC | dHash |')
        L.append('|---|---|---|---|')
        for r in res['flagged']:
            L.append('| ' + ' | '.join(cell(r[k]) for k in ('id', 'ref', 'ncc', 'dhash')) + ' |')
        L.append('')
    L.append('## 最像参考图的 10 款（需人工复核）')
    L.append('| 编号 | 最像的参考图 | NCC | dHash |')
    L.append('|---|---|---|---|')
    for r in sorted(res['rows'], key=lambda r: -r['ncc'] if r['ncc'] is not None else float('inf'))[:10]:
        L.append('| ' + ' | '.join(cell(r[k]) for k in ('id', 'nearest_ref', 'ncc', 'dhash')) + ' |')
    L.append('')
    L.append('## 最相似的 10 对（款间查重）')
    L.append('| A | B | NCC |')
    L.append('|---|---|---|')
    for a, b, v in res['pairs'][:10]:
        L.append('| ' + ' | '.join(cell(value) for value in (a, b, v)) + ' |')
    L.append('')
    L.append('> 方法：成品网格 → 墨量图 → 裁包围盒 → 32×32；NCC（含镜像）+ dHash(64bit)。')
    L.append('> 参考图先转成"照搬版"（直接缩到 52 格量化）再比，两边同尺度。')
    L.append('> 数值通过后仍需人工把 `nearest_ref` 最高的几款和参考图并排看，确认没有照搬独特构图。')
    L.append('> 本报告只覆盖已成功读取的参考图与所列作品的数值相似度，不构成法律上的原创性保证；未提供参考图时不能判断与外部作品是否相似。')
    return '\n'.join(L)


def write(res, out_dir, series='', style=''):
    with open(os.path.join(out_dir, '原创性报告.json'), 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2, allow_nan=False)
    p = os.path.join(out_dir, '原创性报告.md')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(report_md(res, series, style))
    return p
