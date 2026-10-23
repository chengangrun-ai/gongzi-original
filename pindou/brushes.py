"""纹样笔刷与填充纹理：与风格无关，靠角色名上色。

设计约束（来自拼豆工艺，任何风格都要守）
- 线宽 ≥ 1.2 格，细节线 ≥ 1 格；
- 重复纹样的周期 ≥ 3 格，圈距 ≥ 2 格，否则会糊成一片；
- 灰阶渐变最多 2–3 阶，或用 4×4 抖动；
- 碎点必须贴近主体，否则熨完会掉。
"""
import math

import numpy as np

from . import geom
from .canvas import rad_density


def _period(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} 必须是大于零的有限数值')
    return value


# ---------------------------------------------------------------- 基础笔刷
def hatch(cv, poly, gap=3.2, ang=0.8, w=1.2, role='line', cross=False):
    """排线填充：在 poly 里画等距平行线（可交叉成网格）。"""
    gap = _period(gap, '排线间距')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = math.hypot(x1 - x0, y1 - y0) / 2 + 1
    with cv.clip(p):
        for a in ([ang, ang + math.pi / 2] if cross else [ang]):
            n = int(2 * R / gap) + 2
            for k in range(-n, n + 1):
                d = k * gap
                ox, oy = -math.sin(a) * d, math.cos(a) * d
                cv.stroke([(cx + ox - math.cos(a) * R, cy + oy - math.sin(a) * R),
                           (cx + ox + math.cos(a) * R, cy + oy + math.sin(a) * R)], w, role)


def dots(cv, poly, gap=3.0, r=0.55, role='line', stagger=True):
    """规则点阵（网点/波点）。"""
    gap = _period(gap, '点阵间距')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    with cv.clip(p):
        row = 0
        y = y0 + gap / 2
        while y < y1:
            off = (gap / 2 if (stagger and row % 2) else 0)
            x = x0 + gap / 2 + off
            while x < x1:
                cv.circle(x, y, r, role)
                x += gap
            y += gap * 0.87
            row += 1


def scales(cv, poly, r=2.6, gap=0.0, w=1.2, role='line'):
    """鱼鳞/龙鳞：一排排半圆。r 为半径，周期 ≥ 2r。"""
    r = _period(r, '鳞片半径')
    step = _period(r * 2 + gap, '鳞片周期')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    with cv.clip(p):
        row = 0
        y = y0
        while y < y1 + r:
            off = step / 2 if row % 2 else 0
            x = x0 - step + off
            while x < x1 + step:
                cv.stroke(geom.arc(x, y, r, math.pi, 2 * math.pi, 0.3), w, role)
                x += step
            y += r * 0.95
            row += 1


def seigaiha(cv, poly, r=3.2, gap=1.6, rings=3, w=1.1, role='line'):
    """青海波：同心半圆叠排；圈距 ≥ 2 格才不糊。"""
    r, gap = _period(r, '青海波半径'), _period(gap, '青海波圈距')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    step = r * 2 + gap
    with cv.clip(p):
        row = 0
        y = y0
        while y < y1 + r * 2:
            off = step / 2 if row % 2 else 0
            x = x0 - step + off
            while x < x1 + step:
                for k in range(rings):
                    rr = r - k * gap
                    if rr > gap * 0.8:
                        cv.stroke(geom.arc(x, y, rr, math.pi, 2 * math.pi, 0.3), w, role)
                x += step
            y += r * 0.8
            row += 1


def waves(cv, poly, n=4, amp=2.2, w=1.2, role='line', period=18.0):
    """波浪线组：在 poly 范围内画 n 条正弦浪。"""
    period = _period(period, '波浪周期')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    with cv.clip(p):
        for k in range(n):
            yy = y0 + (y1 - y0) * (k + 0.5) / n
            xs = np.linspace(x0 - 1, x1 + 1, 60)
            ys = yy + amp * np.sin(xs / period * 2 * math.pi + k * 1.7)
            cv.stroke(np.stack([xs, ys], 1), w, role)


def rays(cv, cx, cy, r0, r1, n=12, w=1.2, role='line', alt=False):
    """放射光芒（日出、圣光、放射底纹）。"""
    for k in range(n):
        a = 2 * math.pi * k / n
        if alt and k % 2:
            continue
        cv.stroke([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                   (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], w, role)


def sunburst(cv, cx, cy, r, n=24, role='accent', w=1.3, inner=0.55):
    """实心放射三角（复古/波普底纹）。"""
    for k in range(n):
        a0 = 2 * math.pi * k / n
        a1 = a0 + math.pi / n * 1.15
        cv.poly([(cx + r * inner * math.cos(a0), cy + r * inner * math.sin(a0)),
                 (cx + r * math.cos(a0), cy + r * math.sin(a0)),
                 (cx + r * math.cos(a1), cy + r * math.sin(a1)),
                 (cx + r * inner * math.cos(a1), cy + r * inner * math.sin(a1))], role)


def stars(cv, pts, r=1.5, role='light', n=4, spin=0.0):
    """四角/多角小星。"""
    for x, y in pts:
        cv.poly(geom.star_poly(x, y, r, r * 0.28, n, -math.pi / 2 + spin), role)


def sparkle(cv, x, y, r, w=1.2, role='light'):
    """十字星光。"""
    cv.stroke([(x - r, y), (x + r, y)], w, role)
    cv.stroke([(x, y - r), (x, y + r)], w, role)


def splatter(cv, x, y, r, rng, n=6, role='line', rmin=0.55, rmax=1.5, spread=1.0):
    """墨溅/飞点：贴着主体撒，半径 ≥ 半格，避免碎到熨不上。"""
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        d = r * spread * math.sqrt(rng.uniform(0.25, 1.0))
        rr = rng.uniform(rmin, rmax)
        cv.circle(x + d * math.cos(a), y + d * math.sin(a), rr, role)


def spiral_curl(cv, x, y, r, turns=1.6, w=1.4, role='line', a0=0.0):
    """卷芽/云纹/浪花的小螺旋。"""
    cv.stroke(geom.spiral(x, y, r, r * 0.12, a0, turns, 0.3), w, role)


def tribal_band(cv, pts, w=3.0, role='line', rng=None, teeth=6):
    """部落纹条带：沿脊线的实心带 + 一侧楔形齿。"""
    pts = geom.P(pts)
    n = len(pts)
    prof = geom.wprofile(n, w * 0.45, w * 0.45, mid=(0.5, w))
    cv.tapered(pts, prof, role)
    nrm, tan = geom.normals(pts)
    for k in range(teeth):
        u = (k + 0.5) / teeth
        i = min(n - 1, int(u * n))
        L = w * 0.9
        base = pts[i] + nrm[i] * (prof[i] * 0.45)
        cv.poly([base, base + nrm[i] * L + tan[i] * L * 0.55,
                 base + tan[i] * L * 1.1], role)


def weave_band(cv, pts, w=3.4, role='line', rng=None, n=5, alt_role=None):
    """编结带（凯尔特/北欧）：沿脊线交替上下穿插的宽带。"""
    pts = geom.P(pts)
    nrm, tan = geom.normals(pts)
    L = geom.cumlen(pts)[-1]
    for k in range(n):
        u0 = k / n
        seg = pts[int(u0 * (len(pts) - 1)):int((u0 + 1) / n * (len(pts) - 1)) + 1]
        if len(seg) < 3:
            continue
        r = alt_role if (alt_role and k % 2) else role
        cv.tapered(seg, w * 0.9, r)
        mid = seg[len(seg) // 2]
        i = int(u0 * (len(pts) - 1))
        cv.stroke([mid - nrm[i] * w * 0.9, mid + nrm[i] * w * 0.9], w * 0.5, 'white' if r != 'white' else 'line')


def checker(cv, poly, cell=4.0, role='light', base=None):
    """棋盘格底纹。"""
    cell = _period(cell, '棋盘格边长')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    if base:
        cv.poly(p, base)
    with cv.clip(p):
        j = 0
        y = y0
        while y < y1:
            i = 0
            x = x0
            while x < x1:
                if (i + j) % 2 == 0:
                    cv.rect(x, y, min(x + cell, x1), min(y + cell, y1), role)
                x += cell
                i += 1
            y += cell
            j += 1


def confetti(cv, poly, n=14, rng=None, role='accent', r=0.7):
    """彩屑/纸屑：随机小方点（复古、波普风格用）。"""
    rng = rng or np.random.default_rng(0)
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    with cv.clip(p):
        for _ in range(n):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            cv.rect(x, y, x + r * 1.6, y + r * 1.6, role)


def bubbles(cv, poly, n=7, rng=None, role='light', rmin=1.2, rmax=3.2):
    """气泡：小圆环。"""
    rng = rng or np.random.default_rng(0)
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    for _ in range(n):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        r = rng.uniform(rmin, rmax)
        cv.ring(x, y, r, 1.1, role)


def halftone(cv, poly, role='light', ang=0.6, gap=2.8, rmax=1.3, lo=0.15, hi=1.0):
    """半调网点：靠圆点大小做明暗（波普、印刷风）。"""
    gap = _period(gap, '半调网点间距')
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    R = math.hypot(x1 - x0, y1 - y0)
    with cv.clip(p):
        for k in range(int(-R / gap), int(R / gap) + 2):
            for m in range(int(-R / gap), int(R / gap) + 2):
                x = (x0 + x1) / 2 + k * gap * math.cos(ang) - m * gap * math.sin(ang)
                y = (y0 + y1) / 2 + k * gap * math.sin(ang) + m * gap * math.cos(ang)
                t = np.clip((x - x0) / max(x1 - x0, 1e-6) * 0.6 + (y - y0) / max(y1 - y0, 1e-6) * 0.4, 0, 1)
                rr = rmax * (hi - (hi - lo) * t)
                if rr > 0.42:
                    cv.circle(x, y, rr, role)


def contour(cv, poly, n=5, role='line', w=1.1):
    """等距内轮廓（木刻、版画、等高线）。"""
    for k in range(n):
        d = 1.4 + k * 2.4
        try:
            inner = geom.inset(poly, d)
        except Exception:
            break
        if len(inner) < 3 or abs(geom.area(inner)) < 6:
            break
        cv.stroke(np.vstack([inner, inner[:1]]), w, role)


def gradient_fill(cv, poly, levels, field=None, lo=0.05, hi=0.95):
    """格级渐变填充（2–3 阶 + 抖动），比实心色块更有体积感。"""
    levels = tuple(levels)
    if not levels:
        raise ValueError('渐变至少需要一种颜色')
    if not np.isfinite([lo, hi]).all() or min(lo, hi) < 0 or max(lo, hi) > 1:
        raise ValueError('渐变明暗范围必须在 0 到 1 之间')
    p = geom.P(poly)
    m = cv.mask(p)
    if field is None:
        x0, y0 = p.min(0)
        x1, y1 = p.max(0)
        yy, xx = (np.mgrid[0:m.shape[0], 0:m.shape[1]] + 0.5) / cv.z
        field = np.clip((yy - y0) / max(y1 - y0, 1e-6) * 0.75
                        + (xx - x0) / max(x1 - x0, 1e-6) * 0.25, 0, 1)
    field = lo + (hi - lo) * np.asarray(field, float)
    cv.shade(m, field, levels, over=[levels[0]])


def dither_fill(cv, poly, role, rng=None, density=0.5):
    """抖动填充：实心底 + 稀疏另一色点，做出"半调"质感。"""
    m = cv.mask(poly)
    cv.stipple(m, density, role, rng=rng, over=[0, cv.pal.index('white')] if cv.pal.has('white') else [0])


# ---------------------------------------------------------------- 纹理注册表
def _t_solid(cv, poly, st, rng, role):
    cv.poly(poly, role)


def _t_stipple(cv, poly, st, rng, role):
    m = cv.mask(poly)
    cv.stipple(m, st.get('stipple_density', 0.55), st.get('detail', 'line'), rng=rng)


def _t_hatch(cv, poly, st, rng, role):
    hatch(cv, poly, gap=st.get('hatch_gap', 3.4), ang=rng.uniform(0.5, 1.1),
          w=st.get('line_width', 1.3), role=st.get('detail', 'line'))


def _t_cross(cv, poly, st, rng, role):
    hatch(cv, poly, gap=st.get('hatch_gap', 3.6), ang=rng.uniform(0.5, 1.0),
          w=st.get('line_width', 1.2), role=st.get('detail', 'line'), cross=True)


def _t_dots(cv, poly, st, rng, role):
    dots(cv, poly, gap=st.get('dot_gap', 3.2), r=st.get('dot_r', 0.6), role=st.get('detail', 'line'))


def _t_scales(cv, poly, st, rng, role):
    scales(cv, poly, r=st.get('scale_r', 2.8), w=st.get('line_width', 1.2), role=st.get('detail', 'line'))


def _t_seigaiha(cv, poly, st, rng, role):
    seigaiha(cv, poly, r=st.get('scale_r', 3.4), rings=3, w=st.get('line_width', 1.1),
             role=st.get('detail', 'line'))


def _t_waves(cv, poly, st, rng, role):
    waves(cv, poly, n=st.get('wave_n', 4), amp=st.get('wave_amp', 2.0),
          w=st.get('line_width', 1.2), role=st.get('detail', 'line'))


def _t_checker(cv, poly, st, rng, role):
    checker(cv, poly, cell=st.get('checker_cell', 4.5), role=st.get('detail', 'line'), base=role)


def _t_halftone(cv, poly, st, rng, role):
    halftone(cv, poly, role=st.get('detail', 'light'), gap=st.get('dot_gap', 2.8))


def _t_confetti(cv, poly, st, rng, role):
    confetti(cv, poly, n=st.get('confetti_n', 14), rng=rng, role=st.get('detail', 'accent'))


def _t_contour(cv, poly, st, rng, role):
    contour(cv, poly, n=st.get('contour_n', 4), role=st.get('detail', 'line'), w=st.get('line_width', 1.1))


def _t_weave(cv, poly, st, rng, role):
    """编结带纹理：在主体内叠 3 条编织带。"""
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    with cv.clip(p):
        for k in range(3):
            y = y0 + (y1 - y0) * (k + 0.5) / 3
            pts = geom.spline([(x0, y), ((x0 + x1) / 2, y + 2.4), (x1, y)], 0.3)
            weave_band(cv, pts, w=st.get('line_width', 1.4) * 2.6, role=st.get('detail', 'line'),
                       alt_role=st.get('fill', 'mid'))


def _t_gradient(cv, poly, st, rng, role):
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    m = cv.mask(p)
    cv.poly(p, role)
    yy, xx = (np.mgrid[0:m.shape[0], 0:m.shape[1]] + 0.5) / cv.z
    t = np.clip((yy - y0) / max(y1 - y0, 1e-6) * 0.75 + (xx - x0) / max(x1 - x0, 1e-6) * 0.25, 0, 1)
    lv = [r for r in (st.get('fill', 'mid'), st.get('shade1', 'dark'), st.get('shade2', 'line')) if cv.pal.has(r)]
    cv.shade(m, t, lv, over=[role])


def _t_sparkle(cv, poly, st, rng, role):
    """星屑：稀疏的四角星 + 小点，密度低、不糊。"""
    p = geom.P(poly)
    x0, y0 = p.min(0)
    x1, y1 = p.max(0)
    n = int(st.get('sparkle_n', 8))
    with cv.clip(p):
        for _ in range(n):
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
            r = rng.uniform(1.1, 1.9)
            cv.poly(geom.star_poly(x, y, r, r * 0.3, 4, 0), st.get('hi', 'white'))
            if rng.random() < 0.6:
                cv.circle(x + rng.uniform(-3, 3), y + rng.uniform(-3, 3), 0.55, role)


TEXTURES = {'solid': _t_solid, 'stipple': _t_stipple, 'hatch': _t_hatch, 'cross': _t_cross,
            'dots': _t_dots, 'scales': _t_scales, 'seigaiha': _t_seigaiha, 'waves': _t_waves,
            'checker': _t_checker, 'halftone': _t_halftone, 'confetti': _t_confetti,
            'contour': _t_contour, 'sparkle': _t_sparkle, 'weave': _t_weave, 'gradient': _t_gradient}


def fill(cv, poly, kind, st, rng, role=None):
    """按纹理名填充一个闭合区域。kind 不在表里时退回 solid。"""
    fn = TEXTURES.get(kind, _t_solid)
    role = role or st.get('fill', 'mid')
    if kind == 'solid':
        fn(cv, poly, st, rng, role)
        return
    # 先铺底，再上纹理（纹理画在底色之上）
    cv.poly(poly, role)
    if kind in ('stipple', 'halftone'):
        fn(cv, poly, st, rng, role)
    else:
        fn(cv, poly, st, rng, role)
