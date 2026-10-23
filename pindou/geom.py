"""几何工具：全部是纯 numpy 的点集运算，不依赖任何绘图库。

坐标单位是"格"（1 格 = 1 颗豆），y 轴向下，设计画布一律 52 格宽。
"""
import math

import numpy as np


def P(pts):
    p = np.asarray(pts, dtype=float)
    if p.ndim > 2 or (p.ndim == 2 and p.shape[1] != 2) or p.size % 2:
        raise ValueError('点集必须由 (x, y) 坐标对组成')
    p = p.reshape(-1, 2)
    if not np.isfinite(p).all():
        raise ValueError('点坐标必须是有限数值')
    return p


def _positive(value, name):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f'{name} 必须是大于零的有限数值')
    return value


def cumlen(pts):
    pts = P(pts)
    d = np.hypot(*np.diff(pts, axis=0).T)
    return np.concatenate([[0], np.cumsum(d)])


def resample(pts, step=0.25):
    step = _positive(step, '采样间距')
    pts = P(pts)
    if len(pts) < 2:
        return pts
    lengths = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    if not lengths.any():
        return pts[:1]
    # 分段采样，原折线的拐点必须保留，不能把拐角截成一条斜线。
    out = [pts[:1]]
    for a, b, length in zip(pts[:-1], pts[1:], lengths):
        if length:
            u = np.linspace(0, 1, int(math.ceil(length / step)) + 1)[1:, None]
            out.append(a + (b - a) * u)
    return np.vstack(out)


def spline(ctrl, step=0.25, closed=False, alpha=0.5):
    """向心 Catmull-Rom 样条，返回按弧长重采样的折线。"""
    step = _positive(step, '样条采样间距')
    if not math.isfinite(float(alpha)) or not 0 <= alpha <= 1:
        raise ValueError('样条 alpha 必须在 0 到 1 之间')
    C = P(ctrl)
    if len(C) < 3:
        return resample(C, step)
    Q = np.vstack([C[-1], C, C[0], C[1]]) if closed else np.vstack([2 * C[0] - C[1], C, 2 * C[-1] - C[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        m = max(4, int(np.linalg.norm(p2 - p1) / step * 1.5))
        for t in np.linspace(t1, t2, m, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    out.append(C[0] if closed else C[-1])
    return resample(np.array(out), step)


def normals(pts):
    p = P(pts)
    if len(p) < 2:
        return np.zeros_like(p), np.zeros_like(p)
    keep = np.r_[True, np.any(np.diff(p, axis=0) != 0, axis=1)]
    unique = p[keep]
    if len(unique) < 2:
        return np.zeros_like(p), np.zeros_like(p)
    t = np.gradient(unique, axis=0)[np.cumsum(keep) - 1]
    n = np.hypot(t[:, 0], t[:, 1])[:, None]
    t = t / np.maximum(n, 1e-9)
    return np.stack([-t[:, 1], t[:, 0]], axis=1), t


def offset(pts, d):
    n, _ = normals(pts)
    return P(pts) + n * (np.asarray(d, float)[:, None] if np.ndim(d) else d)


def area(poly):
    p = P(poly)
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def inset(poly, d):
    """闭合轮廓向内收 d 格（自动判断方向；d<0 为外扩）。"""
    p = P(poly)
    a = offset(p, d)
    b = offset(p, -d)
    return a if (abs(area(a)) < abs(area(b))) == (d > 0) else b


def arc(cx, cy, r, a0, a1, step=0.25, ry=None):
    step = _positive(step, '圆弧采样间距')
    ry = r if ry is None else ry
    if not np.isfinite([cx, cy, r, ry, a0, a1]).all() or min(r, ry) < 0:
        raise ValueError('圆弧参数必须有限，半径不能为负')
    n = max(3, int(abs(a1 - a0) * max(r, ry) / step) + 1)
    a = np.linspace(a0, a1, n)
    return np.stack([cx + r * np.cos(a), cy + ry * np.sin(a)], axis=1)


def spiral(cx, cy, r0, r1, a0, turns, step=0.25):
    """从半径 r0、角度 a0 开始绕 turns 圈到半径 r1（turns 为负 = 逆时针）。"""
    step = _positive(step, '螺旋采样间距')
    if not np.isfinite([cx, cy, r0, r1, a0, turns]).all() or min(r0, r1) < 0:
        raise ValueError('螺旋参数必须有限，半径不能为负')
    L = abs(turns) * 2 * math.pi * (r0 + r1) / 2
    n = max(8, int(L / step))
    u = np.linspace(0, 1, n)
    a = a0 + turns * 2 * math.pi * u
    r = r0 + (r1 - r0) * u
    return np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], axis=1)


def rot(pts, ang, c=(0, 0)):
    pts = P(pts)
    c = np.asarray(c, float)
    ca, sa = math.cos(ang), math.sin(ang)
    d = pts - c
    return np.stack([c[0] + d[:, 0] * ca - d[:, 1] * sa, c[1] + d[:, 0] * sa + d[:, 1] * ca], axis=1)


def mirror_x(pts, cx):
    pts = P(pts).copy()
    pts[:, 0] = 2 * cx - pts[:, 0]
    return pts


def mirror_y(pts, cy):
    pts = P(pts).copy()
    pts[:, 1] = 2 * cy - pts[:, 1]
    return pts


def tf(pts, sx=1, sy=None, dx=0, dy=0, ang=0):
    """局部坐标 → 画布：先缩放、再旋转、再平移。"""
    sy = sx if sy is None else sy
    pts = P(pts) * [sx, sy]
    if ang:
        pts = rot(pts, ang)
    return pts + [dx, dy]


def widths_for(pts, widths):
    """宽度可以是：常数 / 任意长度数组（按弧长插值）/ 函数 f(u)，u∈[0,1]。"""
    pts = P(pts)
    n = len(pts)
    if n == 0:
        return np.empty(0, float)
    s = cumlen(pts)
    u = s / s[-1] if s[-1] else np.zeros(n)
    if callable(widths):
        w = np.asarray([widths(v) for v in u], float)
    else:
        w = np.atleast_1d(np.asarray(widths, float))
    if w.ndim != 1 or not w.size or not np.isfinite(w).all() or np.any(w < 0):
        raise ValueError('宽度表必须是一维、非负、有限数值')
    if w.size == 1:
        return np.full(n, float(w[0]))
    if w.size != n:
        return np.interp(u, np.linspace(0, 1, w.size), w)
    return w


def taper_outline(pts, widths):
    pts = P(pts)
    w = widths_for(pts, widths)
    n, _ = normals(pts)
    return np.vstack([pts + n * w[:, None] / 2, (pts - n * w[:, None] / 2)[::-1]])


def wprofile(n, w0, w1, power=1.0, mid=None):
    """宽度表：两端 w0/w1；给 mid=(位置, 最大宽) 时两头细中间粗。"""
    u = np.linspace(0, 1, n)
    if mid is None:
        return w0 + (w1 - w0) * u ** power
    pos, wm = mid
    return np.where(u < pos,
                    w0 + (wm - w0) * np.sin(u / max(pos, 1e-6) * math.pi / 2) ** power,
                    w1 + (wm - w1) * np.sin((1 - u) / max(1 - pos, 1e-6) * math.pi / 2) ** power)


# ---------------------------------------------------------------- 造型工具
def star_poly(cx, cy, r_out, r_in, n=5, ang=-math.pi / 2):
    pts = []
    for k in range(2 * n):
        r = r_out if k % 2 == 0 else r_in
        a = ang + k * math.pi / n
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def ngon(cx, cy, r, n=6, ang=-math.pi / 2, ry=None):
    ry = r if ry is None else ry
    a = np.linspace(0, 2 * math.pi, n, endpoint=False) + ang
    return np.stack([cx + r * np.cos(a), cy + ry * np.sin(a)], axis=1)


def rounded_rect(x0, y0, x1, y1, r, n=6):
    r = max(0.0, min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01))
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0),
                       (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        pts += list(arc(cx, cy, r, a0, a0 + math.pi / 2, step=r / n if r > 0 else 1))
    return np.array(pts)


def petal(cx, cy, r, ang, spread=0.55, tip=1.0, n=24):
    """一片花瓣（泪滴形），从 (cx,cy) 朝 ang 方向伸出，长度 r。"""
    u = np.linspace(0, 1, n)
    w = np.sin(u * math.pi) ** 0.8 * spread * r * tip
    spine = np.stack([cx + r * u * math.cos(ang), cy + r * u * math.sin(ang)], axis=1)
    nx = -math.sin(ang)
    ny = math.cos(ang)
    a = spine + np.stack([nx * w, ny * w], 1)
    b = spine - np.stack([nx * w, ny * w], 1)
    return np.vstack([a, b[::-1]])


def leaf(cx, cy, r, ang, w=0.42, n=26):
    """叶片：两头尖的柳叶形。"""
    u = np.linspace(0, 1, n)
    wid = np.sin(u * math.pi) ** 0.75 * w * r
    spine = np.stack([cx + r * (u - 0.5) * math.cos(ang), cy + r * (u - 0.5) * math.sin(ang)], 1)
    nx, ny = -math.sin(ang), math.cos(ang)
    return np.vstack([spine + np.stack([nx * wid, ny * wid], 1),
                      (spine - np.stack([nx * wid, ny * wid], 1))[::-1]])


def blob(cx, cy, r, rng, lobes=7, rough=0.16, n=64):
    """随机有机形（云、树冠、石头、水洼）。"""
    ph = rng.uniform(0, 2 * math.pi, lobes)
    am = rng.uniform(0.4, 1.0, lobes)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    rr = np.ones(n) * r
    for k in range(lobes):
        rr += r * rough * am[k] * np.cos(a * (k + 2) + ph[k]) / max(1, k * 0.6)
    return np.stack([cx + rr * np.cos(a), cy + rr * np.sin(a)], 1)


def body_along(spine, widths, n=None):
    """沿脊线按宽度表生成身体轮廓（鱼、鲸、蛇、海马都用它）。"""
    if n is None:
        spine = resample(spine, 0.4)
    else:
        if isinstance(n, (bool, np.bool_)) or not isinstance(n, (int, np.integer)) or n < 2:
            raise ValueError('身体采样数 n 必须是至少为 2 的整数')
        spine = P(spine)
        if not len(spine):
            raise ValueError('身体脊线不能为空')
        s = cumlen(spine)
        u = np.linspace(0, s[-1], n)
        spine = np.stack([np.interp(u, s, spine[:, 0]), np.interp(u, s, spine[:, 1])], axis=1)
    w = widths_for(spine, widths)
    nrm, _ = normals(spine)
    a = spine + nrm * w[:, None] / 2
    b = spine - nrm * w[:, None] / 2
    return np.vstack([a, b[::-1]])


def sym_poly(half, dx=0.0, dy=0.0):
    """半边控制点 → 左右对称的闭合轮廓（自动样条平滑）。"""
    h = P(half) + [dx, dy]
    full = np.vstack([h, mirror_x(h[::-1][1:-1] if len(h) > 2 else h[::-1], dx)])
    return spline(full, 0.3, closed=True)


def bezier(p0, p1, p2, p3=None, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2 = np.asarray(p0, float), np.asarray(p1, float), np.asarray(p2, float)
    if p3 is None:
        return (1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2
    p3 = np.asarray(p3, float)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3


def hull(pts):
    p = P(pts)
    p = np.unique(p, axis=0)
    if len(p) <= 2:
        return p
    def half(ps):
        out = []
        for q in ps:
            while len(out) >= 2:
                a, b = out[-1] - out[-2], q - out[-2]
                if a[0] * b[1] - a[1] * b[0] > 0:
                    break
                out.pop()
            out.append(q)
        return out
    lower = half(p)
    upper = half(p[::-1])
    return np.array(lower[:-1] + upper[:-1])
