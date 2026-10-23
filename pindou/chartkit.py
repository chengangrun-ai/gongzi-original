"""出图：色号图、高清原画、成品效果图、总览、目录、zip。

所有 PNG 都写入 Title / Author / Copyright / Description / CreationTime 元数据，便于举证原创。
"""
import io
import csv
import json
import math
import os
import re
import zipfile
import tempfile
from pathlib import Path, PurePosixPath
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.PngImagePlugin import PngInfo

from .palette import PAPER, card, short

FONT_DIRS = [os.environ.get('PINDOU_FONT_DIR', ''), 'C:/Windows/Fonts', '/usr/share/fonts',
             '/System/Library/Fonts', os.path.expanduser('~/.fonts')]
FONT_CN = ['msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'NotoSansSC-Regular.otf', 'NotoSansCJK-Regular.ttc', 'Deng.ttf']
FONT_NUM = ['arialbd.ttf', 'Arial Bold.ttf', 'DejaVuSans-Bold.ttf', 'msyhbd.ttc']
BG = (245, 242, 236)


def _font(names, size):
    for d in FONT_DIRS:
        if not d:
            continue
        for n in names:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def font_cn(size):
    return _font(FONT_CN, size)


def font_num(size):
    return _font(FONT_NUM, size)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def tcol(c):
    return (255, 255, 255) if lum(c) < 150 else (28, 28, 28)


def code_key(c):
    m = re.match(r'([A-Z]+)(\d+)$', c)
    return (m.group(1), int(m.group(2))) if m else (c, 0)


# ---------------------------------------------------------------- 图案对象
class Pattern:
    """一个成品网格 + 配色，负责统计和分区。"""

    def __init__(self, grid, pal):
        self.grid = np.asarray(grid)
        self.pal = pal
        self.H, self.W = self.grid.shape
        cnt = Counter()
        for i in range(1, len(pal)):
            n = int((self.grid == i).sum())
            if n:
                cnt[pal.code(pal.roles[i])] += n
        self.cnt = cnt
        self.used = sorted(cnt, key=code_key)
        self.total = sum(cnt.values())
        self.ncol = len(cnt)
        self.rgb = {pal.code(pal.roles[i]): pal.tone_rgb(i) for i in range(1, len(pal))}

    def bbox(self):
        ys, xs = np.nonzero(self.grid != PAPER)
        if not len(xs):
            return 0, 0, self.W, self.H
        return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

    def cells(self):
        for j in range(self.H):
            for i in range(self.W):
                v = int(self.grid[j, i])
                if v != PAPER:
                    yield j, i, self.pal.code(self.pal.roles[v])

    def singles(self):
        n = 0
        g = self.grid
        for y, x in zip(*np.nonzero(g != PAPER)):
            c = g[y, x]
            if not any(0 <= y + dy < self.H and 0 <= x + dx < self.W and g[y + dy, x + dx] == c
                       for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))):
                n += 1
        return n



# ---------------------------------------------------------------- 文本自适应
def _fit_font(text, base_size, max_w, kind='cn', min_ratio=0.45):
    """按可用宽度挑字号：放不下就缩，缩到下限后截断加省略号。"""
    if not text:
        return text, font_cn(base_size) if kind == 'cn' else font_num(base_size)
    size = base_size
    f = font_cn(size) if kind == 'cn' else font_num(size)
    while d_len(text, f) > max_w and size > max(8, int(base_size * min_ratio)):
        size -= 1
        f = font_cn(size) if kind == 'cn' else font_num(size)
    if d_len(text, f) > max_w:
        cut = text
        while cut and d_len(cut + '…', f) > max_w:
            cut = cut[:-1]
        text = cut.rstrip() + '…'
    return text, f


def d_len(text, font):
    """文本宽度（兼容没有 ImageDraw 的场合）。"""
    try:
        return ImageDraw.Draw(Image.new('RGB', (8, 8))).textlength(text, font=font)
    except Exception:
        return len(text) * font.size


def wrap_text(text, font, max_w, max_lines=2):
    """按宽度折行，超过 max_lines 截断。"""
    out, line = [], ''
    for ch in str(text):
        if d_len(line + ch, font) > max_w and line:
            out.append(line)
            line = ch
            if len(out) >= max_lines:
                break
        else:
            line += ch
    if line and len(out) < max_lines:
        out.append(line)
    if len(out) == max_lines and d_len(out[-1] + str(text)[sum(len(x) for x in out):], font) > max_w:
        rest = str(text)[sum(len(x) for x in out):]
        cut = rest
        while cut and d_len(out[-1] + '…' + cut, font) > max_w:
            cut = cut[:-1]
        out[-1] = out[-1] + (cut + '…' if cut else '…')
    return out


# ---------------------------------------------------------------- 色号图
def _dline(d, p0, p1, fill, w, dash=7, gap=5):
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    s = 0
    while s < L:
        e = min(L, s + dash)
        d.line([(x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L),
                (x0 + (x1 - x0) * e / L, y0 + (y1 - y0) * e / L)], fill=fill, width=w)
        s += dash + gap


def color_chart(pat, path, meta, CS=30, title='', subtitle='', footer=None, watermark='原创图纸 · 禁止搬运',
                legend_note='', show_codes=True):
    """色号大图：每格写色号，10 格红实线、5 格灰虚线，带行列坐标、用色清单和斜向水印。"""
    W, H = pat.W, pat.H
    pad, cm = 64, 46
    gw, gh = W * CS, H * CS
    Wt = pad * 2 + cm * 2 + gw
    # 竖幅太高时自动降每格像素，别让单张图超过 12000px
    if Ht_guess := H * CS:
        if Ht_guess > 12000:
            CS = max(12, int(12000 * CS / Ht_guess))
            gw, gh = W * CS, H * CS
    per = max(1, (Wt - 2 * pad) // 150)
    lrows = math.ceil(max(pat.ncol, 1) / per)

    # 头部：标题 / 副标题 / 图例说明按实际文本折行，高度动态算，绝不互相压
    tag = f'{pat.total:,} 颗 · {pat.ncol} 色'
    fTag = font_cn(26)
    tag_w = d_len(tag, fTag) + 36
    head_w = Wt - pad * 2 - tag_w - 24
    title_lines = wrap_text(title, font_cn(56), head_w, max_lines=2)
    sub_lines = wrap_text(subtitle, font_cn(28), head_w, max_lines=2) if subtitle else []
    note_lines = wrap_text(legend_note, font_cn(20), Wt - pad * 2, max_lines=2) if legend_note else []
    th = 30 + 66 * len(title_lines) + 40 * len(sub_lines) + 32 * len(note_lines) + 34
    lh = 96 + lrows * 96
    fh = 130
    Ht = th + cm * 2 + gh + lh + fh
    im = Image.new('RGB', (Wt, Ht), 'white')
    d = ImageDraw.Draw(im)
    fC = font_num(max(11, int(CS * 0.40)))
    fK = font_num(17)
    fL, fLn = font_num(21), font_cn(19)

    y = 26
    for ln in title_lines:
        d.text((pad, y), ln, font=font_cn(56), fill=(26, 26, 26))
        y += 66
    for ln in sub_lines:
        d.text((pad, y), ln, font=font_cn(28), fill=(90, 90, 90))
        y += 40
    for ln in note_lines:
        d.text((pad, y), ln, font=font_cn(20), fill=(140, 140, 140))
        y += 32
    d.rounded_rectangle([Wt - pad - tag_w, 44, Wt - pad, 92], radius=12, fill=(200, 76, 76))
    d.text((Wt - pad - tag_w + tag_w / 2, 68), tag, font=fTag, fill='white', anchor='mm')

    gx, gy = pad + cm, th + cm
    for j, i, c in pat.cells():
        d.rectangle([gx + i * CS, gy + j * CS, gx + (i + 1) * CS, gy + (j + 1) * CS], fill=pat.rgb[c])
    for i in range(W + 1):
        d.line([(gx + i * CS, gy), (gx + i * CS, gy + gh)], fill=(206, 206, 206), width=1)
    for j in range(H + 1):
        d.line([(gx, gy + j * CS), (gx + gw, gy + j * CS)], fill=(206, 206, 206), width=1)
    for i in range(5, W, 5):
        if i % 10:
            _dline(d, (gx + i * CS, gy), (gx + i * CS, gy + gh), (150, 150, 150), 2)
    for j in range(5, H, 5):
        if j % 10:
            _dline(d, (gx, gy + j * CS), (gx + gw, gy + j * CS), (150, 150, 150), 2)
    for i in range(10, W, 10):
        d.line([(gx + i * CS, gy), (gx + i * CS, gy + gh)], fill=(222, 80, 80), width=3)
    for j in range(10, H, 10):
        d.line([(gx, gy + j * CS), (gx + gw, gy + j * CS)], fill=(222, 80, 80), width=3)
    d.rectangle([gx, gy, gx + gw, gy + gh], outline=(50, 50, 50), width=3)
    if show_codes:
        for j, i, c in pat.cells():
            d.text((gx + i * CS + CS / 2, gy + j * CS + CS / 2 + 1), short(c), font=fC,
                   fill=tcol(pat.rgb[c]), anchor='mm')
    for i in range(W):
        col = (210, 60, 60) if (i + 1) % 10 == 0 else (110, 110, 110)
        d.text((gx + i * CS + CS / 2, gy - cm / 2), str(i + 1), font=fK, fill=col, anchor='mm')
        d.text((gx + i * CS + CS / 2, gy + gh + cm / 2), str(i + 1), font=fK, fill=col, anchor='mm')
    for j in range(H):
        col = (210, 60, 60) if (j + 1) % 10 == 0 else (110, 110, 110)
        d.text((gx - cm / 2, gy + j * CS + CS / 2), str(j + 1), font=fK, fill=col, anchor='mm')
        d.text((gx + gw + cm / 2, gy + j * CS + CS / 2), str(j + 1), font=fK, fill=col, anchor='mm')

    # 斜向淡水印（压在色块上，不影响读色号）
    big = Image.new('RGBA', (int(gw * 1.7), int(gh * 1.7)), (0, 0, 0, 0))
    bd = ImageDraw.Draw(big)
    fw = font_cn(40)
    # 水印颜色跟着图案亮度走：深底用浅水印，否则整片看不见
    try:
        mean_lum = float(np.mean([lum(pat.rgb[c]) for c, n in pat.cnt.items() for _ in range(min(n, 200))]))
    except Exception:
        mean_lum = 200.0
    wm_fill = (255, 255, 255, 30) if mean_lum < 120 else (90, 90, 90, 26)
    for n, yy in enumerate(range(0, big.height, 340)):
        for xx in range(-(n % 2) * 300, big.width, 620):
            bd.text((xx, yy), watermark, font=fw, fill=wm_fill)
    big = big.rotate(28, resample=Image.BICUBIC)
    ox, oy = (big.width - gw) // 2, (big.height - gh) // 2
    im = im.convert('RGBA')
    im.alpha_composite(big.crop((ox, oy, ox + gw, oy + gh)), (gx, gy))
    im = im.convert('RGB')
    d = ImageDraw.Draw(im)

    ly = gy + gh + cm + 26
    d.text((pad, ly), f'用色清单（色号 · 用量）  共 {pat.ncol} 色 · {pat.total:,} 颗',
           font=font_cn(30), fill=(30, 30, 30))
    for n, c in enumerate(pat.used):
        r, k = divmod(n, per)
        x = pad + k * 150
        y = ly + 58 + r * 96
        rgb = pat.rgb[c]
        d.rounded_rectangle([x, y, x + 136, y + 44], radius=8, fill=rgb, outline=(170, 170, 170))
        d.text((x + 68, y + 22), c, font=fL, fill=tcol(rgb), anchor='mm')
        d.text((x + 68, y + 66), f'{pat.cnt[c]} 颗', font=fLn, fill=(80, 80, 80), anchor='mm')
    fy = ly + lh - 4
    flines = []
    for line in (footer or []):
        flines += wrap_text(line, font_cn(20), Wt - pad * 2, max_lines=1) or ['']
    for n, line in enumerate(flines):
        d.text((pad, fy + n * 38), line, font=font_cn(20), fill=(90, 90, 90) if n == 0 else (150, 150, 150))
    _save(im, path, meta)
    return path


def _save(im, path, meta):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    info = PngInfo()
    for k, v in (meta or {}).items():
        if v is not None:
            info.add_text(str(k), str(v))
    fd, temporary = tempfile.mkstemp(prefix='.pindou-', suffix='.png', dir=path.parent)
    os.close(fd)
    try:
        im.save(temporary, format='PNG', optimize=True, pnginfo=info)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


# ---------------------------------------------------------------- 成品效果图
def _sprite(rgb, B, ss=3):
    s = B * ss
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32) / s
    t = (xx + yy) / 2
    base = np.array(rgb, np.float32)
    hi = np.clip(0.5 - t, 0, 0.5) * 0.34
    sd = np.clip(t - 0.5, 0, 0.5) * 0.34
    col = (base * (1 - hi[..., None]) + 255 * hi[..., None]) * (1 - sd[..., None])
    r = np.hypot(xx - 0.5, yy - 0.5)
    col[r < 0.13] = base * 0.62
    col[(r >= 0.13) & (r < 0.18)] *= 0.9
    im = Image.fromarray(np.clip(col, 0, 255).astype(np.uint8)).convert('RGBA')
    mk = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mk).rounded_rectangle([int(.03 * s), int(.03 * s), int(.97 * s), int(.97 * s)],
                                         radius=int(.34 * s), fill=255)
    im.putalpha(mk)
    return im.resize((B, B), Image.LANCZOS)


def bead_mockup(pat, path, meta, B=16, m=48, bg=BG, title=''):
    x0, y0, x1, y1 = pat.bbox()
    Wp, Hp = (x1 - x0) * B + 2 * m, (y1 - y0) * B + 2 * m + (46 if title else 0)
    lay = Image.new('RGBA', (Wp, Hp), (0, 0, 0, 0))
    sp = {c: _sprite(pat.rgb[c], B) for c in pat.used}
    oy = 46 if title else 0
    for j, i, c in pat.cells():
        lay.alpha_composite(sp[c], (m + (i - x0) * B, oy + m + (j - y0) * B))
    a = lay.split()[3].filter(ImageFilter.GaussianBlur(B * 0.5)).point(lambda v: int(v * 0.3))
    sha = Image.new('L', (Wp, Hp), 0)
    sha.paste(a, (int(B * .18), int(B * .3)))
    cv = Image.new('RGBA', (Wp, Hp), bg + (255,))
    shl = Image.new('RGBA', (Wp, Hp), (70, 55, 40, 0))
    shl.putalpha(sha)
    cv.alpha_composite(shl)
    cv.alpha_composite(lay)
    if title:
        ImageDraw.Draw(cv).text((m, 10), title, font=font_cn(24), fill=(90, 90, 90))
    _save(cv.convert('RGB'), path, meta)
    return path


# ---------------------------------------------------------------- 原画
def art_image(cv, grid, path, meta, px=20):
    im = cv.art(px=px, grid=grid)
    _save(im, path, meta)
    return path


# ---------------------------------------------------------------- 总览
def contact_sheet(items, path, cols=5, cell=300, meta=None, title=''):
    """items: [(png_path 或 Image, 标签)]"""
    if not isinstance(cols, int) or cols < 1 or not isinstance(cell, int) or cell < 40:
        raise ValueError('cols 必须为正整数，cell 至少40像素')
    rows = (len(items) + cols - 1) // cols
    top = 70 if title else 20
    sheet = Image.new('RGB', (cols * cell + 40, rows * (cell + 34) + top + 20), BG)
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((20, 20), title, font=font_cn(34), fill=(40, 40, 40))
    for n, (src, label) in enumerate(items):
        if isinstance(src, (str, os.PathLike)):
            with Image.open(src) as opened:
                im = opened.convert('RGB')
        else:
            im = src.copy()
        im.thumbnail((cell - 20, cell - 20), Image.LANCZOS)
        x = 20 + (n % cols) * cell + (cell - 20 - im.size[0]) // 2
        y = top + (n // cols) * (cell + 34) + (cell - 20 - im.size[1]) // 2
        sheet.paste(im, (x, y))
        lab, lab_font = _fit_font(label, 18, cell - 24, 'cn', min_ratio=0.7)
        d.text((20 + (n % cols) * cell + 10, top + (n // cols) * (cell + 34) + cell - 14), lab,
               font=lab_font, fill=(90, 90, 90))
    _save(sheet, path, meta)
    return path


# ---------------------------------------------------------------- 目录 / zip
def write_catalog(entries, out_dir, series, style):
    rows = [['编号', '作品名', '题材', '构图', '画幅', '色数', '颗数', '孤立单颗', '难度', '尺寸cm', '用时', '配方种子']]
    designs = []
    def cell(value):
        value = str(value)
        return "'" + value if value.startswith(('=', '+', '-', '@', '\t', '\r')) else value
    for e in entries:
        st = e['stats']
        rows.append([cell(v) for v in [e['id'], e['name'], e['subject'], e['template'], st['format'],
                              str(st['colors']), str(st['beads']), str(st['singles']),
                              st['stars'], f'{st["size_cm"][0]}×{st["size_cm"][1]}', st['time'], str(e['seed'])]])
        files = {key: Path(os.path.relpath(e[key], out_dir)).as_posix()
                 for key in ('chart', 'art', 'mock', 'grid') if key in e}
        designs.append({key: e[key] for key in ('id', 'name', 'subject', 'template', 'seed')} |
                       dict(format=e.get('format', st['format']), stats=st, files=files))
    with open(os.path.join(out_dir, '目录.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerows(rows)
    with open(os.path.join(out_dir, 'catalog.json'), 'w', encoding='utf-8') as f:
        json.dump(dict(series=series, style=style, count=len(entries),
                       designs=designs), f, ensure_ascii=False, indent=2, allow_nan=False)
    return os.path.join(out_dir, '目录.csv')


def write_zip(out_dir, name, extra=(), include=None):
    """只打包明确的交付物；先验证并完整写出临时包，再替换目标。"""
    root = Path(out_dir).resolve()
    if Path(name).name != name or name in ('.', '..') or '\\' in name or ':' in name:
        raise ValueError('压缩包名称必须是目录内的文件名')
    path = root / name
    allowed_root = {'目录.csv', 'catalog.json', '原创性报告.json', '原创性报告.md', '说明.txt', 'manifest.json', '风格包.json'}
    allowed_dirs = {'色号图': '.png', '原画': '.png', '效果图': '.png', '网格': '.txt'}
    if include is None:
        include = [p for p in root.rglob('*') if p.is_file() and
                   ((p.parent == root and (p.name in allowed_root or re.fullmatch(r'总览_\d+\.png', p.name))) or
                    (p.parent.parent == root and allowed_dirs.get(p.parent.name) == p.suffix.lower()))]
    members = []
    for value in include:
        p = Path(value).resolve(strict=True)
        if not p.is_relative_to(root) or not p.is_file() or Path(value).is_symlink():
            raise ValueError('压缩文件必须是输出目录内的普通文件')
        members.append((p, p.relative_to(root).as_posix()))
    for source, arc in extra:
        arc = str(arc).replace('\\', '/')
        parts = PurePosixPath(arc)
        if parts.is_absolute() or '..' in parts.parts or ':' in arc or not arc or arc.endswith('/'):
            raise ValueError('压缩包内路径非法')
        members.append((Path(source).resolve(strict=True), parts.as_posix()))
    names = [arc for _, arc in members]
    if len(names) != len(set(names)):
        raise ValueError('压缩包内文件名重复')
    fd, temporary = tempfile.mkstemp(prefix='.pindou-', suffix='.zip', dir=root)
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
            for p, arc in sorted(members, key=lambda value: value[1]):
                z.write(p, arc)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return str(path)
