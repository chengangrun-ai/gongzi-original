"""绘图引擎：矢量显示列表 → 拼豆调色板索引网格（+ 高清原画）。

坐标单位是"格"（1 颗豆），设计画布一律 52 格宽；zoom 把它放大成真实网格（如 1.5 → 78 格）。
渲染方式：先在 S 倍超采样缓冲上逐形状栅格化（PIL 多边形，无抗锯齿），
再按"加权多数表决"落到每颗豆——线、点缀权重高，细黑线和小红点不会被灰吞掉。
只用 numpy + Pillow，不需要 cairo / OpenCV，Windows 直接能跑。
"""
import contextlib
import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from . import geom
from .palette import PAPER

BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0 - 0.5 + 1 / 32


def _finite(value, name, minimum=None):
    value = float(value)
    if not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f'{name} 必须是有限数值' + (f'，且不能小于 {minimum}' if minimum is not None else ''))
    return value


def _sampling(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f'{name} 必须是正整数')
    return int(value)


def _field(value, shape, name, unit=False):
    try:
        out = np.broadcast_to(np.asarray(value, float), shape).copy()
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{name} 的形状必须能匹配网格 {shape}') from exc
    if not np.isfinite(out).all() or (unit and np.any((out < 0) | (out > 1))):
        raise ValueError(f'{name} 必须是有限数值' + ('，且在 0 到 1 之间' if unit else ''))
    return out


def pixel_line(g):
    """网格坐标折线 → 像素完美的单颗线（8 邻连通、去掉 L 形拐角的多余格）。"""
    g = geom.resample(g, 0.1) if len(g) >= 2 else g
    out = []
    for x, y in g:
        cc = (int(math.floor(x)), int(math.floor(y)))
        if out and out[-1] == cc:
            continue
        if out and max(abs(cc[0] - out[-1][0]), abs(cc[1] - out[-1][1])) > 1:
            for _ in range(10):
                m = (out[-1][0] + int(np.sign(cc[0] - out[-1][0])), out[-1][1] + int(np.sign(cc[1] - out[-1][1])))
                out.append(m)
                if max(abs(cc[0] - m[0]), abs(cc[1] - m[1])) <= 1:
                    break
        out.append(cc)
        while len(out) >= 3:
            a, b, d = out[-3], out[-2], out[-1]
            if abs(a[0] - d[0]) == 1 and abs(a[1] - d[1]) == 1:
                out.pop(-2)
            else:
                break
    return out


class Canvas:
    """显示列表式画布。所有绘制函数都接受"角色名"（line/dark/mid/light/white/accent…）。"""

    THIN = 1.35      # 网格里宽度小于这个的线，按单颗线落格（不会断、不会变双线）
    DOT = 0.80       # 网格里半径小于这个的圆点，直接落成 1 颗豆

    def __init__(self, W, H, pal, seed=0, zoom=1.0):
        self.W, self.H, self.z = (_finite(v, n, 0) for v, n in ((W, '宽度'), (H, '高度'), (zoom, '缩放')))
        if min(self.W, self.H, self.z) <= 0:
            raise ValueError('画布宽高和缩放必须大于零')
        if not np.isfinite([self.W * self.z, self.H * self.z]).all():
            raise ValueError('缩放后的画布尺寸溢出')
        self.GW, self.GH = int(round(self.W * self.z)), int(round(self.H * self.z))
        if min(self.GW, self.GH) < 1:
            raise ValueError('缩放后画布至少需要一行一列格子')
        self.pal = pal
        self._index_dtype = next(dtype for dtype in (np.int8, np.int16, np.int32, np.int64)
                                 if len(pal) - 1 <= np.iinfo(dtype).max)
        self.ops = []
        self.effects = []
        self.rng = np.random.default_rng(seed)

    # ------------------------------------------------------------ 记录
    def _idx(self, role):
        idx = self.pal.index(role)
        if not 0 <= idx < len(self.pal):
            raise ValueError('颜色索引超出调色板范围')
        return idx

    def _add(self, role, kind, payload, snap=None):
        if role is None:
            return
        self.ops.append((kind, self._idx(role), payload, snap))

    def poly(self, pts, role='line'):
        pts = geom.P(pts)
        if len(pts) >= 3:
            self._add(role, 'fill', [pts])

    def compound(self, polys, role='line'):
        """多个闭合轮廓按奇偶规则填充（做镂空、环形、窗格）。"""
        ps = [geom.P(p) for p in polys if len(geom.P(p)) >= 3]
        if ps:
            self._add(role, 'fill', ps)

    def stroke(self, pts, w=1.3, role='line', close=False, cap='round'):
        w = _finite(w, '线宽', 0)
        if cap not in ('round', 'butt'):
            raise ValueError('线帽只能是 round 或 butt')
        pts = geom.P(pts)
        if len(pts) < 2 or w == 0:
            return
        snap = self._snap_line(pts, close) if w * self.z < self.THIN else None
        self._add(role, 'stroke', (pts, float(w), close, cap), snap)

    def tapered(self, pts, widths, role='line', caps=True):
        pts = geom.P(pts)
        if len(pts) < 2 or role is None:
            return
        w = geom.widths_for(pts, widths)
        self.poly(geom.taper_outline(pts, w), role)
        if caps:
            for k in (0, -1):
                if w[k] > 0.3:
                    self.circle(*pts[k], w[k] / 2, role)
        thin = (w * self.z < self.THIN) & (w * self.z > 0.3)
        if thin.any():
            idx = np.nonzero(thin)[0]
            for r in np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1):
                if len(r) >= 2:
                    self.ops.append(('stroke', self._idx(role), None, self._snap_line(pts[r[0]:r[-1] + 1])))

    def circle(self, x, y, r, role='line'):
        x, y, r = _finite(x, '圆心 x'), _finite(y, '圆心 y'), _finite(r, '半径', 0)
        if r == 0:
            return
        snap = [(int(math.floor(x * self.z)), int(math.floor(y * self.z)))] if r * self.z < self.DOT else None
        self._add(role, 'dot', (float(x), float(y), float(r)), snap)

    def ellipse(self, x, y, rx, ry, role='line', ang=0.0):
        self.poly(geom.rot(geom.arc(x, y, rx, 0, 2 * math.pi, ry=ry), ang, (x, y)), role)

    def ring(self, x, y, r, w, role='line'):
        x, y, r, w = (_finite(v, n, m) for v, n, m in
                       ((x, '圆心 x', None), (y, '圆心 y', None), (r, '半径', 0), (w, '线宽', 0)))
        if r == 0 or w == 0:
            return
        snap = self._snap_line(geom.arc(x, y, r, 0, 2 * math.pi, 0.1), True) if w * self.z < self.THIN else None
        self._add(role, 'stroke', (geom.arc(x, y, r, 0, 2 * math.pi, 0.15), float(w), True, 'round'), snap)

    def rect(self, x0, y0, x1, y1, role='line', r=0.0):
        self.poly(geom.rounded_rect(x0, y0, x1, y1, r) if r > 0 else
                  [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], role)

    def pixels(self, cells_g, role='line'):
        """直接点名网格格子（网格坐标）；原画里画成小圆点。"""
        cl = [(int(a), int(b)) for a, b in cells_g]
        if cl:
            self._add(role, 'pixel', cl, cl)

    @contextlib.contextmanager
    def clip(self, pts):
        self.ops.append(('push', None, geom.P(pts), None))
        try:
            yield self
        finally:
            self.ops.append(('pop', None, None, None))

    def _snap_line(self, pts, close=False):
        g = geom.P(pts) * self.z
        if close:
            g = np.vstack([g, g[:1]])
        return pixel_line(g)

    # ------------------------------------------------------------ 格级效果
    def effect(self, fn):
        self.effects.append(fn)

    def mask(self, pts, cover=0.5, S=6):
        """闭合图形 → 格级布尔遮罩（网格分辨率）。"""
        S = _sampling(S, '遮罩采样数')
        cover = _finite(cover, '遮罩覆盖率', 0)
        if cover > 1:
            raise ValueError('遮罩覆盖率必须在 0 到 1 之间')
        pts = geom.P(pts)
        if len(pts) < 3:
            return np.zeros((self.GH, self.GW), bool)
        gh, gw = self.GH * S, self.GW * S
        im = Image.new('L', (gw, gh), 0)
        sc = S * self.z
        ImageDraw.Draw(im).polygon([(x * sc, y * sc) for x, y in pts], fill=255)
        a = np.asarray(im) > 127
        return a.reshape(self.GH, S, self.GW, S).mean(axis=(1, 3)) >= cover

    def stipple(self, mask, density, role='line', rng=None, spacing=True, over=None):
        """点刺：在 mask 内按 density 撒单颗豆（默认只落在纸色格子上）。"""
        mask = self._effect_mask(mask)
        dens = _field(density, mask.shape, '点刺密度', unit=True)
        rng = rng if rng is not None else self.rng
        tone = self._idx(role)
        ov = [PAPER, self._idx('white')] if over is None else [self._idx(r) for r in over]
        randoms = None

        def fn(g):
            nonlocal randoms
            H, W = g.shape
            if randoms is None:
                randoms = rng.permutation(H * W), rng.random(H * W)
            order, r = randoms
            for k in order:
                y, x = divmod(int(k), W)
                if not mask[y, x] or g[y, x] not in ov or r[k] >= dens[y, x]:
                    continue
                if spacing and any(0 <= y + dy < H and 0 <= x + dx < W and g[y + dy, x + dx] == tone
                                   for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                    continue
                g[y, x] = tone
        self.effects.append(fn)

    def shade(self, mask, field, levels, over=None, dither=0.6, jitter=0.0):
        """格级渐变：field∈[0,1]（0 = 最亮）量化到 levels（角色名列表，亮→暗）。"""
        mask = self._effect_mask(mask)
        F = _field(field, mask.shape, '渐变亮度', unit=True)
        levels = tuple(levels)
        if not levels:
            raise ValueError('渐变至少需要一种颜色')
        dither, jitter = _finite(dither, '抖动强度', 0), _finite(jitter, '随机强度', 0)
        lv = np.array([self._idx(r) for r in levels])
        ov = [int(lv[0])] if over is None else [self._idx(r) for r in over]
        rng = self.rng
        noise = None

        def fn(g):
            nonlocal noise
            H, W = g.shape
            k = len(lv) - 1
            yy, xx = np.mgrid[0:H, 0:W]
            if noise is None:
                noise = rng.uniform(-jitter, jitter, (H, W)) if jitter else 0
            th = BAYER4[yy % 4, xx % 4] * dither + noise
            q = np.clip(np.floor(F * k + 0.5 + th), 0, k).astype(int)
            m = mask & np.isin(g, ov)
            g[m] = lv[q[m]]
        self.effects.append(fn)

    def _effect_mask(self, mask):
        mask = np.asarray(mask)
        if mask.shape != (self.GH, self.GW):
            raise ValueError(f'效果遮罩必须匹配网格 {(self.GH, self.GW)}')
        if not np.isin(mask, [0, 1]).all():
            raise ValueError('效果遮罩只能包含布尔值或 0/1')
        return mask.astype(bool, copy=True)

    def paint_cells(self, cells_xy, role):
        """直接指定若干格（网格坐标 x, y）的颜色。"""
        tone = self._idx(role)
        pc = [(int(x), int(y)) for x, y in cells_xy]

        def fn(g):
            H, W = g.shape
            for x, y in pc:
                if 0 <= x < W and 0 <= y < H:
                    g[y, x] = tone
        self.effects.append(fn)

    # ------------------------------------------------------------ 渲染
    def _paint(self, buf, clip, kind, idx, payload, snap, sc, art=False):
        """把一个显示项直接画进索引缓冲。"""
        gh, gw = buf.shape
        if art and snap is not None:
            # 原画里不用"单颗线"落格，直接画真实几何（细线给一个最小可见宽度）
            if payload is None:
                return
            if kind == 'stroke':
                pts, w, close, cap = payload
                self._paint_stroke(buf, clip, pts, max(w, 0.34), close, cap, idx=idx, sc=sc)
            elif kind == 'dot':
                x, y, r = payload
                self._paint_dot(buf, clip, x, y, max(r, 0.17), idx, sc)
            elif kind == 'pixel':
                for gx, gy in payload:
                    if 0 <= gx < self.GW and 0 <= gy < self.GH:
                        self._paint_dot(buf, clip, (gx + 0.5) / self.z, (gy + 0.5) / self.z,
                                        0.42 / self.z, idx, sc)
            return
        if snap is not None:
            for gx, gy in snap:
                if not (0 <= gx < self.GW and 0 <= gy < self.GH):
                    continue
                a, b = int(round(gx / self.z * sc)), int(round(gy / self.z * sc))
                c, e = int(round((gx + 1) / self.z * sc)), int(round((gy + 1) / self.z * sc))
                a, b = max(0, a), max(0, b)
                c, e = min(gw, c), min(gh, e)
                if c > a and e > b:
                    sub = buf[b:e, a:c]
                    if clip is not None:
                        sub[clip[b:e, a:c]] = idx
                    else:
                        sub[:] = idx
            return
        if payload is None:
            return
        if kind == 'fill':
            if len(payload) == 1:
                self._paint_poly(buf, clip, payload[0], idx, sc)
            else:
                m = None
                for p in payload:
                    im = Image.fromarray((self._poly_mask(p, sc, gh, gw) * 255).astype(np.uint8)).convert('1')
                    m = im if m is None else ImageChops.logical_xor(m, im)
                m = np.asarray(m)
                self._assign(buf, clip, m, idx)
        elif kind == 'stroke':
            self._paint_stroke(buf, clip, *payload, idx=idx, sc=sc)
        elif kind == 'dot':
            self._paint_dot(buf, clip, *payload, idx=idx, sc=sc)

    @staticmethod
    def _assign(buf, clip, m, idx):
        if clip is None:
            buf[m] = idx
        else:
            buf[m & clip] = idx

    @staticmethod
    def _bbox(pts, pad=0):
        p = np.asarray(pts, float)
        return (int(math.floor(p[:, 0].min())) - pad, int(math.floor(p[:, 1].min())) - pad,
                int(math.ceil(p[:, 0].max())) + pad + 1, int(math.ceil(p[:, 1].max())) + pad + 1)

    def _poly_mask(self, pts, sc, gh, gw):
        p = geom.P(pts) * sc
        out = np.zeros((gh, gw), bool)
        x0, y0, x1, y1 = self._bbox(p, 1)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
        if x1 <= x0 or y1 <= y0:
            return out
        im = Image.new('L', (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(im).polygon([(x - x0, y - y0) for x, y in p], fill=255)
        out[y0:y1, x0:x1] = np.asarray(im) > 127
        return out

    def _paint_poly(self, buf, clip, pts, idx, sc):
        m = self._poly_mask(pts, sc, buf.shape[0], buf.shape[1])
        self._assign(buf, clip, m, idx)

    def _paint_stroke(self, buf, clip, pts, w, close, cap, idx, sc):
        p = geom.P(pts) * sc
        wid = max(1, int(round(w * sc)))
        gh, gw = buf.shape
        if wid <= 2:                                  # 极细线：直接画线，接缝看不出来
            if close:
                p = np.vstack([p, p[:1]])
            x0, y0, x1, y1 = self._bbox(p, wid + 2)
            x0, y0, x1, y1 = max(0, x0), max(0, y0), min(gw, x1), min(gh, y1)
            if x1 <= x0 or y1 <= y0:
                return
            im = Image.new('L', (x1 - x0, y1 - y0), 0)
            ImageDraw.Draw(im).line([(x - x0, y - y0) for x, y in p], fill=255, width=wid)
            m = np.zeros((gh, gw), bool)
            m[y0:y1, x0:x1] = np.asarray(im) > 127
            self._assign(buf, clip, m, idx)
            return
        # 粗线：用"偏移轮廓多边形"填充，避免 PIL 逐段画线留下的 1px 接缝
        if close:
            p = np.vstack([p, p[:1]])
        half = w * sc / 2.0
        a = geom.offset(p, half)
        b = geom.offset(p, -half)
        poly = np.vstack([a, b[::-1]])
        self._paint_poly(buf, clip, poly, idx, 1.0)   # 已经是像素坐标，sc 传 1
        if cap == 'round' and not close:
            r = half
            for cx, cy in (p[0], p[-1]):
                self._paint_dot(buf, clip, cx, cy, r, idx, 1.0)

    def _paint_dot(self, buf, clip, x, y, r, idx, sc):
        cx, cy, rr = x * sc, y * sc, r * sc
        gh, gw = buf.shape
        x0, y0 = max(0, int(cx - rr) - 1), max(0, int(cy - rr) - 1)
        x1, y1 = min(gw, int(cx + rr) + 2), min(gh, int(cy + rr) + 2)
        if x1 <= x0 or y1 <= y0:
            return
        im = Image.new('L', (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(im).ellipse([cx - rr - x0, cy - rr - y0, cx + rr - x0, cy + rr - y0], fill=255)
        m = np.zeros((gh, gw), bool)
        m[y0:y1, x0:x1] = np.asarray(im) > 127
        self._assign(buf, clip, m, idx)

    def _render(self, gh, gw, sc, art=False):
        buf = np.zeros((gh, gw), self._index_dtype)
        clip = None
        stack = []
        for kind, idx, payload, snap in self.ops:
            if kind == 'push':
                m = self._poly_mask(payload, sc, gh, gw)
                stack.append(clip)
                clip = m if clip is None else (clip & m)
            elif kind == 'pop':
                clip = stack.pop()
            else:
                self._paint(buf, clip, kind, idx, payload, snap, sc, art)
        return buf

    def grid(self, S=8, effects=True):
        """超采样索引 → 每颗豆一个调色板索引（按配色容量选整数类型，0 = 不放豆）。"""
        S = _sampling(S, '网格采样数')
        buf = self._render(self.GH * S, self.GW * S, S * self.z)
        H, W, N = self.GH, self.GW, len(self.pal)
        cell = (np.arange(self.GH * S)[:, None] // S) * W + (np.arange(self.GW * S)[None, :] // S)
        comb = cell.ravel().astype(np.int64) * N + buf.ravel().astype(np.int64)
        cnt = np.bincount(comb, minlength=H * W * N).reshape(H * W, N).astype(np.float32)
        g = (cnt * self.pal.weight[None, :]).argmax(1).reshape(H, W).astype(self._index_dtype)
        if effects:
            for fn in self.effects:
                fn(g)
        return g

    def grid_no_effects(self, S=8):
        return self.grid(S, effects=False)

    def art(self, px=20, ss=2, grid=None):
        """高清原画：同一份显示列表在高分辨率下重放，再降采样得到抗锯齿。"""
        px, ss = _sampling(px, '原画格像素'), _sampling(ss, '原画采样数')
        sc = float(px * ss)
        gh, gw = int(round(self.H * px * ss)), int(round(self.W * px * ss))
        buf = self._render(gh, gw, sc, art=True)
        if grid is not None:
            grid = np.asarray(grid)
            if grid.shape != (self.GH, self.GW) or not np.issubdtype(grid.dtype, np.integer):
                raise ValueError('原画叠加网格必须是尺寸匹配的整数网格')
            if np.any((grid < 0) | (grid >= len(self.pal))):
                raise ValueError('原画叠加网格颜色索引超出调色板范围')
            base = self.grid_no_effects()
            ys, xs = np.nonzero((grid != base) & (grid > PAPER))
            for y, x in zip(ys, xs):
                idx = int(grid[y, x])
                rgb = self.pal.tone_rgb(idx)
                if 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] > 238:
                    continue                      # 白色托底在纸底上看不见，不画（避免一圈白噪点）
                self._paint_dot(buf, None, (x + 0.5) / self.z, (y + 0.5) / self.z, 0.42 / self.z, idx, sc)
        lut = np.zeros((len(self.pal), 3), np.uint8)
        for i in range(len(self.pal)):
            lut[i] = self.pal.tone_rgb(i)
        im = Image.fromarray(lut[buf]).resize((max(1, gw // ss), max(1, gh // ss)), Image.BOX)
        return im


# ---------------------------------------------------------------- 密度场
def lin_density(shape, p0, p1, d0, d1, gamma=1.0):
    p0, p1 = geom.P([p0, p1])
    gamma = _finite(gamma, '密度曲线 gamma', 0)
    d0, d1 = _finite(d0, '起点密度', 0), _finite(d1, '终点密度', 0)
    if gamma <= 0 or max(d0, d1) > 1 or np.array_equal(p0, p1):
        raise ValueError('密度需在 0 到 1 之间，轴端点不能重合，gamma 必须大于零')
    yy, xx = _yx(shape)
    v = np.asarray(p1, float) - p0
    L2 = v @ v
    u = np.clip(((xx - p0[0]) * v[0] + (yy - p0[1]) * v[1]) / L2, 0, 1) ** gamma
    return d0 + (d1 - d0) * u


def rad_density(shape, c, r0, r1, d0, d1, gamma=1.0):
    c = geom.P([c])[0]
    r0, r1 = _finite(r0, '内半径', 0), _finite(r1, '外半径', 0)
    d0, d1 = _finite(d0, '起点密度', 0), _finite(d1, '终点密度', 0)
    gamma = _finite(gamma, '密度曲线 gamma', 0)
    if r1 <= r0 or gamma <= 0 or max(d0, d1) > 1:
        raise ValueError('外半径必须大于内半径，gamma 必须大于零，密度需在 0 到 1 之间')
    yy, xx = _yx(shape)
    u = np.clip((np.hypot(xx - c[0], yy - c[1]) - r0) / (r1 - r0), 0, 1) ** gamma
    return d0 + (d1 - d0) * u


def _yx(shape):
    if hasattr(shape, 'yx'):
        return shape.yx()
    H, W = shape
    H, W = _sampling(H, '密度场高度'), _sampling(W, '密度场宽度')
    return np.mgrid[0:H, 0:W] + 0.5
