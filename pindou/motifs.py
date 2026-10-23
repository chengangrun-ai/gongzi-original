"""参数化题材造型库：每个造型都从零用样条/几何画出来，不读任何参考图。

约定
- 造型画在局部坐标里（约 [-1,1] 见方），由 T() 缩放到 (cx, cy)、尺寸 s；
- 造型负责"主体"，纹理和描边由 st（风格包）决定；
- 返回包围盒，供构图模板做重心/占位判断。
"""
import math

import numpy as np

from . import brushes, geom

MOTIFS = {}
META = {}


def motif(name, cat='misc', cn=''):
    def deco(fn):
        MOTIFS[name] = fn
        META[name] = dict(cat=cat, cn=cn or name)
        return fn
    return deco


# ---------------------------------------------------------------- 通用零件
def T(pts, cx, cy, s, sy=None):
    p = geom.P(pts) * [s, s if sy is None else sy]
    return p + [cx, cy]


def LW(st, k=1.0):
    return st.get('line_width', 1.3) * k


def body(cv, poly, st, rng, tex=None, role=None, outline=True, lw=1.0):
    """主体：铺纹理 + 描边（大多数造型都用它）。"""
    role = role or st.get('fill', 'mid')
    brushes.fill(cv, poly, tex or st.get('fill_texture', 'solid'), st, rng, role)
    if outline:
        p = geom.P(poly)
        cv.stroke(np.vstack([p, p[:1]]), LW(st, lw), st.get('line', 'line'))
    return poly


def eye(cv, x, y, r, st, pupil=0.45):
    cv.circle(x, y, r, st.get('white', 'white') if cv.pal.has(st.get('white', 'white')) else 'light')
    cv.circle(x, y, r * pupil, st.get('line', 'line'))
    cv.stroke(geom.arc(x, y, r, 0, 2 * math.pi, 0.3), LW(st, 0.9), st.get('line', 'line'))


def spark(cv, x, y, r, st):
    brushes.sparkle(cv, x, y, r, LW(st, 0.9), st.get('light', 'light'))


# ---------------------------------------------------------------- 走兽
@motif('cat', 'beast', '猫')
def _cat(cv, cx, cy, s, st, rng):
    head = geom.spline([(-0.62, -0.2), (-0.5, -0.72), (-0.18, -0.55), (0, -0.6), (0.18, -0.55),
                        (0.5, -0.72), (0.62, -0.2), (0.55, 0.3), (0, 0.62), (-0.55, 0.3)], 0.2, closed=True)
    ears = [[(-0.58, -0.3), (-0.5, -0.95), (-0.16, -0.62)], [(0.58, -0.3), (0.5, -0.95), (0.16, -0.62)]]
    body(cv, T(ears[0], cx, cy, s), st, rng, 'solid')
    body(cv, T(ears[1], cx, cy, s), st, rng, 'solid')
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    eye(cv, cx - 0.24 * s, cy - 0.08 * s, 0.13 * s, st)
    eye(cv, cx + 0.24 * s, cy - 0.08 * s, 0.13 * s, st)
    cv.poly(T([(-0.06, 0.14), (0.06, 0.14), (0, 0.22)], cx, cy, s), st.get('accent', 'line'))
    for k in (-1, 1):
        for j in range(2):
            y0 = cy + (0.16 + j * 0.14) * s
            cv.stroke([(cx + k * 0.12 * s, y0), (cx + k * 0.5 * s, y0 + (j * 0.08 - 0.05) * s)], LW(st, 0.8), st.get('line', 'line'))
    return (cx - 0.62 * s, cy - 0.95 * s, cx + 0.62 * s, cy + 0.62 * s)


@motif('fox', 'beast', '狐狸')
def _fox(cv, cx, cy, s, st, rng):
    head = geom.spline([(0, 0.92), (-0.26, 0.5), (-0.52, 0.05), (-0.56, -0.34), (-0.24, -0.2),
                        (0, -0.26), (0.24, -0.2), (0.56, -0.34), (0.52, 0.05), (0.26, 0.5)], 0.2, closed=True)
    for k in (-1, 1):
        ear = [(k * 0.24, -0.24), (k * 0.66, -1.02), (k * 0.04, -0.44)]
        body(cv, T(ear, cx, cy, s), st, rng, 'solid')
        cv.poly(T([(k * 0.3, -0.4), (k * 0.55, -0.9), (k * 0.16, -0.5)], cx, cy, s), st.get('light', 'light'))
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    cheek = geom.spline([(0, 0.7), (-0.3, 0.34), (-0.2, 0.02), (0, 0.1), (0.2, 0.02), (0.3, 0.34)], 0.2, closed=True)
    cv.poly(T(cheek, cx, cy, s), st.get('light', 'light'))
    cv.circle(cx, cy + 0.66 * s, 0.07 * s, st.get('line', 'line'))
    for k in (-1, 1):
        cv.stroke(T([(k * 0.1, -0.06), (k * 0.32, 0.02)], cx, cy, s), LW(st, 1.2), st.get('line', 'line'))
    return (cx - 0.66 * s, cy - 1.02 * s, cx + 0.66 * s, cy + 0.92 * s)


@motif('wolf', 'beast', '狼')
def _wolf(cv, cx, cy, s, st, rng):
    head = geom.spline([(0, 0.75), (-0.3, 0.62), (-0.56, 0.25), (-0.62, -0.35), (-0.3, -0.28),
                        (0, -0.36), (0.3, -0.28), (0.62, -0.35), (0.56, 0.25), (0.3, 0.62)], 0.2, closed=True)
    for k in (-1, 1):
        body(cv, T([(k * 0.3, -0.3), (k * 0.56, -0.98), (k * 0.04, -0.5)], cx, cy, s), st, rng, 'solid')
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    cv.poly(T([(-0.26, 0.1), (0.26, 0.1), (0.16, 0.62), (-0.16, 0.62)], cx, cy, s), st.get('light', 'light'))
    cv.poly(T([(-0.08, 0.2), (0.08, 0.2), (0, 0.32)], cx, cy, s), st.get('line', 'line'))
    for k in (-1, 1):
        cv.stroke(T([(k * 0.12, -0.12), (k * 0.4, -0.04)], cx, cy, s), LW(st, 1.2), st.get('line', 'line'))
        cv.circle(cx + k * 0.26 * s, cy - 0.1 * s, 0.075 * s, st.get('accent', 'accent'))
    return (cx - 0.62 * s, cy - 0.98 * s, cx + 0.62 * s, cy + 0.75 * s)


@motif('bear', 'beast', '熊')
def _bear(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        cv.circle(cx + k * 0.46 * s, cy - 0.46 * s, 0.24 * s, st.get('fill', 'mid'))
        cv.stroke(geom.arc(cx + k * 0.46 * s, cy - 0.46 * s, 0.24 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    head = geom.arc(cx, cy, 0.66 * s, 0, 2 * math.pi, 0.3)
    body(cv, head, st, rng, st.get('face_texture', 'solid'))
    cv.ellipse(cx, cy + 0.26 * s, 0.26 * s, 0.19 * s, st.get('light', 'light'))
    cv.circle(cx, cy + 0.18 * s, 0.07 * s, st.get('line', 'line'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.26 * s, cy - 0.12 * s, 0.075 * s, st.get('line', 'line'))
    return (cx - 0.7 * s, cy - 0.7 * s, cx + 0.7 * s, cy + 0.66 * s)


@motif('rabbit', 'beast', '兔')
def _rabbit(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        ear = geom.spline([(k * 0.16, -0.2), (k * 0.3, -1.15), (k * 0.46, -1.1), (k * 0.42, -0.15)], 0.2, closed=True)
        body(cv, T(ear, cx, cy, s), st, rng, 'solid')
        cv.stroke(T([(k * 0.24, -0.3), (k * 0.36, -0.95)], cx, cy, s), LW(st, 0.8), st.get('light', 'light'))
    head = geom.arc(cx, cy, 0.56 * s, 0, 2 * math.pi, 0.3)
    body(cv, head, st, rng, st.get('face_texture', 'solid'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.2 * s, cy - 0.06 * s, 0.08 * s, st.get('line', 'line'))
    cv.circle(cx, cy + 0.14 * s, 0.06 * s, st.get('accent', 'line'))
    cv.stroke([(cx - 0.2 * s, cy + 0.3 * s), (cx, cy + 0.36 * s), (cx + 0.2 * s, cy + 0.3 * s)], LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.56 * s, cy - 1.15 * s, cx + 0.56 * s, cy + 0.56 * s)


@motif('deer', 'beast', '鹿')
def _deer(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        horn = geom.spline([(k * 0.2, -0.5), (k * 0.3, -0.85), (k * 0.24, -1.15), (k * 0.5, -1.25)], 0.15)
        cv.tapered(horn, geom.wprofile(60, LW(st, 1.1), LW(st, 0.7)), st.get('line', 'line'))
        cv.stroke(T([(k * 0.28, -0.95), (k * 0.55, -0.9)], cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    head = geom.spline([(0, 0.6), (-0.3, 0.3), (-0.34, -0.15), (-0.16, -0.45), (0, -0.4),
                        (0.16, -0.45), (0.34, -0.15), (0.3, 0.3)], 0.2, closed=True)
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.17 * s, cy - 0.1 * s, 0.06 * s, st.get('line', 'line'))
    cv.circle(cx, cy + 0.42 * s, 0.07 * s, st.get('line', 'line'))
    return (cx - 0.55 * s, cy - 1.3 * s, cx + 0.55 * s, cy + 0.6 * s)


@motif('owl', 'bird', '猫头鹰')
def _owl(cv, cx, cy, s, st, rng):
    bod = geom.spline([(0, -0.62), (-0.5, -0.5), (-0.62, 0.05), (-0.4, 0.62), (0, 0.78),
                       (0.4, 0.62), (0.62, 0.05), (0.5, -0.5)], 0.2, closed=True)
    for k in (-1, 1):
        cv.poly(T([(k * 0.3, -0.55), (k * 0.56, -0.95), (k * 0.62, -0.4)], cx, cy, s), st.get('fill', 'mid'))
    body(cv, T(bod, cx, cy, s), st, rng, st.get('face_texture', 'scales'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.24 * s, cy - 0.18 * s, 0.19 * s, st.get('white', 'white') if cv.pal.has('white') else 'light')
        cv.stroke(geom.arc(cx + k * 0.24 * s, cy - 0.18 * s, 0.19 * s, 0, 2 * math.pi, 0.3), LW(st, 0.9), st.get('line', 'line'))
        cv.circle(cx + k * 0.24 * s, cy - 0.18 * s, 0.08 * s, st.get('line', 'line'))
    cv.poly(T([(-0.07, 0.05), (0.07, 0.05), (0, 0.2)], cx, cy, s), st.get('accent', 'line'))
    return (cx - 0.62 * s, cy - 0.95 * s, cx + 0.62 * s, cy + 0.78 * s)


@motif('bird', 'bird', '小鸟')
def _bird(cv, cx, cy, s, st, rng):
    bod = geom.spline([(-0.55, 0.35), (-0.3, -0.1), (-0.05, -0.35), (0.3, -0.3), (0.5, -0.55),
                       (0.55, -0.1), (0.35, 0.3), (0, 0.45), (-0.3, 0.5)], 0.2, closed=True)
    body(cv, T(bod, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    wing = geom.spline([(-0.2, 0.0), (0.1, -0.05), (0.35, 0.12), (0.05, 0.3)], 0.2, closed=True)
    brushes.fill(cv, T(wing, cx, cy, s), st.get('wing_texture', 'hatch'), st, rng, st.get('shade1', 'dark'))
    cv.stroke(np.vstack([T(wing, cx, cy, s), T(wing, cx, cy, s)[:1]]), LW(st, 0.9), st.get('line', 'line'))
    cv.circle(cx + 0.4 * s, cy - 0.36 * s, 0.06 * s, st.get('line', 'line'))
    cv.poly(T([(0.55, -0.42), (0.78, -0.32), (0.55, -0.24)], cx, cy, s), st.get('accent', 'line'))
    return (cx - 0.55 * s, cy - 0.55 * s, cx + 0.78 * s, cy + 0.5 * s)


@motif('butterfly', 'bug', '蝴蝶')
def _butterfly(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        up = geom.spline([(0.06 * k, -0.12), (0.42 * k, -0.92), (0.9 * k, -0.55), (0.78 * k, 0.02), (0.2 * k, 0.05)], 0.2, closed=True)
        lo = geom.spline([(0.08 * k, 0.06), (0.72 * k, 0.2), (0.66 * k, 0.74), (0.28 * k, 0.72), (0.05 * k, 0.34)], 0.2, closed=True)
        body(cv, T(up, cx, cy, s), st, rng, 'solid', role=st.get('fill', 'mid'))
        body(cv, T(lo, cx, cy, s), st, rng, 'solid', role=st.get('shade1', 'dark'))
        cv.circle(cx + k * 0.46 * s, cy - 0.5 * s, 0.13 * s, st.get('accent', 'accent'))
        cv.circle(cx + k * 0.38 * s, cy + 0.42 * s, 0.09 * s, st.get('light', 'light'))
    cv.ellipse(cx, cy + 0.08 * s, 0.07 * s, 0.44 * s, st.get('line', 'line'))
    for k in (-1, 1):
        cv.stroke(geom.spline([(0, -0.34 * s), (k * 0.18 * s, -0.62 * s), (k * 0.32 * s, -0.66 * s)], 0.3), LW(st, 1.0), st.get('line', 'line'))
    return (cx - 0.9 * s, cy - 0.92 * s, cx + 0.9 * s, cy + 0.74 * s)


@motif('moth', 'bug', '飞蛾')
def _moth(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        w = geom.spline([(0.08 * k, -0.25), (0.5 * k, -0.8), (0.92 * k, -0.3), (0.78 * k, 0.4), (0.22 * k, 0.2)], 0.2, closed=True)
        body(cv, T(w, cx, cy, s), st, rng, st.get('wing_texture', 'stipple'), role=st.get('fill', 'mid'))
        cv.circle(cx + k * 0.48 * s, cy - 0.18 * s, 0.15 * s, st.get('light', 'light'))
        cv.circle(cx + k * 0.48 * s, cy - 0.18 * s, 0.07 * s, st.get('accent', 'accent'))
    cv.ellipse(cx, cy + 0.02 * s, 0.12 * s, 0.56 * s, st.get('line', 'line'))
    for k in (-1, 1):
        cv.stroke(geom.spline([(0, -0.46 * s), (k * 0.22 * s, -0.76 * s), (k * 0.4 * s, -0.7 * s)], 0.3), LW(st, 1.1), st.get('line', 'line'))
    return (cx - 0.92 * s, cy - 0.8 * s, cx + 0.92 * s, cy + 0.58 * s)


@motif('bee', 'bug', '蜜蜂')
def _bee(cv, cx, cy, s, st, rng):
    bod = geom.spline([(0, -0.45), (-0.42, -0.3), (-0.5, 0.15), (-0.25, 0.5), (0.25, 0.5), (0.5, 0.15), (0.42, -0.3)], 0.2, closed=True)
    body(cv, T(bod, cx, cy, s), st, rng, 'solid', role=st.get('accent', 'accent'))
    for k in range(3):
        x = cx + (-0.22 + k * 0.22) * s
        cv.stroke([(x, cy - 0.3 * s), (x, cy + 0.45 * s)], LW(st, 1.6), st.get('line', 'line'))
    for k in (-1, 1):
        wing = geom.ellipse if False else geom.arc(cx + k * 0.3 * s, cy - 0.5 * s, 0.24 * s, 0, 2 * math.pi, ry=0.14 * s)
        cv.poly(wing, st.get('light', 'light'))
    return (cx - 0.5 * s, cy - 0.65 * s, cx + 0.5 * s, cy + 0.5 * s)


@motif('koi', 'sea', '锦鲤')
def _koi(cv, cx, cy, s, st, rng):
    spine = geom.spline([(-0.72, 0.05), (-0.3, -0.22), (0.15, -0.1), (0.5, 0.12), (0.82, 0.02)], 0.2)
    w = geom.wprofile(len(spine), 0.16, 0.44, mid=(0.62, 0.9))
    body(cv, T(geom.body_along(spine, w), cx, cy, s), st, rng, st.get('face_texture', 'scales'))
    for k in (-1, 1):
        fin = np.array([(0.18, 0.3), (0.46, 0.62), (0.0, 0.5)])
        cv.poly(T(fin * [1, k], cx, cy, s), st.get('shade1', 'dark'))
    tail = np.array([(-0.66, 0.02), (-1.0, -0.42), (-0.9, 0.04), (-1.0, 0.48)])
    cv.poly(T(geom.spline(tail, 0.2, closed=True), cx, cy, s), st.get('shade1', 'dark'))
    cv.circle(cx + 0.6 * s, cy - 0.02 * s, 0.075 * s, st.get('line', 'line'))
    cv.circle(cx - 0.05 * s, cy - 0.3 * s, 0.17 * s, st.get('accent', 'accent'))
    return (cx - 1.0 * s, cy - 0.62 * s, cx + 0.82 * s, cy + 0.62 * s)


@motif('fish', 'sea', '小鱼')
def _fish(cv, cx, cy, s, st, rng):
    spine = geom.spline([(-0.62, 0), (-0.2, -0.1), (0.25, -0.04), (0.58, 0.04)], 0.2)
    w = geom.wprofile(len(spine), 0.24, 0.62, mid=(0.42, 0.8))
    body(cv, T(geom.body_along(spine, w), cx, cy, s), st, rng, st.get('face_texture', 'scales'))
    tail = np.array([(-0.58, 0), (-0.98, -0.46), (-0.84, 0), (-0.98, 0.46)])
    cv.poly(T(geom.spline(tail, 0.2, closed=True), cx, cy, s), st.get('shade1', 'dark'))
    cv.circle(cx + 0.42 * s, cy - 0.08 * s, 0.07 * s, st.get('line', 'line'))
    return (cx - 1.0 * s, cy - 0.55 * s, cx + 0.6 * s, cy + 0.55 * s)


@motif('whale', 'sea', '鲸')
def _whale(cv, cx, cy, s, st, rng):
    spine = geom.spline([(-0.78, 0.12), (-0.3, -0.08), (0.22, -0.04), (0.62, 0.12), (0.86, 0.04)], 0.2)
    w = geom.wprofile(len(spine), 0.22, 0.55, mid=(0.34, 0.8))
    body(cv, T(geom.body_along(spine, w), cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    tail = np.array([(-0.72, 0.08), (-1.0, -0.44), (-0.86, 0.06), (-1.04, 0.5)])
    cv.poly(T(geom.spline(tail, 0.2, closed=True), cx, cy, s), st.get('shade1', 'dark'))
    for k in range(3):
        cv.stroke(T([(-0.46 + k * 0.2, 0.16), (-0.34 + k * 0.2, 0.52)], cx, cy, s), LW(st, 0.9), st.get('light', 'light'))
    cv.circle(cx + 0.56 * s, cy - 0.04 * s, 0.07 * s, st.get('line', 'line'))
    return (cx - 1.04 * s, cy - 0.6 * s, cx + 0.86 * s, cy + 0.6 * s)


@motif('octopus', 'sea', '章鱼')
def _octopus(cv, cx, cy, s, st, rng):
    head = geom.spline([(0, -0.82), (-0.44, -0.6), (-0.58, -0.05), (-0.46, 0.16), (0, 0.2),
                        (0.46, 0.16), (0.58, -0.05), (0.44, -0.6)], 0.2, closed=True)
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    for k in range(7):
        u = (k - 3) / 3.0
        sw = 0.14 * (1 if k % 2 else -1)
        pts = geom.spline([(u * 0.42, 0.1), (u * 0.72, 0.42), (u * 0.92 + sw, 0.72), (u * 0.7 + sw, 0.92)], 0.25)
        w = geom.wprofile(len(pts), 0.24, 0.05, power=0.8)
        cv.tapered(T(pts, cx, cy, s), w * s, st.get('fill', 'mid'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.22 * s, cy - 0.14 * s, 0.1 * s, st.get('line', 'line'))
        cv.circle(cx + k * 0.22 * s, cy - 0.14 * s, 0.045 * s, st.get('light', 'light'))
    cv.stroke(geom.arc(cx, cy + 0.02 * s, 0.12 * s, 0.3, math.pi - 0.3, 0.3), LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.95 * s, cy - 0.82 * s, cx + 0.95 * s, cy + 0.95 * s)


@motif('jellyfish', 'sea', '水母')
def _jellyfish(cv, cx, cy, s, st, rng):
    dome = geom.spline([(-0.7, 0.0), (-0.62, -0.55), (0, -0.78), (0.62, -0.55), (0.7, 0.0), (0, 0.12)], 0.2, closed=True)
    body(cv, T(dome, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    for k in range(5):
        u = (k - 2) / 2.2
        pts = geom.spline([(u * 0.45, 0.1), (u * 0.6 + 0.1, 0.55), (u * 0.5, 0.95)], 0.2)
        cv.stroke(T(pts, cx, cy, s), LW(st, 1.0), st.get('shade1', 'dark'))
    cv.stroke(geom.arc(cx, cy - 0.05 * s, 0.45 * s, math.pi * 1.15, math.pi * 1.85, 0.3), LW(st, 1.0), st.get('light', 'light'))
    return (cx - 0.7 * s, cy - 0.78 * s, cx + 0.7 * s, cy + 1.0 * s)


@motif('turtle', 'sea', '海龟')
def _turtle(cv, cx, cy, s, st, rng):
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        limb = geom.arc(cx + 0.62 * s * math.cos(a), cy + 0.12 + 0.5 * s * math.sin(a), 0.24 * s, 0, 2 * math.pi, 0.3, ry=0.13 * s)
        cv.poly(geom.rot(limb, a, (cx, cy + 0.12)), st.get('shade1', 'dark'))
    cv.circle(cx, cy - 0.62 * s, 0.24 * s, st.get('fill', 'mid'))
    cv.stroke(geom.arc(cx, cy - 0.62 * s, 0.24 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.09 * s, cy - 0.66 * s, 0.045 * s, st.get('line', 'line'))
    shell = geom.arc(cx, cy + 0.14, 0.68 * s, 0, 2 * math.pi, 0.3, ry=0.58 * s)
    body(cv, shell, st, rng, st.get('face_texture', 'scales'))
    for k in range(6):
        a = 2 * math.pi * k / 6
        cv.poly(geom.ngon(cx + 0.36 * s * math.cos(a), cy + 0.14 + 0.3 * s * math.sin(a), 0.17 * s, 6, a),
                st.get('light', 'light'))
    return (cx - 0.9 * s, cy - 0.9 * s, cx + 0.9 * s, cy + 0.85 * s)


@motif('snake', 'bug', '蛇')
def _snake(cv, cx, cy, s, st, rng):
    pts = geom.spline([(-0.45, 0.75), (0.3, 0.5), (-0.3, 0.1), (0.35, -0.3), (-0.15, -0.62), (0.3, -0.8)], 0.2)
    w = geom.wprofile(len(pts), 0.42, 0.14)
    body(cv, T(geom.body_along(pts, w), cx, cy, s), st, rng, st.get('face_texture', 'scales'))
    hx, hy = cx + 0.32 * s, cy - 0.82 * s
    cv.circle(hx, hy, 0.15 * s, st.get('fill', 'mid'))
    cv.stroke(geom.arc(hx, hy, 0.15 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    cv.circle(hx + 0.05 * s, hy - 0.03 * s, 0.045 * s, st.get('accent', 'line'))
    cv.stroke([(hx + 0.1 * s, hy + 0.05 * s), (hx + 0.24 * s, hy + 0.13 * s)], LW(st, 0.8), st.get('accent', 'line'))
    return (cx - 0.7 * s, cy - s, cx + 0.7 * s, cy + 0.8 * s)


@motif('crab', 'sea', '蟹')
def _crab(cv, cx, cy, s, st, rng):
    shell = geom.arc(cx, cy, 0.6 * s, 0, 2 * math.pi, 0.3, ry=0.45 * s)
    body(cv, shell, st, rng, st.get('face_texture', 'solid'))
    for k in (-1, 1):
        for j in range(3):
            a = (0.4 + j * 0.35) * k
            cv.stroke([(cx + k * 0.5 * s, cy + 0.1 * s),
                       (cx + k * (0.75 + 0.12 * j) * s, cy + (0.3 + 0.25 * j) * s)], LW(st, 1.1), st.get('line', 'line'))
        claw = geom.spline([(k * 0.5, -0.15), (k * 0.9, -0.5), (k * 1.0, -0.15), (k * 0.75, -0.05)], 0.2, closed=True)
        body(cv, T(claw, cx, cy, s), st, rng, 'solid')
        cv.circle(cx + k * 0.22 * s, cy - 0.3 * s, 0.07 * s, st.get('line', 'line'))
    return (cx - 1.0 * s, cy - 0.6 * s, cx + 1.0 * s, cy + 0.9 * s)


@motif('dragon', 'beast', '龙')
def _dragon(cv, cx, cy, s, st, rng):
    head = geom.spline([(0.1, -0.45), (0.55, -0.5), (0.85, -0.15), (0.8, 0.2), (0.5, 0.3),
                        (0.25, 0.15), (0.05, 0.2)], 0.2, closed=True)
    body(cv, T(head, cx, cy, s), st, rng, st.get('face_texture', 'scales'))
    neck = geom.spline([(0.05, 0.05), (-0.25, 0.35), (-0.6, 0.25), (-0.8, 0.55), (-0.5, 0.8)], 0.2)
    cv.tapered(T(neck, cx, cy, s), geom.wprofile(len(neck), 0.42 * s, 0.1 * s), st.get('fill', 'mid'))
    for k in range(4):
        a = -0.3 + k * 0.35
        cv.poly(T([(0.35 + 0.1 * k, -0.45), (0.45 + 0.1 * k, -0.85), (0.6 + 0.1 * k, -0.42)], cx, cy, s), st.get('accent', 'accent'))
    cv.circle(cx + 0.6 * s, cy - 0.2 * s, 0.08 * s, st.get('accent', 'line'))
    cv.stroke(geom.spline([(0.8, 0.0), (1.0, 0.1), (1.05, 0.35)], 0.3), LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.85 * s, cy - 0.9 * s, cx + 1.1 * s, cy + 0.9 * s)


@motif('dino', 'beast', '小恐龙')
def _dino(cv, cx, cy, s, st, rng):
    bod = geom.spline([(-0.62, 0.55), (-0.5, -0.15), (-0.15, -0.5), (0.3, -0.45), (0.52, -0.1),
                       (0.48, 0.55), (0, 0.68)], 0.2, closed=True)
    for k in range(4):
        x = -0.4 + k * 0.24
        cv.poly(T([(x, -0.3), (x + 0.1, -0.66), (x + 0.2, -0.26)], cx, cy, s), st.get('accent', 'accent'))
    body(cv, T(bod, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    for k in (-1, 1):
        cv.stroke(T([(-0.3, 0.55), (-0.34, 0.86)], cx, cy, s), LW(st, 1.5), st.get('line', 'line'))
        cv.stroke(T([(0.24, 0.55), (0.28, 0.86)], cx, cy, s), LW(st, 1.5), st.get('line', 'line'))
    cv.circle(cx + 0.3 * s, cy - 0.26 * s, 0.06 * s, st.get('line', 'line'))
    cv.stroke(T([(0.4, 0.18), (0.58, 0.24)], cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.62 * s, cy - 0.66 * s, cx + 0.58 * s, cy + 0.86 * s)


# ---------------------------------------------------------------- 花草
@motif('flower', 'flora', '花')
def _flower(cv, cx, cy, s, st, rng):
    n = st.get('petals', 6)
    for k in range(n):
        a = 2 * math.pi * k / n + rng.uniform(-0.05, 0.05)
        p = T(geom.petal(0, 0, 0.58, a, spread=0.42, tip=1.0), cx, cy, s)
        body(cv, p, st, rng, st.get('face_texture', 'solid'))
    cv.circle(cx, cy, 0.22 * s, st.get('accent', 'accent'))
    cv.stroke(geom.arc(cx, cy, 0.22 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    brushes.dots(cv, geom.arc(cx, cy, 0.1 * s, 0, 2 * math.pi, 0.4), gap=0.3 * s, r=0.05 * s, role=st.get('line', 'line'), stagger=False)
    return (cx - 0.62 * s, cy - 0.62 * s, cx + 0.62 * s, cy + 0.62 * s)


@motif('rose', 'flora', '玫瑰')
def _rose(cv, cx, cy, s, st, rng):
    rings = [(1.0, st.get('shade1', 'dark'), 6), (0.72, st.get('fill', 'mid'), 5), (0.45, st.get('light', 'light'), 4)]
    for rr, role, n in rings:
        for k in range(n):
            a = 2 * math.pi * k / n + rr
            p = geom.petal(cx, cy, rr * s, a, spread=0.42, tip=1.0)
            body(cv, p, st, rng, 'solid', role=role)
    cv.circle(cx, cy, 0.14 * s, st.get('accent', 'accent'))
    for k in range(2):
        a = 2 * math.pi * k / 2 + 0.6
        p = geom.leaf(cx + 0.95 * s * math.cos(a), cy + 0.95 * s * math.sin(a), 0.5 * s, a, w=0.3)
        cv.poly(p, st.get('shade1', 'dark'))
    return (cx - 1.2 * s, cy - 1.2 * s, cx + 1.2 * s, cy + 1.2 * s)


@motif('lotus', 'flora', '莲花')
def _lotus(cv, cx, cy, s, st, rng):
    for k in range(5):
        a = -math.pi / 2 + (k - 2) * 0.42
        p = T(geom.petal(0, 0.15 * s, 0.95 * s, a, spread=0.36), cx, cy, 1.0)
        body(cv, p, st, rng, st.get('face_texture', 'solid'))
    for k in range(3):
        a = -math.pi / 2 + (k - 1) * 0.62
        p = T(geom.petal(0, 0.24 * s, 0.42 * s, a, spread=0.22), cx, cy, 1.0)
        body(cv, p, st, rng, 'solid', role=st.get('accent', 'accent'))
    return (cx - 0.95 * s, cy - 0.95 * s, cx + 0.95 * s, cy + 0.9 * s)


@motif('mushroom', 'flora', '蘑菇')
def _mushroom(cv, cx, cy, s, st, rng):
    cap = geom.spline([(-0.85, 0.05), (-0.6, -0.6), (0, -0.8), (0.6, -0.6), (0.85, 0.05), (0, 0.15)], 0.2, closed=True)
    body(cv, T(cap, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('accent', 'accent'))
    for k in range(4):
        a = -2.4 + k * 0.7
        cv.circle(cx + 0.42 * s * math.cos(a), cy + 0.34 * s * math.sin(a), 0.1 * s, st.get('white', 'white') if cv.pal.has('white') else 'light')
    stem = geom.spline([(-0.24, 0.1), (-0.3, 0.6), (-0.2, 0.8), (0.2, 0.8), (0.3, 0.6), (0.24, 0.1)], 0.2, closed=True)
    body(cv, T(stem, cx, cy, s), st, rng, 'solid', role=st.get('light', 'light'))
    return (cx - 0.85 * s, cy - 0.8 * s, cx + 0.85 * s, cy + 0.8 * s)


@motif('leaf', 'flora', '叶片')
def _leaf(cv, cx, cy, s, st, rng):
    p = geom.leaf(cx, cy, 1.7 * s, -math.pi / 2 + rng.uniform(-0.2, 0.2), w=0.5)
    body(cv, p, st, rng, st.get('face_texture', 'solid'))
    cv.stroke([(cx, cy + 0.85 * s), (cx, cy - 0.85 * s)], LW(st, 1.0), st.get('line', 'line'))
    for k in range(4):
        y = cy - 0.5 * s + k * 0.32 * s
        for k2 in (-1, 1):
            cv.stroke([(cx, y), (cx + k2 * (0.42 - k * 0.06) * s, y - 0.18 * s)], LW(st, 0.85), st.get('line', 'line'))
    return (cx - 0.8 * s, cy - 0.9 * s, cx + 0.8 * s, cy + 0.9 * s)


@motif('fern', 'flora', '蕨叶')
def _fern(cv, cx, cy, s, st, rng):
    spine = geom.spline([(0, 0.95 * s), (0.1 * s, 0.2 * s), (-0.05 * s, -0.6 * s), (0.05 * s, -1.0 * s)], 0.3)
    spine = spine + [cx, cy]
    cv.stroke(spine, LW(st, 1.2), st.get('line', 'line'))
    n = 7
    for k in range(n):
        i = int((k + 0.6) / (n + 0.4) * (len(spine) - 1))
        x, y = spine[i]
        L = (0.75 - k * 0.075) * s
        for k2 in (-1, 1):
            p = geom.leaf(x, y, L, (k2 * 1.1) - math.pi / 2 * 0.15, w=0.34)
            body(cv, p, st, rng, 'solid', role=st.get('fill', 'mid'))
    return (cx - 0.8 * s, cy - 1.0 * s, cx + 0.8 * s, cy + 1.0 * s)


@motif('cactus', 'flora', '仙人掌')
def _cactus(cv, cx, cy, s, st, rng):
    trunk = geom.rounded_rect(cx - 0.26 * s, cy - 0.9 * s, cx + 0.26 * s, cy + 0.9 * s, 0.26 * s)
    body(cv, trunk, st, rng, 'solid')
    for k, y in ((-1, 0.1), (1, -0.25)):
        arm = geom.rounded_rect(cx + k * 0.26 * s, cy + (y - 0.18) * s,
                                cx + k * 0.72 * s, cy + (y + 0.18) * s, 0.18 * s)
        cv.poly(arm, st.get('fill', 'mid'))
        up = geom.rounded_rect(cx + k * 0.46 * s, cy + (y - 0.7) * s, cx + k * 0.72 * s, cy + y * s, 0.13 * s)
        cv.poly(up, st.get('fill', 'mid'))
    pot = geom.spline([(-0.5, 0.75), (0.5, 0.75), (0.38, 1.1), (-0.38, 1.1)], 0.2, closed=True)
    body(cv, T(pot, cx, cy, s), st, rng, 'solid', role=st.get('accent', 'accent'))
    return (cx - 0.75 * s, cy - 0.9 * s, cx + 0.75 * s, cy + 1.1 * s)


@motif('tree', 'flora', '树')
def _tree(cv, cx, cy, s, st, rng):
    trunk = geom.spline([(-0.12, 1.0), (-0.08, 0.3), (0.08, 0.3), (0.12, 1.0)], 0.2, closed=True)
    body(cv, T(trunk, cx, cy, s), st, rng, 'solid', role=st.get('shade1', 'dark'))
    crown = geom.blob(cx, cy - 0.3 * s, 0.78 * s, rng, lobes=8, rough=0.14)
    body(cv, crown, st, rng, st.get('face_texture', 'stipple'))
    for k in range(4):
        a = rng.uniform(0, 6.28)
        cv.circle(cx + 0.4 * s * math.cos(a), cy - 0.3 * s + 0.4 * s * math.sin(a), 0.1 * s, st.get('accent', 'accent'))
    return (cx - 0.85 * s, cy - 1.1 * s, cx + 0.85 * s, cy + 1.0 * s)


@motif('wreath', 'flora', '花环')
def _wreath(cv, cx, cy, s, st, rng):
    R = 0.72 * s
    n = st.get('wreath_n', 9)
    for k in range(n):
        a = 2 * math.pi * k / n
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        p = geom.leaf(x, y, 0.5 * s, a + math.pi / 2, w=0.32)
        body(cv, p, st, rng, 'solid', role=st.get('shade1', 'dark'))
        if k % 3 == 0:
            cv.circle(x, y, 0.11 * s, st.get('accent', 'accent'))
    cv.stroke(geom.arc(cx, cy, R, 0, 2 * math.pi, 0.4), LW(st, 0.9), st.get('line', 'line'))
    return (cx - 1.05 * s, cy - 1.05 * s, cx + 1.05 * s, cy + 1.05 * s)


# ---------------------------------------------------------------- 天象
@motif('moon', 'sky', '月')
def _moon(cv, cx, cy, s, st, rng):
    outer = geom.arc(cx, cy, 0.85 * s, 0, 2 * math.pi, 0.3)
    inner = geom.arc(cx + 0.45 * s, cy - 0.2 * s, 0.72 * s, 0, 2 * math.pi, 0.3)
    cv.compound([outer, inner], st.get('fill', 'light'))
    cv.stroke(geom.arc(cx, cy, 0.85 * s, 1.2, 4.6, 0.3), LW(st), st.get('line', 'line'))
    cv.stroke(geom.arc(cx + 0.45 * s, cy - 0.2 * s, 0.72 * s, 2.4, 5.9, 0.3), LW(st), st.get('line', 'line'))
    for _ in range(5):
        a = rng.uniform(1.4, 4.4)
        d = rng.uniform(0.35, 0.75)
        brushes.sparkle(cv, cx + d * s * math.cos(a), cy + d * s * math.sin(a), 0.12 * s, LW(st, 0.8), st.get('light', 'light'))
    return (cx - 0.9 * s, cy - 0.9 * s, cx + 0.9 * s, cy + 0.9 * s)


@motif('sun', 'sky', '太阳')
def _sun(cv, cx, cy, s, st, rng):
    brushes.rays(cv, cx, cy, 0.75 * s, 1.15 * s, st.get('ray_n', 12), LW(st, 1.1), st.get('line', 'line'))
    body(cv, geom.arc(cx, cy, 0.7 * s, 0, 2 * math.pi, 0.3), st, rng, st.get('face_texture', 'solid'), role=st.get('accent', 'accent'))
    cv.circle(cx, cy, 0.3 * s, st.get('light', 'light'))
    return (cx - 1.15 * s, cy - 1.15 * s, cx + 1.15 * s, cy + 1.15 * s)


@motif('planet', 'sky', '星球')
def _planet(cv, cx, cy, s, st, rng):
    cv.ellipse(cx, cy, 1.15 * s, 0.32 * s, st.get('line', 'line'), ang=-0.32)
    body(cv, geom.arc(cx, cy, 0.72 * s, 0, 2 * math.pi, 0.3), st, rng, st.get('face_texture', 'solid'))
    for k in range(3):
        y = cy + (k - 1) * 0.26 * s
        cv.stroke(geom.arc(cx, y, 0.68 * s, 0.15, math.pi - 0.15, 0.3, ry=0.1 * s), LW(st, 0.9), st.get('light', 'light'))
    cv.circle(cx + 0.3 * s, cy - 0.2 * s, 0.1 * s, st.get('accent', 'accent'))
    return (cx - 1.15 * s, cy - 0.8 * s, cx + 1.15 * s, cy + 0.8 * s)


@motif('star', 'sky', '星星')
def _star(cv, cx, cy, s, st, rng):
    p = T(geom.star_poly(0, 0, 1.0, 0.45, st.get('star_n', 5), -math.pi / 2), cx, cy, s)
    body(cv, p, st, rng, st.get('face_texture', 'solid'), role=st.get('accent', 'accent'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.22 * s, cy - 0.06 * s, 0.09 * s, st.get('line', 'line'))
    return (cx - s, cy - s, cx + s, cy + s)


@motif('comet', 'sky', '彗星')
def _comet(cv, cx, cy, s, st, rng):
    for k in range(4):
        pts = T(geom.spline([(0.15, -0.3), (-0.45, 0.02 + k * 0.13), (-1.0, 0.24 + k * 0.17)], 0.3), cx, cy, s)
        cv.tapered(pts, geom.wprofile(len(pts), 0.22 * s, 0.05 * s), st.get('accent', 'accent'))
    body(cv, geom.arc(cx + 0.3 * s, cy - 0.36 * s, 0.4 * s, 0, 2 * math.pi, 0.3), st, rng, 'solid', role=st.get('light', 'light'))
    return (cx - 1.05 * s, cy - 0.8 * s, cx + 0.72 * s, cy + 0.9 * s)


@motif('eclipse', 'sky', '日蚀')
def _eclipse(cv, cx, cy, s, st, rng):
    brushes.rays(cv, cx, cy, 0.72 * s, 1.2 * s, 20, LW(st, 1.0), st.get('line', 'line'))
    cv.circle(cx, cy, 0.7 * s, st.get('accent', 'accent'))
    cv.circle(cx, cy, 0.5 * s, st.get('line', 'line'))
    return (cx - 1.2 * s, cy - 1.2 * s, cx + 1.2 * s, cy + 1.2 * s)


@motif('constellation', 'sky', '星座')
def _constellation(cv, cx, cy, s, st, rng):
    pts = [(cx + s * x, cy + s * y) for x, y in
           [(-0.8, 0.5), (-0.35, -0.15), (0.1, 0.25), (0.45, -0.5), (0.85, 0.1), (0.3, 0.65), (-0.1, 0.85)]]
    for i in range(len(pts) - 1):
        cv.stroke([pts[i], pts[i + 1]], LW(st, 1.0), st.get('line', 'line'))
    for i, p in enumerate(pts):
        r = (0.2 if i % 2 else 0.14) * s
        cv.poly(geom.star_poly(p[0], p[1], r, r * 0.34, 4, 0), st.get('accent', 'accent') if i % 3 == 0 else st.get('light', 'light'))
    return (cx - 0.9 * s, cy - 0.6 * s, cx + 0.95 * s, cy + 0.9 * s)


# ---------------------------------------------------------------- 器物
@motif('candle', 'object', '蜡烛')
def _candle(cv, cx, cy, s, st, rng):
    bod = geom.rounded_rect(cx - 0.3 * s, cy - 0.4 * s, cx + 0.3 * s, cy + 1.0 * s, 0.08 * s)
    body(cv, bod, st, rng, st.get('face_texture', 'solid'), role=st.get('light', 'light'))
    for k in range(3):
        cv.stroke([(cx - 0.22 * s, cy + (0.1 + k * 0.3) * s), (cx + 0.22 * s, cy + (0.1 + k * 0.3) * s)], LW(st, 0.85), st.get('shade1', 'dark'))
    flame = geom.spline([(0, -1.0), (-0.22, -0.55), (0, -0.3), (0.22, -0.55)], 0.2, closed=True)
    cv.poly(T(flame, cx, cy, s), st.get('accent', 'accent'))
    cv.stroke(T(flame, cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    cv.stroke([(cx, -0.4 * s + cy), (cx, -0.22 * s + cy)], LW(st, 1.2), st.get('line', 'line'))
    return (cx - 0.35 * s, cy - 1.0 * s, cx + 0.35 * s, cy + s)


@motif('key', 'object', '钥匙')
def _key(cv, cx, cy, s, st, rng):
    cv.circle(cx, cy - 0.55 * s, 0.36 * s, st.get('fill', 'mid'))
    cv.compound([geom.arc(cx, cy - 0.55 * s, 0.36 * s, 0, 2 * math.pi, 0.3),
                 geom.arc(cx, cy - 0.55 * s, 0.17 * s, 0, 2 * math.pi, 0.3)], st.get('fill', 'mid'))
    cv.stroke(geom.arc(cx, cy - 0.55 * s, 0.36 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy - 0.55 * s, 0.17 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    cv.rect(cx - 0.1 * s, cy - 0.25 * s, cx + 0.1 * s, cy + 1.0 * s, st.get('fill', 'mid'))
    cv.stroke([(cx - 0.1 * s, cy - 0.25 * s), (cx - 0.1 * s, cy + 1.0 * s)], LW(st), st.get('line', 'line'))
    cv.stroke([(cx + 0.1 * s, cy - 0.25 * s), (cx + 0.1 * s, cy + 1.0 * s)], LW(st), st.get('line', 'line'))
    for k in range(2):
        y = cy + (0.5 + k * 0.25) * s
        cv.rect(cx + 0.1 * s, y, cx + 0.42 * s, y + 0.16 * s, st.get('fill', 'mid'))
    return (cx - 0.4 * s, cy - 0.95 * s, cx + 0.45 * s, cy + s)


@motif('bottle', 'object', '瓶子')
def _bottle(cv, cx, cy, s, st, rng):
    bod = geom.spline([(-0.1, -1.0), (0.1, -1.0), (0.12, -0.5), (0.45, -0.2), (0.48, 0.6),
                       (0.3, 0.95), (-0.3, 0.95), (-0.48, 0.6), (-0.45, -0.2), (-0.12, -0.5)], 0.2, closed=True)
    body(cv, T(bod, cx, cy, s), st, rng, st.get('face_texture', 'solid'))
    cv.rect(cx - 0.16 * s, cy - 1.12 * s, cx + 0.16 * s, cy - 0.92 * s, st.get('shade1', 'dark'))
    cv.rect(cx - 0.36 * s, cy + 0.1 * s, cx + 0.36 * s, cy + 0.6 * s, st.get('light', 'light'))
    cv.stroke([(cx - 0.36 * s, cy + 0.1 * s), (cx + 0.36 * s, cy + 0.1 * s)], LW(st, 0.9), st.get('line', 'line'))
    cv.stroke([(cx - 0.36 * s, cy + 0.6 * s), (cx + 0.36 * s, cy + 0.6 * s)], LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.48 * s, cy - 1.12 * s, cx + 0.48 * s, cy + 0.95 * s)


@motif('hourglass', 'object', '沙漏')
def _hourglass(cv, cx, cy, s, st, rng):
    top = geom.spline([(-0.6, -0.95), (0.6, -0.95), (0.5, -0.75), (0.12, -0.05), (0.5, 0.7), (0.6, 0.9), (-0.6, 0.9), (-0.5, 0.7), (-0.12, -0.05), (-0.5, -0.75)], 0.2, closed=True)
    body(cv, T(top, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('light', 'light'))
    sand1 = geom.spline([(-0.42, 0.72), (0.42, 0.72), (0.1, 0.05), (-0.1, 0.05)], 0.2, closed=True)
    cv.poly(T(sand1, cx, cy, s), st.get('accent', 'accent'))
    sand2 = geom.spline([(-0.2, -0.1), (0.2, -0.1), (0.36, -0.7), (-0.36, -0.7)], 0.2, closed=True)
    cv.poly(T(sand2, cx, cy, s), st.get('accent', 'accent'))
    for y in (-0.98, 0.93):
        cv.rect(cx - 0.68 * s, cy + y * s, cx + 0.68 * s, cy + (y + 0.1) * s, st.get('shade1', 'dark'))
    return (cx - 0.7 * s, cy - s, cx + 0.7 * s, cy + s)


@motif('lantern', 'object', '灯笼')
def _lantern(cv, cx, cy, s, st, rng):
    cv.stroke([(cx, cy - 1.1 * s), (cx, cy - 0.85 * s)], LW(st, 1.1), st.get('line', 'line'))
    cv.rect(cx - 0.34 * s, cy - 0.88 * s, cx + 0.34 * s, cy - 0.72 * s, st.get('shade1', 'dark'))
    bod = geom.arc(cx, cy, 0.62 * s, 0, 2 * math.pi, 0.3, ry=0.72 * s)
    body(cv, bod, st, rng, 'solid', role=st.get('accent', 'accent'))
    for k in range(4):
        x = cx + (k - 1.5) * 0.3 * s
        cv.stroke([(x, cy - 0.68 * s), (x, cy + 0.68 * s)], LW(st, 0.85), st.get('line', 'line'))
    cv.rect(cx - 0.34 * s, cy + 0.7 * s, cx + 0.34 * s, cy + 0.86 * s, st.get('shade1', 'dark'))
    cv.stroke([(cx, cy + 0.86 * s), (cx, cy + 1.12 * s)], LW(st, 1.0), st.get('line', 'line'))
    return (cx - 0.66 * s, cy - 1.12 * s, cx + 0.66 * s, cy + 1.12 * s)


@motif('anchor', 'object', '船锚')
def _anchor(cv, cx, cy, s, st, rng):
    cv.stroke(geom.arc(cx, cy - 0.72 * s, 0.18 * s, 0, 2 * math.pi, 0.3), LW(st, 1.2), st.get('line', 'line'))
    cv.stroke([(cx, cy - 0.54 * s), (cx, cy + 0.85 * s)], LW(st, 1.6), st.get('line', 'line'))
    cv.stroke([(cx - 0.42 * s, cy - 0.3 * s), (cx + 0.42 * s, cy - 0.3 * s)], LW(st, 1.5), st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy + 0.1 * s, 0.7 * s, 0.25, math.pi - 0.25, 0.3), LW(st, 1.7), st.get('line', 'line'))
    for k in (-1, 1):
        cv.poly([(cx + k * 0.66 * s, cy + 0.42 * s), (cx + k * 0.86 * s, cy + 0.2 * s), (cx + k * 0.5 * s, cy + 0.26 * s)], st.get('line', 'line'))
    return (cx - 0.9 * s, cy - 0.9 * s, cx + 0.9 * s, cy + 0.9 * s)


@motif('dagger', 'object', '匕首')
def _dagger(cv, cx, cy, s, st, rng):
    blade = geom.spline([(0, -1.05), (-0.14, -0.2), (-0.12, 0.15), (0, 0.28), (0.12, 0.15), (0.14, -0.2)], 0.2, closed=True)
    body(cv, T(blade, cx, cy, s), st, rng, 'solid', role=st.get('light', 'light'))
    cv.stroke(T([(0, -0.95), (0, 0.2)], cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    cv.rect(cx - 0.5 * s, cy + 0.28 * s, cx + 0.5 * s, cy + 0.44 * s, st.get('shade1', 'dark'))
    cv.rect(cx - 0.11 * s, cy + 0.44 * s, cx + 0.11 * s, cy + 0.95 * s, st.get('fill', 'mid'))
    cv.stroke(geom.arc(cx, cy + 1.02 * s, 0.12 * s, 0, 2 * math.pi, 0.3), LW(st, 1.2), st.get('accent', 'accent'))
    return (cx - 0.5 * s, cy - 1.05 * s, cx + 0.5 * s, cy + 1.14 * s)


@motif('book', 'object', '书')
def _book(cv, cx, cy, s, st, rng):
    cover = geom.rounded_rect(cx - 0.7 * s, cy - 0.85 * s, cx + 0.7 * s, cy + 0.85 * s, 0.07 * s)
    body(cv, cover, st, rng, st.get('face_texture', 'solid'))
    cv.rect(cx - 0.62 * s, cy - 0.75 * s, cx + 0.55 * s, cy + 0.75 * s, st.get('light', 'light'))
    cv.stroke([(cx - 0.05 * s, cy - 0.85 * s), (cx - 0.05 * s, cy + 0.85 * s)], LW(st, 1.2), st.get('line', 'line'))
    for k in range(4):
        y = cy - 0.4 * s + k * 0.22 * s
        cv.stroke([(cx + 0.08 * s, y), (cx + 0.42 * s, y)], LW(st, 0.8), st.get('shade1', 'dark'))
    cv.circle(cx - 0.34 * s, cy, 0.16 * s, st.get('accent', 'accent'))
    return (cx - 0.7 * s, cy - 0.85 * s, cx + 0.7 * s, cy + 0.85 * s)


@motif('coffee', 'object', '咖啡杯')
def _coffee(cv, cx, cy, s, st, rng):
    cup = geom.spline([(-0.55, -0.35), (0.55, -0.35), (0.4, 0.7), (-0.4, 0.7)], 0.2, closed=True)
    body(cv, T(cup, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('light', 'light'))
    cv.stroke(geom.arc(cx + 0.55 * s, cy + 0.05 * s, 0.28 * s, -1.3, 1.3, 0.3), LW(st, 1.4), st.get('line', 'line'))
    cv.ellipse(cx, cy - 0.35 * s, 0.56 * s, 0.14 * s, st.get('accent', 'accent'))
    for k in (-1, 1):
        pts = geom.spline([(k * 0.2 * s, cy - 0.55 * s), (k * 0.1 * s, cy - 0.8 * s), (k * 0.24 * s, cy - 1.0 * s)], 0.3)
        cv.stroke(pts, LW(st, 1.0), st.get('line', 'line'))
    return (cx - 0.85 * s, cy - 1.0 * s, cx + 0.85 * s, cy + 0.7 * s)


@motif('camera', 'object', '相机')
def _camera(cv, cx, cy, s, st, rng):
    bod = geom.rounded_rect(cx - 0.85 * s, cy - 0.45 * s, cx + 0.85 * s, cy + 0.62 * s, 0.12 * s)
    body(cv, bod, st, rng, st.get('face_texture', 'solid'))
    cv.rect(cx - 0.3 * s, cy - 0.68 * s, cx + 0.3 * s, cy - 0.42 * s, st.get('shade1', 'dark'))
    cv.circle(cx, cy + 0.06 * s, 0.42 * s, st.get('light', 'light'))
    cv.stroke(geom.arc(cx, cy + 0.06 * s, 0.42 * s, 0, 2 * math.pi, 0.3), LW(st, 1.2), st.get('line', 'line'))
    cv.circle(cx, cy + 0.06 * s, 0.22 * s, st.get('line', 'line'))
    cv.circle(cx - 0.08 * s, cy - 0.02 * s, 0.07 * s, st.get('light', 'light'))
    cv.circle(cx + 0.6 * s, cy - 0.22 * s, 0.09 * s, st.get('accent', 'accent'))
    return (cx - 0.85 * s, cy - 0.68 * s, cx + 0.85 * s, cy + 0.62 * s)


@motif('cassette', 'object', '磁带')
def _cassette(cv, cx, cy, s, st, rng):
    bod = geom.rounded_rect(cx - 0.95 * s, cy - 0.6 * s, cx + 0.95 * s, cy + 0.6 * s, 0.1 * s)
    body(cv, bod, st, rng, st.get('face_texture', 'solid'))
    cv.rect(cx - 0.72 * s, cy - 0.42 * s, cx + 0.72 * s, cy + 0.05 * s, st.get('light', 'light'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.4 * s, cy + 0.3 * s, 0.16 * s, st.get('line', 'line'))
        cv.circle(cx + k * 0.4 * s, cy + 0.3 * s, 0.06 * s, st.get('light', 'light'))
    cv.poly([(cx - 0.6 * s, cy + 0.52 * s), (cx + 0.6 * s, cy + 0.52 * s), (cx + 0.45 * s, cy + 0.32 * s), (cx - 0.45 * s, cy + 0.32 * s)], st.get('shade1', 'dark'))
    return (cx - 0.95 * s, cy - 0.6 * s, cx + 0.95 * s, cy + 0.6 * s)


@motif('clock', 'object', '时钟')
def _clock(cv, cx, cy, s, st, rng):
    body(cv, geom.arc(cx, cy, 0.85 * s, 0, 2 * math.pi, 0.3), st, rng, st.get('face_texture', 'solid'), role=st.get('light', 'light'))
    for k in range(12):
        a = 2 * math.pi * k / 12
        r0 = 0.66 * s if k % 3 else 0.58 * s
        cv.stroke([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                   (cx + 0.74 * s * math.cos(a), cy + 0.74 * s * math.sin(a))], LW(st, 1.0), st.get('line', 'line'))
    cv.stroke([(cx, cy), (cx + 0.42 * s, cy - 0.22 * s)], LW(st, 1.5), st.get('line', 'line'))
    cv.stroke([(cx, cy), (cx - 0.1 * s, cy - 0.5 * s)], LW(st, 1.2), st.get('line', 'line'))
    cv.circle(cx, cy, 0.08 * s, st.get('accent', 'accent'))
    return (cx - 0.85 * s, cy - 0.85 * s, cx + 0.85 * s, cy + 0.85 * s)


@motif('potion', 'object', '药瓶')
def _potion(cv, cx, cy, s, st, rng):
    bod = geom.spline([(-0.15, -0.6), (0.15, -0.6), (0.2, -0.2), (0.55, 0.35), (0.4, 0.85), (-0.4, 0.85), (-0.55, 0.35), (-0.2, -0.2)], 0.2, closed=True)
    body(cv, T(bod, cx, cy, s), st, rng, 'solid', role=st.get('light', 'light'))
    liq = geom.spline([(-0.46, 0.25), (0.46, 0.25), (0.4, 0.82), (-0.4, 0.82)], 0.2, closed=True)
    cv.poly(T(liq, cx, cy, s), st.get('accent', 'accent'))
    cv.rect(cx - 0.19 * s, cy - 0.78 * s, cx + 0.19 * s, cy - 0.58 * s, st.get('shade1', 'dark'))
    for k in range(3):
        cv.circle(cx + (k - 1) * 0.2 * s, cy + (0.45 + 0.1 * (k % 2)) * s, 0.06 * s, st.get('white', 'white') if cv.pal.has('white') else 'light')
    return (cx - 0.58 * s, cy - 0.78 * s, cx + 0.58 * s, cy + 0.85 * s)


# ---------------------------------------------------------------- 符号
@motif('eye', 'symbol', '眼睛')
def _eye(cv, cx, cy, s, st, rng):
    up = geom.spline([(-1.0, 0), (-0.5, -0.55), (0, -0.62), (0.5, -0.55), (1.0, 0)], 0.2)
    lo = geom.spline([(-1.0, 0), (-0.5, 0.5), (0, 0.56), (0.5, 0.5), (1.0, 0)], 0.2)
    poly = np.vstack([up, lo[::-1]])
    body(cv, T(poly, cx, cy, s), st, rng, 'solid', role=st.get('white', 'white') if cv.pal.has('white') else 'light')
    cv.circle(cx, cy, 0.42 * s, st.get('accent', 'accent'))
    cv.circle(cx, cy, 0.2 * s, st.get('line', 'line'))
    cv.circle(cx - 0.1 * s, cy - 0.1 * s, 0.08 * s, st.get('white', 'white') if cv.pal.has('white') else 'light')
    for k in range(7):
        a = -math.pi * (0.15 + 0.7 * k / 6)
        cv.stroke([(cx + 1.0 * s * math.cos(a), cy + 0.62 * s * math.sin(a)),
                   (cx + 1.22 * s * math.cos(a), cy + 0.9 * s * math.sin(a))], LW(st, 1.1), st.get('line', 'line'))
    return (cx - 1.25 * s, cy - 0.9 * s, cx + 1.25 * s, cy + 0.9 * s)


@motif('heart', 'symbol', '心')
def _heart(cv, cx, cy, s, st, rng):
    h = geom.spline([(0, 0.85), (-0.62, 0.2), (-0.72, -0.25), (-0.42, -0.6), (0, -0.35),
                     (0.42, -0.6), (0.72, -0.25), (0.62, 0.2)], 0.2, closed=True)
    body(cv, T(h, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('accent', 'accent'))
    cv.stroke(T([(-0.34, -0.3), (-0.5, -0.05), (-0.34, 0.05)], cx, cy, s), LW(st, 1.0), st.get('light', 'light'))
    return (cx - 0.72 * s, cy - 0.6 * s, cx + 0.72 * s, cy + 0.85 * s)


@motif('mandala', 'symbol', '曼陀罗')
def _mandala(cv, cx, cy, s, st, rng):
    n = st.get('mandala_n', 12)
    for k in range(n):
        a = 2 * math.pi * k / n
        p = geom.petal(cx + 0.34 * s * math.cos(a), cy + 0.34 * s * math.sin(a), 0.46 * s, a, spread=0.24)
        body(cv, p, st, rng, 'solid', role=st.get('light', 'light'))
    for k in range(n):
        a = 2 * math.pi * (k + 0.5) / n
        cv.poly(geom.petal(cx + 0.72 * s * math.cos(a), cy + 0.72 * s * math.sin(a), 0.26 * s, a, spread=0.16),
                st.get('shade1', 'dark'))
    for rr, w in ((0.26 * s, 1.2), (0.86 * s, 1.3), (0.99 * s, 0.9)):
        cv.stroke(geom.arc(cx, cy, rr, 0, 2 * math.pi, 0.35), LW(st, w), st.get('line', 'line'))
    cv.circle(cx, cy, 0.13 * s, st.get('accent', 'accent'))
    return (cx - s, cy - s, cx + s, cy + s)


@motif('compass', 'symbol', '罗盘')
def _compass(cv, cx, cy, s, st, rng):
    body(cv, geom.arc(cx, cy, 0.88 * s, 0, 2 * math.pi, 0.3), st, rng, st.get('face_texture', 'solid'))
    cv.stroke(geom.arc(cx, cy, 0.88 * s, 0, 2 * math.pi, 0.3), LW(st, 1.3), st.get('line', 'line'))
    for k in range(8):
        a = 2 * math.pi * k / 8 - math.pi / 2
        L = 0.72 * s if k % 2 == 0 else 0.5 * s
        wdt = 0.13 * s if k % 2 == 0 else 0.08 * s
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        b1 = (cx + wdt * math.cos(a + math.pi / 2), cy + wdt * math.sin(a + math.pi / 2))
        b2 = (cx + wdt * math.cos(a - math.pi / 2), cy + wdt * math.sin(a - math.pi / 2))
        cv.poly([tip, b1, (cx, cy), b2], st.get('accent', 'accent') if k % 2 == 0 else st.get('light', 'light'))
        cv.stroke([tip, b1, (cx, cy), b2, tip], LW(st, 0.8), st.get('line', 'line'))
    cv.circle(cx, cy, 0.1 * s, st.get('line', 'line'))
    return (cx - 0.9 * s, cy - 0.9 * s, cx + 0.9 * s, cy + 0.9 * s)


@motif('yinyang', 'symbol', '阴阳')
def _yinyang(cv, cx, cy, s, st, rng):
    R = 0.85 * s
    light = st.get('light', 'light')
    cv.circle(cx, cy, R, light)
    cv.poly(np.vstack([geom.arc(cx, cy, R, -math.pi / 2, math.pi / 2, 0.3), [(cx, cy - R)]]), st.get('line', 'line'))
    cv.circle(cx, cy - R / 2, R / 2, st.get('line', 'line'))
    cv.circle(cx, cy + R / 2, R / 2, light)
    cv.circle(cx, cy - R / 2, R / 7, light)
    cv.circle(cx, cy + R / 2, R / 7, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy, R, 0, 2 * math.pi, 0.3), LW(st, 1.4), st.get('line', 'line'))
    return (cx - R, cy - R, cx + R, cy + R)


@motif('skull', 'symbol', '骷髅')
def _skull(cv, cx, cy, s, st, rng):
    cr = geom.spline([(0, -0.85), (-0.5, -0.7), (-0.62, -0.1), (-0.45, 0.25), (-0.3, 0.5),
                      (0, 0.62), (0.3, 0.5), (0.45, 0.25), (0.62, -0.1), (0.5, -0.7)], 0.2, closed=True)
    body(cv, T(cr, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('light', 'light'))
    for k in (-1, 1):
        cv.poly(T([(k * 0.16, -0.2), (k * 0.44, -0.28), (k * 0.4, 0.08), (k * 0.18, 0.12)], cx, cy, s), st.get('line', 'line'))
    cv.poly(T([(0, 0.06), (0.08, 0.26), (-0.08, 0.26)], cx, cy, s), st.get('line', 'line'))
    for k in range(4):
        x = (k - 1.5) * 0.13
        cv.stroke(T([(x, 0.36), (x, 0.55)], cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    cv.stroke(T([(-0.3, 0.36), (0.3, 0.36)], cx, cy, s), LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.62 * s, cy - 0.85 * s, cx + 0.62 * s, cy + 0.62 * s)


@motif('triquetra', 'symbol', '三角结')
def _triquetra(cv, cx, cy, s, st, rng):
    R = 0.5 * s
    for k in range(3):
        a = -math.pi / 2 + k * 2 * math.pi / 3
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        cv.ring(x, y, R * 0.8, 1.9, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy, R * 1.78, 0, 2 * math.pi, 0.4), LW(st, 1.3), st.get('line', 'line'))
    return (cx - R * 1.85, cy - R * 1.85, cx + R * 1.85, cy + R * 1.85)


@motif('spiral', 'symbol', '螺旋')
def _spiral(cv, cx, cy, s, st, rng):
    for k in range(2):
        a0 = k * math.pi
        pts = geom.spiral(cx, cy, 0.12 * s, 0.9 * s, a0, 1.5 * (1 if k == 0 else -1), 0.3)
        cv.tapered(pts, geom.wprofile(len(pts), 0.26 * s, 0.05 * s), st.get('line', 'line'))
    return (cx - s, cy - s, cx + s, cy + s)


@motif('wave_icon', 'symbol', '浪')
def _wave_icon(cv, cx, cy, s, st, rng):
    for k in range(3):
        y = cy + (k - 1) * 0.45 * s
        xs = np.linspace(cx - s, cx + s, 70)
        ys = y + 0.18 * s * np.sin((xs - cx) / (0.55 * s) * math.pi + k)
        cv.stroke(np.stack([xs, ys], 1), LW(st, 1.3), st.get('line', 'line'))
    return (cx - s, cy - 0.75 * s, cx + s, cy + 0.75 * s)


@motif('mountain', 'symbol', '山')
def _mountain(cv, cx, cy, s, st, rng):
    p = [(cx - s, cy + 0.75 * s), (cx - 0.45 * s, cy - 0.55 * s), (cx - 0.1 * s, cy + 0.05 * s),
         (cx + 0.3 * s, cy - 0.8 * s), (cx + s, cy + 0.75 * s)]
    body(cv, p, st, rng, st.get('face_texture', 'solid'))
    for k in (-1, 1):
        cv.poly([(cx + k * 0.45 * s, cy - 0.55 * s + (0 if k < 0 else -0.25) * s),
                 (cx + k * 0.2 * s, cy - 0.15 * s), (cx + k * 0.62 * s, cy - 0.1 * s)],
                st.get('light', 'light'))
    return (cx - s, cy - 0.8 * s, cx + s, cy + 0.75 * s)


# ---------------------------------------------------------------- 萌物
@motif('ghost', 'cute', '小幽灵')
def _ghost(cv, cx, cy, s, st, rng):
    p = geom.spline([(0, -0.9), (-0.55, -0.55), (-0.62, 0.2), (-0.45, 0.85), (-0.2, 0.55),
                     (0, 0.85), (0.2, 0.55), (0.45, 0.85), (0.62, 0.2), (0.55, -0.55)], 0.2, closed=True)
    body(cv, T(p, cx, cy, s), st, rng, 'solid', role=st.get('white', 'white') if cv.pal.has('white') else 'light')
    for k in (-1, 1):
        cv.ellipse(cx + k * 0.22 * s, cy - 0.2 * s, 0.09 * s, 0.13 * s, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy + 0.02 * s, 0.16 * s, 0.2, math.pi - 0.2, 0.3), LW(st, 1.0), st.get('line', 'line'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.42 * s, cy + 0.06 * s, 0.09 * s, st.get('accent', 'accent'))
    return (cx - 0.62 * s, cy - 0.9 * s, cx + 0.62 * s, cy + 0.85 * s)


@motif('cloud', 'cute', '云')
def _cloud(cv, cx, cy, s, st, rng):
    p = geom.blob(cx, cy, 0.62 * s, rng, lobes=5, rough=0.1)
    body(cv, p, st, rng, 'solid', role=st.get('white', 'white') if cv.pal.has('white') else 'light')
    for k in range(3):
        cv.circle(cx + (k - 1) * 0.3 * s, cy + 0.25 * s, 0.05 * s, st.get('light', 'light'))
    return (cx - 0.75 * s, cy - 0.7 * s, cx + 0.75 * s, cy + 0.7 * s)


@motif('rainbow', 'cute', '彩虹')
def _rainbow(cv, cx, cy, s, st, rng):
    roles = [r for r in ('accent', 'light', 'mid', 'dark', 'accent2') if cv.pal.has(r)] or ['line']
    for k, role in enumerate(roles[:4]):
        r = (0.95 - k * 0.16) * s
        cv.stroke(geom.arc(cx, cy + 0.55 * s, r, math.pi, 2 * math.pi, 0.3), 0.15 * s * 1.4, role)
    for k in (-1, 1):
        p = geom.blob(cx + k * 0.85 * s, cy + 0.6 * s, 0.2 * s, rng, lobes=4, rough=0.1)
        cv.poly(p, st.get('white', 'white') if cv.pal.has('white') else 'light')
    return (cx - s, cy - 0.5 * s, cx + s, cy + 0.85 * s)


@motif('star_buddy', 'cute', '星星仔')
def _star_buddy(cv, cx, cy, s, st, rng):
    p = T(geom.star_poly(0, 0, 0.95, 0.52, 5, -math.pi / 2), cx, cy, s)
    body(cv, p, st, rng, 'solid', role=st.get('accent', 'accent'))
    for k in (-1, 1):
        cv.ellipse(cx + k * 0.2 * s, cy - 0.02 * s, 0.08 * s, 0.12 * s, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy + 0.12 * s, 0.14 * s, 0.3, math.pi - 0.3, 0.3), LW(st, 1.0), st.get('line', 'line'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.36 * s, cy + 0.1 * s, 0.08 * s, st.get('light', 'light'))
    return (cx - 0.95 * s, cy - 0.95 * s, cx + 0.95 * s, cy + 0.95 * s)


@motif('cat_face', 'cute', '猫脸')
def _cat_face(cv, cx, cy, s, st, rng):
    head = geom.arc(cx, cy, 0.78 * s, 0, 2 * math.pi, 0.3, ry=0.7 * s)
    for k in (-1, 1):
        cv.poly(T([(k * 0.4, -0.5), (k * 0.62, -1.0), (k * 0.72, -0.3)], cx, cy, s), st.get('fill', 'mid'))
        cv.poly(T([(k * 0.46, -0.55), (k * 0.6, -0.85), (k * 0.64, -0.42)], cx, cy, s), st.get('accent', 'accent'))
    body(cv, head, st, rng, 'solid')
    for k in (-1, 1):
        cv.circle(cx + k * 0.3 * s, cy - 0.05 * s, 0.1 * s, st.get('line', 'line'))
        cv.stroke([(cx + k * 0.12 * s, cy + 0.2 * s), (cx + k * 0.55 * s, cy + 0.16 * s)], LW(st, 0.9), st.get('line', 'line'))
    cv.poly([(cx - 0.07 * s, cy + 0.14 * s), (cx + 0.07 * s, cy + 0.14 * s), (cx, cy + 0.24 * s)], st.get('accent', 'accent'))
    return (cx - 0.78 * s, cy - s, cx + 0.78 * s, cy + 0.7 * s)


@motif('bear_face', 'cute', '熊脸')
def _bear_face(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        cv.circle(cx + k * 0.58 * s, cy - 0.5 * s, 0.24 * s, st.get('fill', 'mid'))
        cv.stroke(geom.arc(cx + k * 0.58 * s, cy - 0.5 * s, 0.24 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    body(cv, geom.arc(cx, cy, 0.72 * s, 0, 2 * math.pi, 0.3), st, rng, 'solid')
    cv.ellipse(cx, cy + 0.24 * s, 0.26 * s, 0.18 * s, st.get('light', 'light'))
    cv.circle(cx, cy + 0.18 * s, 0.08 * s, st.get('line', 'line'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.28 * s, cy - 0.1 * s, 0.075 * s, st.get('line', 'line'))
    return (cx - 0.82 * s, cy - 0.75 * s, cx + 0.82 * s, cy + 0.72 * s)


@motif('bunny_face', 'cute', '兔脸')
def _bunny_face(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        e = geom.spline([(k * 0.22, -0.3), (k * 0.34, -1.15), (k * 0.5, -1.1), (k * 0.5, -0.25)], 0.2, closed=True)
        body(cv, T(e, cx, cy, s), st, rng, 'solid')
        cv.poly(T([(k * 0.28, -0.4), (k * 0.38, -1.0), (k * 0.44, -0.45)], cx, cy, s), st.get('accent', 'accent'))
    body(cv, geom.arc(cx, cy, 0.6 * s, 0, 2 * math.pi, 0.3), st, rng, 'solid')
    for k in (-1, 1):
        cv.circle(cx + k * 0.22 * s, cy - 0.06 * s, 0.08 * s, st.get('line', 'line'))
    cv.circle(cx, cy + 0.12 * s, 0.06 * s, st.get('accent', 'accent'))
    cv.stroke([(cx - 0.16 * s, cy + 0.26 * s), (cx, cy + 0.32 * s), (cx + 0.16 * s, cy + 0.26 * s)], LW(st, 0.9), st.get('line', 'line'))
    return (cx - 0.6 * s, cy - 1.15 * s, cx + 0.6 * s, cy + 0.6 * s)


# ---------------------------------------------------------------- 风景元素（照片/风景图用）
@motif('hill', 'scene', '丘陵')
def _hill(cv, cx, cy, s, st, rng):
    """一条起伏的丘陵带，宽度 2s，坐在 cy 线上。"""
    n = 7
    xs = np.linspace(-1, 1, n) * s + cx
    ys = np.array([-0.1 + rng.uniform(-0.3, 0.12) for _ in range(n)]) * s + cy
    top = geom.spline(np.stack([xs, ys], 1), 0.4)
    poly = np.vstack([top, [(cx + s, cy + 0.7 * s), (cx - s, cy + 0.7 * s)]])
    body(cv, poly, st, rng, st.get('face_texture', 'solid'), role=st.get('shade1', 'mid'))
    for k in range(3):
        x = cx + rng.uniform(-0.7, 0.7) * s
        y = cy + rng.uniform(0.05, 0.4) * s
        cv.stroke([(x, y), (x + 0.1 * s, y - 0.18 * s)], LW(st, 0.8), st.get('light', 'light'))
    return (cx - s, cy - 0.5 * s, cx + s, cy + 0.7 * s)


@motif('forest', 'scene', '树林')
def _forest(cv, cx, cy, s, st, rng):
    """一排树，大小错落，底部连成一条地面。"""
    n = int(st.get('forest_n', 5))
    base = cy + 0.55 * s
    cv.rect(cx - s, base - 0.08 * s, cx + s, base + 0.2 * s, st.get('shade2', 'dark'))
    for k in range(n):
        u = (k + 0.5) / n
        x = cx + (u - 0.5) * 1.9 * s
        h = (0.55 + 0.45 * rng.random()) * s
        w = h * 0.42
        trunk = [(x - 0.05 * s, base), (x + 0.05 * s, base), (x + 0.04 * s, base - h * 0.45), (x - 0.04 * s, base - h * 0.45)]
        cv.poly(trunk, st.get('shade2', 'dark'))
        crown = geom.blob(x, base - h * 0.62, w, rng, lobes=4, rough=0.12)
        cv.poly(crown, st.get('shade1', 'mid'))
        cv.stroke(np.vstack([crown, crown[:1]]), LW(st, 0.9), st.get('line', 'line'))
    return (cx - s, cy - 0.9 * s, cx + s, base + 0.2 * s)


@motif('lake', 'scene', '水面')
def _lake(cv, cx, cy, s, st, rng):
    """水面 + 倒影短线 + 几道波纹。"""
    cv.rect(cx - s, cy - 0.35 * s, cx + s, cy + 0.55 * s, st.get('shade1', 'mid'))
    for k in range(3):
        y = cy - 0.2 * s + k * 0.25 * s
        xs = np.linspace(cx - s, cx + s, 30)
        cv.stroke(np.stack([xs, y + 0.05 * s * np.sin(xs / (0.35 * s) * 2 * math.pi + k)], 1),
                  LW(st, 0.9), st.get('light', 'light'))
    for k in range(5):
        x = cx + rng.uniform(-0.85, 0.85) * s
        y = cy + rng.uniform(-0.1, 0.45) * s
        cv.stroke([(x, y), (x + 0.16 * s, y)], LW(st, 0.8), st.get('white', 'light'))
    return (cx - s, cy - 0.35 * s, cx + s, cy + 0.55 * s)


@motif('house', 'scene', '小屋')
def _house(cv, cx, cy, s, st, rng):
    base = cy + 0.75 * s
    wall = [(cx - 0.62 * s, base), (cx + 0.62 * s, base), (cx + 0.62 * s, cy - 0.1 * s), (cx - 0.62 * s, cy - 0.1 * s)]
    body(cv, wall, st, rng, 'solid', role=st.get('light', 'light'))
    roof = [(cx - 0.78 * s, cy - 0.08 * s), (cx, cy - 0.75 * s), (cx + 0.78 * s, cy - 0.08 * s)]
    body(cv, roof, st, rng, 'solid', role=st.get('shade2', 'dark'))
    cv.rect(cx + 0.3 * s, cy - 0.9 * s, cx + 0.46 * s, cy - 0.55 * s, st.get('shade2', 'dark'))
    cv.rect(cx - 0.12 * s, cy + 0.25 * s, cx + 0.14 * s, base, st.get('shade2', 'dark'))
    cv.rect(cx - 0.46 * s, cy + 0.1 * s, cx - 0.2 * s, cy + 0.35 * s, st.get('accent', 'accent'))
    cv.rect(cx + 0.2 * s, cy + 0.1 * s, cx + 0.46 * s, cy + 0.35 * s, st.get('accent', 'accent'))
    return (cx - 0.78 * s, cy - 0.9 * s, cx + 0.78 * s, base)


@motif('boat', 'scene', '小船')
def _boat(cv, cx, cy, s, st, rng):
    hull = [(cx - 0.85 * s, cy + 0.2 * s), (cx + 0.85 * s, cy + 0.2 * s),
            (cx + 0.6 * s, cy + 0.6 * s), (cx - 0.6 * s, cy + 0.6 * s)]
    body(cv, hull, st, rng, 'solid', role=st.get('shade2', 'dark'))
    cv.stroke([(cx, cy + 0.2 * s), (cx, cy - 1.0 * s)], LW(st, 1.3), st.get('line', 'line'))
    sail = [(cx + 0.06 * s, cy - 0.92 * s), (cx + 0.62 * s, cy + 0.12 * s), (cx + 0.06 * s, cy + 0.12 * s)]
    body(cv, sail, st, rng, 'solid', role=st.get('light', 'light'))
    jib = [(cx - 0.06 * s, cy - 0.86 * s), (cx - 0.5 * s, cy + 0.12 * s), (cx - 0.06 * s, cy + 0.12 * s)]
    cv.poly(jib, st.get('shade1', 'mid'))
    return (cx - 0.85 * s, cy - s, cx + 0.85 * s, cy + 0.6 * s)


@motif('lighthouse', 'scene', '灯塔')
def _lighthouse(cv, cx, cy, s, st, rng):
    tower = [(cx - 0.3 * s, cy + 0.85 * s), (cx + 0.3 * s, cy + 0.85 * s),
             (cx + 0.17 * s, cy - 0.5 * s), (cx - 0.17 * s, cy - 0.5 * s)]
    body(cv, tower, st, rng, 'solid', role=st.get('light', 'light'))
    for k in range(3):
        y = cy + 0.5 * s - k * 0.4 * s
        cv.rect(cx - 0.28 * s + k * 0.02 * s, y, cx + 0.28 * s - k * 0.02 * s, y + 0.16 * s, st.get('accent', 'accent'))
    cv.rect(cx - 0.26 * s, cy - 0.62 * s, cx + 0.26 * s, cy - 0.46 * s, st.get('shade2', 'dark'))
    cv.rect(cx - 0.2 * s, cy - 0.85 * s, cx + 0.2 * s, cy - 0.6 * s, st.get('accent', 'accent'))
    cv.poly([(cx - 0.26 * s, cy - 0.85 * s), (cx, cy - 1.05 * s), (cx + 0.26 * s, cy - 0.85 * s)], st.get('shade2', 'dark'))
    for k in (-1, 1):
        cv.stroke([(cx + k * 0.22 * s, cy - 0.72 * s), (cx + k * 0.72 * s, cy - 0.9 * s)], LW(st, 0.9), st.get('light', 'light'))
        cv.stroke([(cx + k * 0.22 * s, cy - 0.72 * s), (cx + k * 0.72 * s, cy - 0.55 * s)], LW(st, 0.9), st.get('light', 'light'))
    return (cx - 0.75 * s, cy - 1.05 * s, cx + 0.75 * s, cy + 0.85 * s)


# ---------------------------------------------------------------- 人物（只做原创角色，不还原具体角色）
@motif('chibi', 'person', 'Q版小人')
def _chibi(cv, cx, cy, s, st, rng):
    """原创 Q 版人物骨架：头 + 头发 + 身体 + 手臂。发型/衣服由 rng 变化。"""
    hy = cy - 0.35 * s
    body_poly = geom.spline([(-0.34, 0.25), (0.34, 0.25), (0.3, 0.95), (-0.3, 0.95)], 0.25, closed=True)
    body(cv, T(body_poly, cx, cy, s), st, rng, 'solid', role=st.get('shade1', 'mid'))
    for k in (-1, 1):
        cv.stroke([(cx + k * 0.3 * s, cy + 0.4 * s), (cx + k * 0.52 * s, cy + 0.8 * s)], LW(st, 1.6), st.get('line', 'line'))
    head = geom.arc(cx, hy, 0.42 * s, 0, 2 * math.pi, 0.3, ry=0.44 * s)
    body(cv, head, st, rng, 'solid', role=st.get('light', 'light'))
    style = int(rng.integers(0, 3))
    if style == 0:                                     # 短发
        hair = geom.spline([(-0.46, -0.1), (-0.3, -0.5), (0, -0.56), (0.3, -0.5), (0.46, -0.1), (0.3, -0.22), (-0.3, -0.22)], 0.2, closed=True)
        cv.poly(T(hair, cx, hy, s), st.get('shade2', 'dark'))
    elif style == 1:                                   # 双马尾
        cv.poly(T([(-0.44, -0.32), (-0.2, -0.55), (0.2, -0.55), (0.44, -0.32), (0.36, -0.05), (-0.36, -0.05)], cx, hy, s), st.get('shade2', 'dark'))
        for k in (-1, 1):
            cv.circle(cx + k * 0.5 * s, hy + 0.18 * s, 0.16 * s, st.get('shade2', 'dark'))
    else:                                              # 长发
        hair = geom.spline([(-0.46, -0.15), (-0.34, -0.55), (0, -0.6), (0.34, -0.55), (0.46, -0.15), (0.5, 0.55), (0.3, 0.5), (0.34, -0.1), (-0.34, -0.1), (-0.3, 0.5), (-0.5, 0.55)], 0.2, closed=True)
        cv.poly(T(hair, cx, hy, s), st.get('shade2', 'dark'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.16 * s, hy + 0.04 * s, 0.07 * s, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, hy + 0.1 * s, 0.1 * s, 0.3, math.pi - 0.3, 0.3), LW(st, 0.9), st.get('line', 'line'))
    cv.circle(cx, cy + 0.62 * s, 0.07 * s, st.get('accent', 'accent'))
    return (cx - 0.55 * s, hy - 0.6 * s, cx + 0.55 * s, cy + 0.95 * s)


@motif('bust', 'person', '半身像')
def _bust(cv, cx, cy, s, st, rng):
    """原创半身剪影（肩 + 颈 + 头 + 发），适合做头像徽章。"""
    shoulders = geom.spline([(-0.85, 0.95), (-0.55, 0.35), (-0.2, 0.15), (0.2, 0.15), (0.55, 0.35), (0.85, 0.95)], 0.25)
    poly = np.vstack([shoulders, [(0.85, 1.1), (-0.85, 1.1)]])
    body(cv, T(poly, cx, cy, s), st, rng, 'solid', role=st.get('shade1', 'mid'))
    cv.rect(cx - 0.16 * s, cy - 0.05 * s, cx + 0.16 * s, cy + 0.3 * s, st.get('light', 'light'))
    head = geom.arc(cx, cy - 0.32 * s, 0.38 * s, 0, 2 * math.pi, 0.3, ry=0.44 * s)
    body(cv, head, st, rng, 'solid', role=st.get('light', 'light'))
    hair = geom.spline([(-0.42, -0.3), (-0.32, -0.72), (0, -0.82), (0.32, -0.72), (0.42, -0.3), (0.34, -0.42), (0, -0.5), (-0.34, -0.42)], 0.2, closed=True)
    cv.poly(T(hair, cx, cy - 0.32 * s, s), st.get('shade2', 'dark'))
    for k in (-1, 1):
        cv.circle(cx + k * 0.14 * s, cy - 0.3 * s, 0.055 * s, st.get('line', 'line'))
    return (cx - 0.85 * s, cy - 0.85 * s, cx + 0.85 * s, cy + 1.1 * s)


# ---------------------------------------------------------------- 第二辑：风景道具 / 和风 / 萌宠
@motif('gate', 'scene', '鸟居')
def _gate(cv, cx, cy, s, st, rng):
    base = cy + 0.85 * s
    for k in (-1, 1):
        cv.poly([(cx + k * 0.52 * s, base), (cx + k * 0.38 * s, base),
                 (cx + k * 0.44 * s, cy - 0.5 * s), (cx + k * 0.56 * s, cy - 0.5 * s)], st.get('accent', 'line'))
    cv.poly([(cx - 0.82 * s, cy - 0.72 * s), (cx + 0.82 * s, cy - 0.72 * s),
             (cx + 0.86 * s, cy - 0.56 * s), (cx - 0.86 * s, cy - 0.56 * s)], st.get('shade2', 'dark'))
    cv.poly([(cx - 0.9 * s, cy - 0.86 * s), (cx + 0.9 * s, cy - 0.86 * s),
             (cx + 0.86 * s, cy - 0.76 * s), (cx - 0.86 * s, cy - 0.76 * s)], st.get('shade2', 'dark'))
    cv.rect(cx - 0.62 * s, cy - 0.42 * s, cx + 0.62 * s, cy - 0.32 * s, st.get('accent', 'line'))
    return (cx - 0.9 * s, cy - 0.86 * s, cx + 0.9 * s, base)


@motif('bridge', 'scene', '拱桥')
def _bridge(cv, cx, cy, s, st, rng):
    deck = geom.spline([(cx - s, cy + 0.1 * s), (cx - 0.5 * s, cy - 0.22 * s),
                        (cx, cy - 0.34 * s), (cx + 0.5 * s, cy - 0.22 * s), (cx + s, cy + 0.1 * s)], 0.3)
    cv.stroke(deck, LW(st, 2.0), st.get('shade2', 'dark'))
    under = geom.arc(cx, cy + 0.34 * s, 0.62 * s, math.pi, 2 * math.pi, 0.3, ry=0.5 * s)
    cv.stroke(under, LW(st, 1.6), st.get('line', 'line'))
    for k in range(7):
        u = k / 6
        x = cx + (u - 0.5) * 1.9 * s
        y = cy + 0.1 * s - 0.44 * s * (1 - (2 * u - 1) ** 2) * 0.7
        cv.stroke([(x, y), (x, y - 0.16 * s)], LW(st, 1.0), st.get('line', 'line'))
    return (cx - s, cy - 0.6 * s, cx + s, cy + 0.5 * s)


@motif('fence', 'scene', '栅栏')
def _fence(cv, cx, cy, s, st, rng):
    n = 6
    for k in range(n):
        x = cx + (k / (n - 1) - 0.5) * 1.9 * s
        h = 0.5 * s if k % 2 else 0.6 * s
        cv.poly([(x - 0.05 * s, cy + 0.6 * s), (x + 0.05 * s, cy + 0.6 * s),
                 (x + 0.05 * s, cy + 0.6 * s - h), (x, cy + 0.72 * s - h), (x - 0.05 * s, cy + 0.6 * s - h)],
                st.get('shade1', 'mid'))
    for y in (cy + 0.2 * s, cy + 0.42 * s):
        cv.rect(cx - 0.95 * s, y, cx + 0.95 * s, y + 0.07 * s, st.get('shade2', 'dark'))
    return (cx - 0.98 * s, cy - 0.1 * s, cx + 0.98 * s, cy + 0.75 * s)


@motif('path', 'scene', '小路')
def _path(cv, cx, cy, s, st, rng):
    road = [(cx - 0.2 * s, cy - 0.6 * s), (cx + 0.2 * s, cy - 0.6 * s),
            (cx + 0.92 * s, cy + 0.92 * s), (cx - 0.92 * s, cy + 0.92 * s)]
    cv.poly(road, st.get('shade1', 'mid'))
    cv.stroke([road[0], road[3]], LW(st, 1.2), st.get('line', 'line'))
    cv.stroke([road[1], road[2]], LW(st, 1.2), st.get('line', 'line'))
    for k in range(4):
        u = (k + 0.55) / 4.2
        w = 0.03 * s + 0.1 * s * u
        y = cy - 0.6 * s + (0.92 * s + 0.6 * s) * u
        cv.rect(cx - w, y, cx + w, y + 0.05 * s + 0.04 * s * u, st.get('white', 'light'))
    return (cx - 0.92 * s, cy - 0.6 * s, cx + 0.92 * s, cy + 0.92 * s)


@motif('dog', 'beast', '小狗')
def _dog(cv, cx, cy, s, st, rng):
    torso = geom.spline([(-0.34, 0.95), (-0.4, 0.35), (-0.2, 0.05), (0.22, 0.05), (0.4, 0.4), (0.32, 0.95)], 0.25, closed=True)
    body(cv, T(torso, cx, cy, s), st, rng, st.get('face_texture', 'solid'), role=st.get('fill', 'mid'))
    cv.circle(cx, cy - 0.42 * s, 0.36 * s, st.get('fill', 'mid'))
    cv.stroke(geom.arc(cx, cy - 0.42 * s, 0.36 * s, 0, 2 * math.pi, 0.3), LW(st), st.get('line', 'line'))
    for k in (-1, 1):
        cv.poly(T([(k * 0.24, -0.6), (k * 0.46, -0.92), (k * 0.5, -0.5)], cx, cy, s), st.get('shade2', 'dark'))
        cv.circle(cx + k * 0.13 * s, cy - 0.48 * s, 0.05 * s, st.get('line', 'line'))
    cv.ellipse(cx, cy - 0.28 * s, 0.13 * s, 0.09 * s, st.get('light', 'light'))
    cv.circle(cx, cy - 0.33 * s, 0.05 * s, st.get('line', 'line'))
    cv.stroke([(cx - 0.08 * s, cy - 0.22 * s), (cx, cy - 0.16 * s), (cx + 0.08 * s, cy - 0.22 * s)],
              LW(st, 0.9), st.get('line', 'line'))
    cv.stroke(geom.spline([(0.3, 0.5), (0.62, 0.2), (0.5, -0.1)], 0.3), LW(st, 1.7), st.get('line', 'line'))
    for k in (-1, 1):
        cv.rect(cx + k * 0.22 * s - 0.06 * s, cy + 0.72 * s, cx + k * 0.22 * s + 0.06 * s, cy + 0.98 * s,
                st.get('shade2', 'dark'))
    return (cx - 0.62 * s, cy - 0.95 * s, cx + 0.62 * s, cy + 0.98 * s)


@motif('panda', 'beast', '熊猫')
def _panda(cv, cx, cy, s, st, rng):
    for k in (-1, 1):
        cv.circle(cx + k * 0.5 * s, cy - 0.55 * s, 0.22 * s, st.get('line', 'line'))
    head = geom.arc(cx, cy, 0.62 * s, 0, 2 * math.pi, 0.3, ry=0.56 * s)
    body(cv, head, st, rng, 'solid', role=st.get('white', 'light'))
    for k in (-1, 1):
        cv.ellipse(cx + k * 0.26 * s, cy - 0.06 * s, 0.15 * s, 0.19 * s, st.get('line', 'line'), ang=k * 0.25)
        cv.circle(cx + k * 0.26 * s, cy - 0.08 * s, 0.06 * s, st.get('white', 'light'))
    cv.circle(cx, cy + 0.18 * s, 0.08 * s, st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy + 0.22 * s, 0.14 * s, 0.3, math.pi - 0.3, 0.3), LW(st, 1.0), st.get('line', 'line'))
    return (cx - 0.72 * s, cy - 0.78 * s, cx + 0.72 * s, cy + 0.6 * s)


@motif('bamboo', 'flora', '竹')
def _bamboo(cv, cx, cy, s, st, rng):
    for k in range(3):
        x = cx + (k - 1) * 0.36 * s
        top = cy - 0.9 * s + 0.12 * s * abs(k - 1)
        cv.rect(x - 0.09 * s, top, x + 0.09 * s, cy + 0.92 * s, st.get('fill', 'mid'))
        cv.stroke([(x - 0.09 * s, top), (x - 0.09 * s, cy + 0.92 * s)], LW(st, 0.9), st.get('line', 'line'))
        cv.stroke([(x + 0.09 * s, top), (x + 0.09 * s, cy + 0.92 * s)], LW(st, 0.9), st.get('line', 'line'))
        for j in range(4):
            y = top + (0.28 + j * 0.4) * s
            cv.stroke([(x - 0.11 * s, y), (x + 0.11 * s, y)], LW(st, 1.0), st.get('line', 'line'))
        for j in range(3):
            yy = top + 0.16 * s + j * 0.34 * s
            side = 1 if (k + j) % 2 else -1
            leaf = geom.leaf(x + side * 0.28 * s, yy - 0.06 * s, 0.46 * s, side * -0.5, w=0.3)
            cv.poly(leaf, st.get('shade1', 'mid'))
            cv.stroke(np.vstack([leaf, leaf[:1]]), LW(st, 0.8), st.get('line', 'line'))
    return (cx - 0.95 * s, cy - 0.95 * s, cx + 0.95 * s, cy + 0.95 * s)


@motif('sakura', 'flora', '樱花枝')
def _sakura(cv, cx, cy, s, st, rng):
    branch = geom.spline([(-0.95, 0.7), (-0.4, 0.25), (0.2, 0.05), (0.85, -0.35)], 0.3)
    cv.tapered(T(branch, cx, cy, s), geom.wprofile(len(branch), 0.18, 0.08), st.get('shade2', 'dark'))
    spots = [(-0.42, 0.34, 1.0), (-0.05, 0.14, 1.15), (0.36, -0.04, 0.95), (0.7, -0.24, 0.8)]
    for (x, y, sc) in spots:
        px, py = cx + x * s, cy + y * s
        for k in range(5):
            a = 2 * math.pi * k / 5 + rng.uniform(-0.1, 0.1)
            petal = geom.petal(px, py, 0.3 * s * sc, a, spread=0.44)
            cv.poly(petal, st.get('light', 'white'))
            cv.stroke(np.vstack([petal, petal[:1]]), LW(st, 0.9), st.get('line', 'line'))
        cv.circle(px, py, 0.08 * s * sc, st.get('accent', 'line'))
    return (cx - s, cy - 0.5 * s, cx + 0.95 * s, cy + 0.85 * s)


@motif('koi_pair', 'sea', '双鲤')
def _koi_pair(cv, cx, cy, s, st, rng):
    for k, ang, oy in ((1, 0.0, -0.22), (-1, math.pi, 0.22)):
        sp = geom.spline([(-0.55, 0.0), (-0.2, -0.28), (0.2, -0.2), (0.5, 0.05)], 0.25)
        w = geom.wprofile(len(sp), 0.14, 0.4, mid=(0.6, 0.62))
        poly = geom.body_along(sp, w)
        poly = geom.rot(poly, ang)
        ox = cx + k * 0.1 * s
        oyy = cy + oy * s
        body(cv, T(poly, ox, oyy, s), st, rng, st.get('face_texture', 'scales'), role=st.get('fill', 'mid'))
        tail = geom.rot(np.array([(-0.5, 0.0), (-0.82, -0.34), (-0.72, 0.0), (-0.82, 0.34)]), ang)
        cv.poly(T(tail, ox, oyy, s), st.get('shade2', 'dark'))
        eye = geom.rot(np.array([[0.42, -0.02]]), ang)[0]
        cv.circle(ox + eye[0] * s, oyy + eye[1] * s, 0.06 * s, st.get('line', 'line'))
    cv.circle(cx, cy, 0.09 * s, st.get('accent', 'accent'))
    return (cx - 0.95 * s, cy - 0.95 * s, cx + 0.95 * s, cy + 0.95 * s)


@motif('moon_phase', 'sky', '月相')
def _moon_phase(cv, cx, cy, s, st, rng):
    for k, phase in enumerate((0.32, 0.5, 0.0)):
        x = cx + (k - 1) * 0.62 * s
        cv.circle(x, cy, 0.26 * s, st.get('white', 'light'))
        cv.stroke(geom.arc(x, cy, 0.26 * s, 0, 2 * math.pi, 0.3), LW(st, 1.0), st.get('line', 'line'))
        if phase:
            cv.compound([geom.arc(x, cy, 0.26 * s, 0, 2 * math.pi, 0.3),
                         geom.arc(x + phase * 0.5 * s, cy, 0.26 * s, 0, 2 * math.pi, 0.3)], st.get('line', 'line'))
    return (cx - 0.95 * s, cy - 0.3 * s, cx + 0.95 * s, cy + 0.3 * s)


def draw(name, cv, cx, cy, s, st, rng):
    """按名字画一个造型，返回包围盒。"""
    fn = MOTIFS.get(name)
    if fn is None:
        raise KeyError(f'没有这个造型：{name}（可用：{", ".join(sorted(MOTIFS))}）')
    return fn(cv, cx, cy, s, st, rng)


def by_cat(cat):
    return [k for k, v in META.items() if v['cat'] == cat]