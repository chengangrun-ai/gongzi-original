"""构图模板：决定"画面怎么摆"，与题材、风格解耦。

每个模板收到 (cv, st, rng, motif, W, H)，自己画背景/边框，再把 motif(cv, cx, cy, s, rng) 摆进去。

设计规则（拼豆工艺 + 可售卖）
- 设计坐标一律 52 格宽：S/M 是 52×52，V 是 52×104；
- V（竖幅）自动切纵向排版：环改成椭圆、主体放大、下方补竖向装饰，避免上下大片空白；
- 主体必须和边框/地面**贴住**，否则拼豆化时会被当成"飘着的碎块"删掉；
- 主体包围盒要够大，这是可售卖的底线。
"""
import math

import numpy as np

from . import brushes, geom

TEMPLATES = {}
INFO = {}


def template(name, cn=''):
    def deco(fn):
        TEMPLATES[name] = fn
        INFO[name] = cn or name
        return fn
    return deco


def LW(st, k=1.0):
    return st.get('line_width', 1.3) * k


def vert(W, H):
    return H > W * 1.5


def ring_geo(W, H):
    """环形构图的几何：竖幅用椭圆把高度吃满。返回 (rx, ry, cy)。"""
    if vert(W, H):
        return W / 2 - 2.0, H * 0.34, H * 0.42
    R = W / 2 - 2.0
    return R, R, H / 2


def _bg(cv, st, W, H, role=None):
    if st.get('bg') == 'fill':
        cv.rect(0, 0, W, H, role or st.get('bg_role', 'bg'))


def _ground(cv, st, W, H, y=None, role=None):
    """地面/水线：铺一块中间调，再压两道亮线，别做成一大块死黑。"""
    y = H * 0.78 if y is None else y
    role = role or st.get('ground') or st.get('shade1') or 'mid'
    cv.rect(0, y, W, H, role)
    cv.stroke([(0, y), (W, y)], LW(st, 1.2), st.get('line', 'line'))
    for k in (0.33, 0.66):
        yy = y + (H - y) * k
        cv.stroke([(0, yy), (W, yy)], LW(st, 0.8), st.get('light', 'light'))


def _drop(cv, st, W, H, y0, y1, role=None):
    """竖向装饰：一串菱形 + 点 + 底线，把竖幅下方的空白填起来，同时和主体连成一片。"""
    role = role or st.get('line', 'line')
    cx = W / 2
    y1 = min(y1, H - 2.5)
    if y1 - y0 < 5:
        return
    cv.stroke([(cx, y0), (cx, y1)], LW(st, 0.9), role)
    n = max(2, int((y1 - y0) // 7))
    for k in range(n):
        y = y0 + (y1 - y0) * (k + 0.5) / n
        r = 1.7 if k % 2 == 0 else 1.0
        cv.poly([(cx, y - r), (cx + r, y), (cx, y + r), (cx - r, y)], role)
    cv.stroke([(cx - 4, y1), (cx + 4, y1)], LW(st, 1.1), role)


@template('badge', '徽章')
def _badge(cv, st, rng, motif, W, H):
    cx = W / 2
    rx, ry, cy = ring_geo(W, H)
    _bg(cv, st, W, H)
    cv.stroke(geom.arc(cx, cy, rx, 0, 2 * math.pi, 0.35, ry=ry), LW(st, 1.1), st.get('line', 'line'))
    if st.get('ticks', True):
        n = st.get('tick_n', 16 if not vert(W, H) else 20)
        for k in range(n):
            a = 2 * math.pi * k / n
            ca, sa = math.cos(a), math.sin(a)
            cv.stroke([(cx + (rx - 1.8) * ca, cy + (ry - 1.8) * sa),
                       (cx + rx * ca, cy + ry * sa)], LW(st, 0.9), st.get('line', 'line'))
    motif(cv, cx, cy, min(rx, ry) * 0.92, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + ry - 1.5, H - 3)
    return dict(shape='circle', r=min(rx, ry), cy=cy)


@template('frame', '几何框')
def _frame(cv, st, rng, motif, W, H):
    cx = W / 2
    _bg(cv, st, W, H)
    kind = st.get('frame_shape') or str(rng.choice(['triangle', 'diamond', 'hex', 'circle']))
    R = W / 2 - 1.5
    cy = H * 0.40 if vert(W, H) else H / 2
    if kind == 'triangle':
        outer = geom.ngon(cx, cy + R * 0.12, R, 3, -math.pi / 2)
    elif kind == 'diamond':
        outer = geom.ngon(cx, cy, R, 4, -math.pi / 2)
    elif kind == 'hex':
        outer = geom.ngon(cx, cy, R, 6, 0)
    else:
        ry = H * 0.34 if vert(W, H) else R
        outer = geom.arc(cx, cy, R, 0, 2 * math.pi, 0.35, ry=ry)
    cv.stroke(np.vstack([outer, outer[:1]]), LW(st, 1.2), st.get('line', 'line'))
    inner = geom.inset(outer, 1.8) if kind != 'circle' else geom.arc(cx, cy, R - 1.8, 0, 2 * math.pi, 0.35)
    cv.stroke(np.vstack([inner, inner[:1]]), LW(st, 0.9), st.get('line', 'line'))
    motif(cv, cx, cy, R * 0.86, rng)
    if vert(W, H):
        _drop(cv, st, W, H, float(geom.P(outer)[:, 1].max()) - 1.5, H - 3)
    return dict(shape=kind, r=R, cy=cy)


@template('arch', '拱框')
def _arch(cv, st, rng, motif, W, H):
    cx = W / 2
    _bg(cv, st, W, H)
    top, bot, r = H * 0.05, H * 0.93, W / 2 - 3
    outer = np.vstack([geom.arc(cx, top + r, r, math.pi, 2 * math.pi, 0.35),
                       [(cx + r, bot), (cx - r, bot)]])
    cv.stroke(np.vstack([outer, outer[:1]]), LW(st, 1.2), st.get('line', 'line'))
    inner = geom.inset(outer, 2.0)
    cv.stroke(np.vstack([inner, inner[:1]]), LW(st, 0.9), st.get('line', 'line'))
    _ground(cv, st, W, H, bot - 1.0)
    _s = min(W * 0.42, (bot - top) * 0.34)
    motif(cv, cx, bot - _s * 0.92, _s, rng)
    return dict(shape='arch')


@template('fullbleed', '满幅')
def _fullbleed(cv, st, rng, motif, W, H):
    cx, cy = W / 2, H / 2
    _bg(cv, st, W, H)
    s = W * 0.48 * st.get('fill_ratio', 0.92) if vert(W, H) else min(W, H) / 2 * st.get('fill_ratio', 0.86)
    motif(cv, cx, cy, s, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + s * 0.88, H - 3)
    return dict(shape='bleed')


@template('medallion', '圆章')
def _medallion(cv, st, rng, motif, W, H):
    cx = W / 2
    rx, ry, cy = ring_geo(W, H)
    _bg(cv, st, W, H)
    n = st.get('medallion_n', 16)
    for k in range(n):
        a = 2 * math.pi * k / n
        px, py = cx + rx * 0.60 * math.cos(a), cy + ry * 0.60 * math.sin(a)
        cv.poly(geom.petal(px, py, min(rx, ry) * 0.30, a, spread=0.15), st.get('shade1', 'dark'))
    for k, w in ((1.0, 1.2), (0.64, 0.9)):
        cv.stroke(geom.arc(cx, cy, rx * k, 0, 2 * math.pi, 0.35, ry=ry * k), LW(st, w), st.get('line', 'line'))
    motif(cv, cx, cy, min(rx, ry) * 0.80, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + ry - 1.5, H - 3)
    return dict(shape='circle', r=min(rx, ry), cy=cy)


@template('poster', '海报')
def _poster(cv, st, rng, motif, W, H):
    cx = W / 2
    _bg(cv, st, W, H)
    hy = H * 0.70
    if st.get('poster_rays', True):
        brushes.rays(cv, cx, hy, 4, max(W, H) * 0.9, st.get('ray_n', 14), LW(st, 0.9), st.get('light', 'light'))
    _ground(cv, st, W, H, hy)
    cv.stroke([(0, hy), (W, hy)], LW(st, 1.2), st.get('line', 'line'))
    _s = min(W * 0.42, hy * 0.48)
    motif(cv, cx, hy - _s * 0.92, _s, rng)
    return dict(shape='poster', cy=hy - _s * 0.92)


@template('banner', '绶带')
def _banner(cv, st, rng, motif, W, H):
    cx = W / 2
    _bg(cv, st, W, H)
    by = H * 0.78
    cv.poly([(cx - W * 0.42, by), (cx + W * 0.42, by), (cx + W * 0.42, by + H * 0.09),
             (cx - W * 0.42, by + H * 0.09)], st.get('shade1', 'dark'))
    cv.stroke([(cx - W * 0.42, by), (cx + W * 0.42, by), (cx + W * 0.42, by + H * 0.09),
               (cx - W * 0.42, by + H * 0.09), (cx - W * 0.42, by)], LW(st, 1.0), st.get('line', 'line'))
    for k in range(3):
        cv.stroke([(cx - W * 0.28 + k * W * 0.28, by + H * 0.045), (cx - W * 0.2 + k * W * 0.28, by + H * 0.045)],
                  LW(st, 1.1), st.get('light', 'light'))
    _s = min(W * 0.44, by * 0.50)
    motif(cv, cx, by - _s * 0.92, _s, rng)
    return dict(shape='banner')


@template('wreath', '花环')
def _wreath(cv, st, rng, motif, W, H):
    cx = W / 2
    rx, ry, cy = ring_geo(W, H)
    _bg(cv, st, W, H)
    n = st.get('wreath_n', 10)
    for k in range(n):
        a = 2 * math.pi * k / n
        p = geom.leaf(cx + rx * 0.82 * math.cos(a), cy + ry * 0.82 * math.sin(a),
                      min(rx, ry) * 0.34, a + math.pi / 2, w=0.28)
        cv.poly(p, st.get('shade1', 'dark'))
    cv.stroke(geom.arc(cx, cy, rx * 0.82, 0, 2 * math.pi, 0.35, ry=ry * 0.82), LW(st, 0.9), st.get('line', 'line'))
    motif(cv, cx, cy, min(rx, ry) * 0.80, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + ry * 0.80, H - 3)
    return dict(shape='circle', r=min(rx, ry), cy=cy)


@template('radial', '放射')
def _radial(cv, st, rng, motif, W, H):
    cx = W / 2
    rx, ry, cy = ring_geo(W, H)
    _bg(cv, st, W, H)
    brushes.sunburst(cv, cx, cy, max(rx, ry) * 1.55, st.get('sun_n', 20), st.get('light', 'light'), inner=0.42)
    r2 = min(rx, ry) * 0.66
    cv.circle(cx, cy, r2, st.get('bg_role', 'bg') if st.get('bg') == 'fill' else 'white')
    cv.stroke(geom.arc(cx, cy, r2, 0, 2 * math.pi, 0.35), LW(st, 1.1), st.get('line', 'line'))
    motif(cv, cx, cy, r2 * 0.90, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + r2 - 1.5, H - 3)
    return dict(shape='circle', r=r2, cy=cy)


@template('window', '彩窗')
def _window(cv, st, rng, motif, W, H):
    cx = W / 2
    rx, ry, cy = ring_geo(W, H)
    _bg(cv, st, W, H)
    n = st.get('pane_n', 8)
    cv.circle(cx, cy, max(rx, ry), st.get('bg_role', 'bg') if st.get('bg') == 'fill' else 'light')
    for k in range(n):
        a0 = 2 * math.pi * k / n
        a1 = a0 + 2 * math.pi / n
        role = (st.get('pane_roles') or ['light', 'accent', 'mid'])[k % 3]
        cv.poly([(cx, cy), (cx + rx * math.cos(a0), cy + ry * math.sin(a0)),
                 (cx + rx * math.cos(a1), cy + ry * math.sin(a1))], role)
    for k in range(n):
        a = 2 * math.pi * k / n
        cv.stroke([(cx, cy), (cx + rx * math.cos(a), cy + ry * math.sin(a))], LW(st, 1.2), st.get('line', 'line'))
    cv.stroke(geom.arc(cx, cy, rx, 0, 2 * math.pi, 0.35, ry=ry), LW(st, 1.4), st.get('line', 'line'))
    r2 = min(rx, ry) * 0.52
    cv.circle(cx, cy, r2, st.get('bg_role', 'bg') if st.get('bg') == 'fill' else 'white')
    cv.stroke(geom.arc(cx, cy, r2, 0, 2 * math.pi, 0.35), LW(st, 1.1), st.get('line', 'line'))
    motif(cv, cx, cy, r2 * 0.94, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + ry - 1.5, H - 3)
    return dict(shape='circle', r=r2, cy=cy)


@template('tile', '纹样铺贴')
def _tile(cv, st, rng, motif, W, H):
    _bg(cv, st, W, H)
    n = st.get('tile_n', 2)
    step = W / n
    rows = max(1, int(round(H / step)))
    for j in range(rows):
        for i in range(n):
            motif(cv, step * (i + 0.5), step * (j + 0.5), step * 0.44, rng)
    return dict(shape='tile')


@template('sticker', '贴纸')
def _sticker(cv, st, rng, motif, W, H):
    cx = W / 2
    cy = H * 0.44 if vert(W, H) else H / 2
    s = W / 2 * 0.82 if vert(W, H) else min(W, H) / 2 * 0.82
    _bg(cv, st, W, H)
    motif(cv, cx, cy, s, rng)
    if vert(W, H):
        _drop(cv, st, W, H, cy + s * 0.88, H - 3)
    return dict(shape='sticker')


@template('card', '卡片')
def _card(cv, st, rng, motif, W, H):
    cx, cy = W / 2, H / 2
    m = 2.4
    _bg(cv, st, W, H)
    cv.rect(m, m, W - m, H - m, st.get('bg_role', 'bg') if st.get('bg') == 'fill' else 'white', r=1.2)
    cv.stroke([(m, m), (W - m, m), (W - m, H - m), (m, H - m), (m, m)], LW(st, 1.3), st.get('line', 'line'))
    cv.stroke([(m + 1.4, m + 1.4), (W - m - 1.4, m + 1.4), (W - m - 1.4, H - m - 1.4), (m + 1.4, H - m - 1.4), (m + 1.4, m + 1.4)],
              LW(st, 0.8), st.get('line', 'line'))
    s = min(W * 0.40, H * 0.40)
    motif(cv, cx, cy - H * 0.02, s, rng)
    for k in range(3):
        y = H - m - 3.0 - k * 1.6
        cv.stroke([(m + 3, y), (W - m - 3 - k * 4, y)], LW(st, 0.8), st.get('light', 'light'))
    return dict(shape='card')


@template('corner', '角饰')
def _corner(cv, st, rng, motif, W, H):
    cx, cy = W / 2, H / 2
    _bg(cv, st, W, H)
    s = W * 0.40 if vert(W, H) else min(W, H) * 0.38
    motif(cv, cx, cy, s, rng)
    for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
        x0 = 2.2 if sx > 0 else W - 2.2
        y0 = 2.2 if sy > 0 else H - 2.2
        cv.stroke([(x0, y0 + sy * 7), (x0, y0), (x0 + sx * 7, y0)], LW(st, 1.1), st.get('line', 'line'))
        brushes.spiral_curl(cv, x0 + sx * 3.0, y0 + sy * 3.0, 1.5, 1.2, LW(st, 1.0), st.get('line', 'line'))
    if vert(W, H):
        _drop(cv, st, W, H, cy + s * 0.88, H - 3)
    return dict(shape='corner')


@template('scene', '场景')
def _scene(cv, st, rng, motif, W, H):
    """风景/照片用：天空 → 远山 → 主体 → 地面，分层构图。
    纸底风格不画天空，只画"贴住地面"的层次，避免飘着的云被当成碎块删掉。"""
    cx = W / 2
    hy = H * 0.64
    fill_bg = st.get('bg') == 'fill'
    _bg(cv, st, W, H)
    if fill_bg:
        cv.rect(0, 0, W, hy, st.get('sky_role', 'light'))
        if rng.random() < 0.75:
            sx = cx + rng.uniform(-0.26, 0.26) * W
            sy = hy * rng.uniform(0.28, 0.42)
            cv.circle(sx, sy, min(W, H) * 0.085, st.get('accent', 'light'))
            if st.get('scene_rays', True):
                brushes.rays(cv, sx, sy, min(W, H) * 0.1, min(W, H) * 0.15, 10, LW(st, 0.8), st.get('light', 'light'))
        for k in range(int(st.get('cloud_n', 2))):
            cx2 = cx + rng.uniform(-0.4, 0.4) * W
            cy2 = hy * rng.uniform(0.12, 0.45)
            cv.poly(geom.blob(cx2, cy2, W * rng.uniform(0.08, 0.13), rng, lobes=4, rough=0.12),
                    st.get('white', 'light'))
    # 远山（两层，贴着地平线）
    for k, (role, up) in enumerate(((st.get('hill_far', 'mid'), 0.34), (st.get('hill_near', 'dark'), 0.2))):
        xs = np.linspace(-2, W + 2, 9)
        ys = hy - up * H * (0.6 + 0.5 * rng.random(9)) * (1 - 0.35 * k)
        ridge = geom.spline(np.stack([xs, ys], 1), 0.5)
        cv.poly(np.vstack([ridge, [(W + 2, hy + 1), (-2, hy + 1)]]), role)
    _ground(cv, st, W, H, hy)
    # 前景剪影（左下角/右下角各一丛，和地面连在一起）
    for k in (-1, 1):
        x = cx + k * W * 0.36
        for j in range(3):
            h = H * rng.uniform(0.08, 0.16)
            cv.poly([(x + (j - 1) * W * 0.05, H - 1), (x + (j - 1) * W * 0.05 - h * 0.28, H - 1 - h),
                     (x + (j - 1) * W * 0.05 + h * 0.28, H - 1 - h)], st.get('shade2', 'dark'))
    _s = min(W * 0.42, hy * 0.52)
    motif(cv, cx, hy - _s * 0.92, _s, rng)
    return dict(shape='scene')


@template('horizon', '地平线')
def _horizon(cv, st, rng, motif, W, H):
    cx = W / 2
    _bg(cv, st, W, H)
    hy = H * 0.62 if vert(W, H) else H * 0.64
    _ground(cv, st, W, H, hy)
    for k in range(3):
        y = hy - 1.5 - k * 1.8
        xs = np.linspace(-1, W + 1, 40)
        cv.stroke(np.stack([xs, y + 0.5 * np.sin(xs / (W / 3.5) * 2 * math.pi)], 1), LW(st, 0.9), st.get('light', 'light'))
    _s = min(W * 0.42, hy * 0.48)
    motif(cv, cx, hy - _s * 0.92, _s, rng)
    return dict(shape='horizon')


@template('emblem', '盾徽')
def _emblem(cv, st, rng, motif, W, H):
    """盾形外框：上方平肩、下方收尖，适合做"店徽/家族徽"。"""
    cx = W / 2
    _bg(cv, st, W, H)
    top, bot = H * 0.12, H * 0.90
    half = W * 0.38
    shield = np.array([
        (cx - half, top), (cx - half * 0.55, top - H * 0.045), (cx + half * 0.55, top - H * 0.045),
        (cx + half, top), (cx + half, top + (bot - top) * 0.42),
        (cx + half * 0.62, bot - (bot - top) * 0.16), (cx, bot),
        (cx - half * 0.62, bot - (bot - top) * 0.16), (cx - half, top + (bot - top) * 0.42)])
    cv.stroke(np.vstack([shield, shield[:1]]), LW(st, 1.4), st.get('line', 'line'))
    inner = geom.inset(shield, 2.2)
    cv.stroke(np.vstack([inner, inner[:1]]), LW(st, 0.9), st.get('line', 'line'))
    motif(cv, cx, top + (bot - top) * 0.46, min(half * 0.78, (bot - top) * 0.30), rng)
    if vert(W, H):
        _drop(cv, st, W, H, bot - 1.5, H - 3)
    return dict(shape='emblem', cy=top + (bot - top) * 0.46)


@template('split', '上下分格')
def _split(cv, st, rng, motif, W, H):
    """上下两格：上面主体、下面一个同题材小图，做"主图 + 说明图"的排版。"""
    cx = W / 2
    _bg(cv, st, W, H)
    mid = H * 0.62
    cv.stroke([(0, mid), (W, mid)], LW(st, 1.3), st.get('line', 'line'))
    s1 = min(W * 0.40, mid * 0.40)
    motif(cv, cx, mid - s1 * 0.95, s1, rng)
    s2 = min(W * 0.20, (H - mid) * 0.34)
    motif(cv, cx, mid + (H - mid) * 0.52, s2, rng)
    return dict(shape='split', cy=mid - s1 * 0.95)


def apply(name, cv, st, rng, motif, W, H):
    fn = TEMPLATES.get(name)
    if fn is None:
        raise KeyError(f'没有这个构图：{name}（可用：{", ".join(sorted(TEMPLATES))}）')
    return fn(cv, st, rng, motif, W, H)
