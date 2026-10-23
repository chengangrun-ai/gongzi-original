"""拼豆化：调色板网格 → 可拼、可熨、不掉豆的成品网格。

1. 剪影：闭运算 + 填小洞，外扩 1 格白边（贴纸式托底），剪影内空白补白豆；
2. 连通：只留一整块（四邻连通）。碎块小于阈值直接删；离主体近的用白豆桥接；
3. 统计：颗数、色数、孤立单颗、成品尺寸、难度星级、预计工时。
"""
import math
import numbers

import numpy as np
from scipy import ndimage

from .palette import PAPER

CROSS = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], bool)
PITCH_CM = 0.26


def _grid(g, pal=None):
    g = np.asarray(g)
    if g.ndim != 2 or not np.issubdtype(g.dtype, np.integer):
        raise ValueError('拼豆网格必须是二维整数数组')
    if np.any(g < PAPER) or (pal is not None and np.any(g >= len(pal))):
        raise ValueError('网格包含负数或超出调色板的颜色索引')
    return g


def _nonnegative(value, name, integer=False):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        raise ValueError(f'{name} 必须是非负数值')
    if integer and not isinstance(value, (int, np.integer)):
        raise ValueError(f'{name} 必须是非负整数')
    if not math.isfinite(float(value)) or value < 0:
        raise ValueError(f'{name} 必须是非负有限数值')
    return int(value) if integer else float(value)


def fill_holes(m, max_area=None):
    """填洞；max_area 给定时只填面积不超过它的小洞（大块留白保持镂空）。"""
    m = np.asarray(m)
    if m.ndim != 2 or not np.isin(m, [0, 1]).all():
        raise ValueError('填洞遮罩必须是二维布尔值或 0/1 数组')
    m = m.astype(bool, copy=True)
    if max_area is not None:
        max_area = _nonnegative(max_area, '洞面积上限')
    if not m.size:
        return m
    inv = ~m
    lab, n = ndimage.label(inv, structure=CROSS)
    if n == 0:
        return m
    areas = np.bincount(lab.ravel(), minlength=n + 1)
    fill = np.ones(n + 1, bool) if max_area is None else areas <= max_area
    fill[np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))] = False
    fill[0] = False
    return m | fill[lab]


def line4(p, q):
    """四邻连通的格线（桥）。"""
    (x0, y0), (x1, y1) = p, q
    out = [(x0, y0)]
    x, y = x0, y0
    while (x, y) != (x1, y1):
        dx, dy = x1 - x, y1 - y
        if abs(dx) >= abs(dy):
            x += int(np.sign(dx))
        else:
            y += int(np.sign(dy))
        out.append((x, y))
    return out


def finalize(g, border=1, close=1, min_island=30, hole=16, bridge_max=5, white=1):
    """返回整理后的网格（同形状，PAPER=0）。white 是白豆的调色板索引。"""
    g = _grid(g).copy()
    border = _nonnegative(border, '白边宽度', integer=True)
    close = _nonnegative(close, '闭运算次数', integer=True)
    min_island = _nonnegative(min_island, '碎块最小面积')
    hole = None if hole is None else _nonnegative(hole, '洞面积上限')
    bridge_max = _nonnegative(bridge_max, '桥接距离')
    white = _nonnegative(white, '托底色索引', integer=True)
    if white == PAPER or white > np.iinfo(g.dtype).max:
        raise ValueError('托底色索引必须为非零、且能由网格整数类型存储')
    if not g.size:
        return g
    ink = g != PAPER
    sil = ndimage.binary_closing(ink, CROSS, iterations=close) if close else ink.copy()
    sil = fill_holes(sil | ink, hole)
    if border:
        sil = ndimage.binary_dilation(sil, CROSS, iterations=border)
    while True:
        lab, n = ndimage.label(sil, structure=CROSS)
        if n <= 1:
            break
        areas = np.bincount(lab.ravel(), minlength=n + 1)
        main = int(np.argmax(areas[1:])) + 1
        # 删除小碎块后重新贴标签；其余块先保留，允许通过相邻块连成链。
        small = areas < min_island
        small[0] = small[main] = False
        if small.any():
            sil[small[lab]] = False
            continue
        notmain = lab != main
        dist, idx = ndimage.distance_transform_edt(notmain, return_indices=True)
        ys, xs = np.nonzero(sil & notmain)
        nearest = int(np.argmin(dist[ys, xs]))
        y, x = int(ys[nearest]), int(xs[nearest])
        if dist[y, x] > bridge_max:
            sil[notmain] = False
            break
        ty, tx = int(idx[0, y, x]), int(idx[1, y, x])
        for bx, by in line4((x, y), (tx, ty)):
            sil[by, bx] = True
    out = g.copy()
    out[~sil] = PAPER
    out[sil & (g == PAPER)] = white
    return out


def singles(g):
    """四邻没有同色邻居的孤立单颗数量。"""
    g = _grid(g)
    neighbor = np.zeros(g.shape, bool)
    horizontal = g[:, 1:] == g[:, :-1]
    vertical = g[1:, :] == g[:-1, :]
    neighbor[:, 1:] |= horizontal
    neighbor[:, :-1] |= horizontal
    neighbor[1:, :] |= vertical
    neighbor[:-1, :] |= vertical
    return int(np.count_nonzero((g != PAPER) & ~neighbor))


def connected(g):
    g = _grid(g)
    lab, n = ndimage.label(g != PAPER, structure=CROSS)
    return n


def stats(g, pal, diff=None):
    g = _grid(g, pal)
    diff = {} if diff is None else diff
    if not isinstance(diff, dict):
        raise ValueError('难度参数必须是字典')
    for name in ('bead_div', 'single_div', 'star_div', 'color_coef', 'board_coef'):
        if name in diff:
            value = _nonnegative(diff[name], f'难度参数 {name}')
            if name.endswith('_div') and value == 0:
                raise ValueError(f'难度参数 {name} 必须大于零')
    cnt = {}
    values = np.bincount(g.ravel().astype(np.int64), minlength=len(pal))
    for i in range(1, len(pal)):
        c = int(values[i])
        if c:
            code = pal.code(pal.roles[i])
            cnt[code] = cnt.get(code, 0) + c
    total = int(sum(cnt.values()))
    ys, xs = np.nonzero(g != PAPER)
    pw = int(xs.max() - xs.min() + 1) if len(xs) else 0
    ph = int(ys.max() - ys.min() + 1) if len(ys) else 0
    sg = singles(g)
    ncol = len(cnt)
    boards = math.ceil(g.shape[0] / 52) * math.ceil(g.shape[1] / 52) if total else 0
    score = (total / diff.get('bead_div', 1100) + sg / diff.get('single_div', 220)
             + max(0, ncol - 2) * diff.get('color_coef', 0.35) + (boards - 1) * diff.get('board_coef', 0.25))
    stars = int(np.clip(round(1 + score / diff.get('star_div', 1.35)), 2, 5))
    level = {2: '入门', 3: '中级', 4: '进阶', 5: '高阶'}[stars]
    if not total:
        stars, level = 0, '空作品'
    lo, hi = total / 750, total / 450
    return dict(W=int(g.shape[1]), H=int(g.shape[0]), pattern_w=pw, pattern_h=ph, beads=total,
                colors=ncol, counts=cnt, singles=sg, boards=boards,
                size_cm=[round(pw * PITCH_CM, 1), round(ph * PITCH_CM, 1)],
                stars='★' * stars + '☆' * (5 - stars), star_n=stars, level=level,
                time=f'约 {max(1, round(lo))}–{max(2, round(hi))} 小时' if total else '0 小时')


def to_codes(g, pal):
    g = _grid(g, pal)
    return [[pal.code(int(v)) if v != PAPER else None for v in row] for row in g]


def quick_png(g, pal, B=8):
    """快速预览（自查小样用）。"""
    g = _grid(g, pal)
    if isinstance(B, (bool, np.bool_)) or not isinstance(B, (int, np.integer)) or B < 1:
        raise ValueError('预览每格像素 B 必须是正整数')
    H, W = g.shape
    lut = np.array([(238, 235, 230)] + [pal.tone_rgb(i) for i in range(1, len(pal))], np.uint8)
    im = np.repeat(np.repeat(lut[g], B, axis=0), B, axis=1)
    im[::B, :] = (im[::B, :] * 0.88).astype(np.uint8)
    im[:, ::B] = (im[:, ::B] * 0.88).astype(np.uint8)
    return im
