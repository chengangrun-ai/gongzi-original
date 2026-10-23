"""把每个造型单独画一张，做成一张对照表，用来人工挑出画得弱的造型。

用法：python scripts/audit_motifs.py [风格id] [输出png]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont

from pindou import beadify, motifs, palette, stylepack
from pindou.canvas import Canvas


def render(name, st, B=8, size=52):
    pal = palette.Palette.from_style(st)
    cv = Canvas(size, size, pal, seed=7)
    st2 = dict(st)
    rng = cv.rng
    motifs.draw(name, cv, size / 2, size / 2, size * 0.40, st2, rng)
    g = beadify.finalize(cv.grid(), border=1, close=1, min_island=24, hole=16,
                         white=cv.pal.index('white') if cv.pal.has('white') else 1)
    return Image.fromarray(beadify.quick_png(g, pal, B))


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else 'ink_tattoo'
    out = sys.argv[2] if len(sys.argv) > 2 else 'audit.png'
    st = stylepack.get(sid)
    names = sorted(motifs.MOTIFS)
    B = 7
    cols = 8
    cw, ch = 52 * B + 6, 52 * B + 22
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 6, rows * ch + 6), (250, 249, 246))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    for i, n in enumerate(names):
        im = render(n, st, B)
        x = 6 + (i % cols) * cw
        y = 6 + (i // cols) * ch
        sheet.paste(im, (x, y))
        d.text((x + 2, y + 52 * B + 2), n, font=f, fill=(60, 60, 60))
    sheet.save(out)
    print(f'{len(names)} 个造型 → {out}')


if __name__ == '__main__':
    main()
