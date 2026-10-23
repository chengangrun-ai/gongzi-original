"""配方合成器：风格 × 题材 × 构图 × 种子 → 一款原创作品。

"原创"落在三件事上：
1. 画面由代码从零绘制（样条、几何、程序化纹样），不读任何参考图像素；
2. 同一题材在不同构图/纹理/种子下真的长得不一样，不是换个颜色；
3. 每款都有固定种子，能逐格复现，可作存证。
"""
import copy
import math
from collections.abc import Mapping
from numbers import Integral

import numpy as np

from . import beadify, brushes, comp, motifs, palette, stylepack
from .canvas import Canvas

SUFFIX = ['', '·贰', '·叁', '·肆', '·伍', '·陆']


def _fmt_mix(style, n, rng):
    """按风格包给的画幅配比，抽出 n 个画幅（保证配比大致对得上）。"""
    mix = style.get('formats') or {'S': 1.0}
    keys = [k for k in ('S', 'M', 'V') if mix.get(k, 0) > 0]
    if not keys:
        keys = ['S']
    w = np.array([mix.get(k, 0) for k in keys], float)
    w = w / w.max()                     # 大但有限的权重也不能在求和时溢出
    w = w / w.sum()
    cnt = np.floor(w * n).astype(int)
    for i in range(n - cnt.sum()):
        cnt[int(np.argmax(w * n - cnt))] += 1
    out = []
    for k, c in zip(keys, cnt):
        out += [k] * int(c)
    rng.shuffle(out)
    return out


def _integer(value, field, minimum=0):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f'{field} 必须是大于等于 {minimum} 的整数')
    return int(value)                    # numpy 整数先转 Python，避免派生种子乘法溢出


def _selection(value, default, available, field):
    value = default if value is None else value
    if isinstance(value, str):
        value = [part.strip() for part in value.split(',')]
    elif not isinstance(value, (list, tuple)):
        raise ValueError(f'{field} 必须是名称或名称列表')
    if not value:
        raise ValueError(f'{field} 不能为空')
    unknown = [item for item in value if not isinstance(item, str) or item not in available]
    if unknown:
        raise ValueError(f'{field} 含未知名称：{unknown!r}')
    return list(dict.fromkeys(value))


def plan(style, n=12, subjects=None, templates=None, seed=1, prefix=None, ids=None):
    """排一套方案：题材尽量不重复、构图轮转、画幅按配比、种子固定。"""
    n = _integer(n, 'n', minimum=1)
    seed = _integer(seed, 'seed')
    if ids is not None:
        if not isinstance(ids, (list, tuple)) or len(ids) != n:
            raise ValueError('ids 必须是与款数 n 等长的编号列表')
        if any(not isinstance(sid, str) or not sid.strip() for sid in ids):
            raise ValueError('ids 中的编号必须是非空文本')
        if len({sid.casefold() for sid in ids}) != n:
            raise ValueError('ids 中的编号不能重复（忽略大小写）')
    if prefix is not None and not isinstance(prefix, str):
        raise ValueError('prefix 必须是文本')
    rng = np.random.default_rng(seed)
    st = stylepack.normalize(style)
    subs = _selection(subjects, st['subjects'], motifs.MOTIFS, 'subjects')
    tpls = _selection(templates, st['templates'], comp.TEMPLATES, 'templates')
    fmts = _fmt_mix(st, n, rng)
    pool = list(subs)
    out, used = [], set()
    for i in range(n):
        if len(used) == len(subs) * len(tpls):
            used.clear()                 # 每一轮都用满全部组合，之后才允许复用
        if not pool:                      # 题材用完了再来一轮，但换构图
            pool = list(subs)
            rng.shuffle(pool)
        sub = pool.pop(int(rng.integers(0, len(pool))))
        # 同一 (题材, 构图) 只用一次：先按顺序轮，撞了就往后找
        tpl = None
        for k in range(len(tpls)):
            cand = tpls[(i + k) % len(tpls)]
            if (sub, cand) not in used:
                tpl = cand
                break
        if tpl is None:
            tpl = tpls[int(rng.integers(0, len(tpls)))]
        used.add((sub, tpl))
        fmt = fmts[i]
        sid = ids[i] if ids is not None else f'{prefix or "PO"}{i + 1:03d}'
        out.append(dict(id=sid, subject=sub, template=tpl, format=fmt,
                        seed=int(seed * 1000 + i * 37 + 11),
                        name=f'{motifs.META[sub]["cn"]}{SUFFIX[min(i // max(len(subs), 1), len(SUFFIX) - 1)]}',
                        tags=[motifs.META[sub]['cat']]))
    return out


def _bbox_ratio(grid):
    ys, xs = np.nonzero(grid != 0)
    if len(xs) == 0:
        return 0.0, 0.0
    return (xs.max() - xs.min() + 1) / grid.shape[1], (ys.max() - ys.min() + 1) / grid.shape[0]


def _subject_ratio(info, W, H):
    """主体（造型）占画布的比例；没有造型包围盒时退回整幅包围盒。"""
    boxes = info.get('motif_boxes') or []
    if not boxes:
        return 1.0, 1.0
    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    return (x1 - x0) / W, (y1 - y0) / H


def _draw(spec, st, pal, W, H, zoom, rng, scale=1.0):
    """画一遍：构图模板 + 造型（scale 用于自动放大主体）。"""
    cv = Canvas(W, H, pal, seed=spec['seed'], zoom=zoom)
    boxes = []

    def draw_motif(c, cx, cy, s, r):
        b = motifs.draw(spec['subject'], c, cx, cy, s * scale, st, r)
        if b:
            boxes.append(b)

    info = comp.apply(spec['template'], cv, st, rng, draw_motif, W, H)
    info['motif_boxes'] = boxes
    return cv, info


def _grid_bbox(grid):
    ys, xs = np.nonzero(grid != 0)
    if len(xs) == 0:
        return 0.0, 0.0
    return (xs.max() - xs.min() + 1) / grid.shape[1], (ys.max() - ys.min() + 1) / grid.shape[0]


def quality_of(result):
    """一款成品的可售卖质量分（0–1）。

    评分不是"好看程度"，而是**能不能卖**的四条硬指标：
    - 主体面积占比（包围盒 / 画布）：< 0.22 直接判废，0.42 以上满分
    - 色阶数：少于 3 色封顶 0.55（太平，卖不上价）
    - 孤立单颗占比：超过 30% 封顶 0.50（难拼、易掉）
    - 难度星级：3–4 星最好卖，5 星偏难，2 星偏简单
    """
    g = result['grid']
    st = result['stats']
    bw, bh = _grid_bbox(g)
    area = bw * bh
    beads = max(int(st['beads']), 1)
    singles_ratio = st['singles'] / beads
    colors = st['colors']
    stars = st['star_n']

    q_area = min(1.0, area / 0.42)
    q_color = min(1.0, colors / 4.0)
    q_single = max(0.0, 1.0 - max(0.0, singles_ratio - 0.12) / 0.28)
    q_star = 1.0 - min(1.0, abs(stars - 3.4) / 2.6)
    score = 0.40 * q_area + 0.22 * q_color + 0.22 * q_single + 0.16 * q_star
    if area < 0.22:                       # 主体太小，熨出来就是一小坨
        score = min(score, 0.30)
    if colors < 3:
        score = min(score, 0.55)
    if singles_ratio > 0.30:
        score = min(score, 0.50)
    return dict(score=round(float(score), 4), area=round(float(area), 3),
                short=round(float(min(bw, bh)), 3), colors=colors,
                singles_ratio=round(float(singles_ratio), 3), stars=stars)


def compose_best(spec, style, S=8, tries=4, target=0.72):
    """同一款最多画 3 遍（第 2 遍换平涂、第 3 遍换满幅），取质量分最高的一版。
    种子固定 + 尝试顺序固定，所以结果仍然可复现。"""
    best = None
    for attempt in range(max(1, tries)):
        s2 = dict(spec, attempt=attempt)
        try:
            r = compose(s2, style, S=S)
        except Exception:
            if attempt == 0:
                raise
            continue
        r['quality'] = quality_of(r)
        if best is None or r['quality']['score'] > best['quality']['score']:
            best = r
        q = r['quality']
        fixable = q['area'] < 0.22 or q['singles_ratio'] > 0.30
        if q['score'] >= target or not fixable:
            break                         # 已经够好，或缺陷不是换纹理能修的（如线描天生 2 色）
    return best


def compose(spec, style, S=8):
    """按一条方案画出画布、拼豆网格和统计。"""
    if not isinstance(spec, Mapping):
        raise ValueError('方案必须是对象')
    spec = copy.deepcopy(dict(spec))
    for field, available in (('subject', motifs.MOTIFS), ('template', comp.TEMPLATES),
                             ('format', stylepack.FORMATS)):
        value = spec.get(field)
        if not isinstance(value, str) or value not in available:
            raise ValueError(f'方案 {field} 无效：{value!r}')
    spec['seed'] = _integer(spec.get('seed'), '方案 seed')
    st = stylepack.normalize(style)
    W, H, zoom = stylepack.FORMATS[spec['format']]
    pal = palette.Palette.from_style(st)
    seed = spec['seed']
    # 每款在纹理池里挑一种，同一风格下也有变化
    pool = st.get('texture_pool')
    st = dict(st)
    rng0 = np.random.default_rng(seed)
    if pool:
        st['fill_texture'] = str(rng0.choice(pool))
        if rng0.random() < 0.5:
            st['face_texture'] = st['fill_texture']
    attempt = int(spec.get('attempt', 0) or 0)
    if attempt == 1:                      # 第 2 遍：强制平涂，压掉点刺造成的孤立单颗
        st['fill_texture'] = 'solid'
        st['face_texture'] = 'solid'
        st['splatter'] = 0
    elif attempt == 2:                    # 第 3 遍：满幅构图，把主体撑到最大
        st['fill_texture'] = 'solid'
        st['face_texture'] = 'solid'
        st['splatter'] = 0
        spec = dict(spec, template='fullbleed')
    elif attempt >= 3:                    # 第 4 遍：加内轮廓，把 2 色款补成 3 色
        st['fill_texture'] = 'contour'
        st['face_texture'] = 'contour'
        st['splatter'] = 0
    rng = np.random.default_rng(seed)
    cv, info = _draw(spec, st, pal, W, H, zoom, rng)
    # 主体偏小就自动放大一次（同一个种子，结果可复现）；环形构图不能放太狠，否则会顶穿外框
    bw, bh = _subject_ratio(info, W, H)
    target = 0.62 if spec['format'] == 'V' else 0.74
    cap = 1.18 if spec['template'] in ('badge', 'medallion', 'wreath', 'window', 'radial', 'frame') else 1.5
    need = target / max(min(bw, bh), 1e-6)
    fit = 0.96 / max(bw, bh, 1e-6)                    # 别让主体放大到出血
    if need > 1.06 and fit > 1.02:
        rng = np.random.default_rng(seed)
        cv, info = _draw(spec, st, pal, W, H, zoom, rng, scale=min(need, cap, fit))

    # 点缀：克制，只在一个焦点上
    pol = st.get('accent_policy') or {}
    if pol.get('focus', 1) > 0 and cv.pal.has('accent') and rng.random() < st.get('accent_rate', 0.5):
        if info.get('shape') == 'circle' and info.get('r'):
            a = rng.uniform(0, 2 * math.pi)
            rr = info['r'] * 0.82
            cv.circle(W / 2 + rr * math.cos(a), H / 2 + rr * math.sin(a), 1.6, 'accent')
    # 墨溅/飞点：贴近主体，别飘出去
    n_spl = int(st.get('splatter', 0))
    if n_spl:
        brushes.splatter(cv, W / 2, H / 2, min(W, H) * 0.42, rng, n=n_spl,
                         role=st.get('detail', 'line'), spread=0.9)

    g0 = cv.grid(S=S)
    before = int((g0 != 0).sum())
    kw = dict(border=st.get('border', 1), close=st.get('close', 1),
              min_island=st.get('min_island', 30), hole=st.get('hole', 16),
              bridge_max=st.get('bridge_max', 5),
              white=cv.pal.index('white') if cv.pal.has('white') else cv.pal.index('light'))
    g = beadify.finalize(g0, **kw)
    # 白边会增加总颗数，不能拿成品总量判断原画是否被删空。
    # 只数原有墨格还剩多少，防止大外框掩盖主体消失。
    if int(np.count_nonzero(g[g0 != 0])) < before * 0.55:
        kw2 = dict(kw, bridge_max=max(kw['bridge_max'], 16), min_island=min(kw['min_island'], 14))
        g = beadify.finalize(g0, **kw2)
    stt = beadify.stats(g, pal, st.get('difficulty'))
    stt['format'] = spec['format']
    stt['fill_ratio'] = round(float((g != 0).sum()) / g.size, 3)
    return dict(canvas=cv, grid=g, pal=pal, style=st, spec=spec, stats=stt, info=info)


def preview(specs, style, path, B=6, cols=4, labels=True):
    """自查小样：一排排小图，看糊/断/飘/空/重复。"""
    from PIL import Image, ImageDraw, ImageFont
    tiles = []
    for spec in specs:
        r = compose(spec, style)
        tiles.append((Image.fromarray(beadify.quick_png(r['grid'], r['pal'], B)), spec))
    if not tiles:
        return None
    cw = max(t.size[0] for t, _ in tiles) + 8
    ch = max(t.size[1] for t, _ in tiles) + 8
    lab = 18 if labels else 0
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 8, rows * (ch + lab) + 8), (250, 249, 246))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    except Exception:
        f = ImageFont.load_default()
    for i, (t, spec) in enumerate(tiles):
        x = 8 + (i % cols) * cw
        y = 8 + (i // cols) * (ch + lab)
        sheet.paste(t, (x + (cw - 8 - t.size[0]) // 2, y + (ch - 8 - t.size[1]) // 2))
        if labels:
            d.text((x + 2, y + ch - 4), f'{spec["id"]} {spec["subject"]}/{spec["template"]}/{spec["format"]}',
                   font=f, fill=(90, 90, 90))
    sheet.save(path)
    return path
