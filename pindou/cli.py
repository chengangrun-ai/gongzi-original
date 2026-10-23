"""命令行入口：python scripts/pindou.py <命令> ...

  styles                                    列出所有风格包
  analyze <参考图目录> [--out dna.json] [--save-style 名称] [--subjects a,b]
  build --style <风格|json> --n 12 --out <目录> [...]
  auto <参考图目录> --n 12 --out <目录> [--subjects a,b]      # 分析 → 生成风格 → 出全套
  audit [--style 风格] [--out png]            # 全部造型对照表（挑出画得弱的）
  check <输出目录> [--refs 参考图目录]        # 重跑原创性核查
  selftest                                   # 自检：跑通全流程
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from pindou import analyze, build as builder, originality, recipes, stylepack  # noqa: E402


def cmd_styles(args):
    all_ = stylepack.list_styles()
    print(f'共 {len(all_)} 个风格包：\n')
    for sid, d in sorted(all_.items()):
        pal = d.get('palette', {})
        print(f'  {sid:18s} {d.get("name", ""):10s} {" ".join("#" + k for k in d.get("tags", [])[:4])}')
        print(f'  {"":18s} 画幅 {d.get("formats")}  纹理 {d.get("fill_texture")}  题材 {", ".join(d.get("subjects", [])[:8])}…')


def cmd_analyze(args):
    out = args.out or os.path.join(args.refs, 'style_dna.json')
    agg = analyze.run(args.refs, out, name=args.name)
    print(f'\n风格 DNA → {out}')
    print(f'  饱和度 {agg["saturation"]}  对比 {agg["contrast"]}  边缘密度 {agg["edge_density"]}  线宽 {agg["line_weight"]}')
    print(f'  直接缩图糊格率 {agg["bead_mud"]}（>0.35 说明必须重画，不能缩图）')
    print(f'  推荐纹理 {agg["texture"]}  画幅配比 {agg["formats"]}')
    print(f'  配色角色 {json.dumps(agg["palette_roles"], ensure_ascii=False)}')
    if args.save_style:
        st = stylepack.from_dna(agg, name=args.save_style)
        if args.subjects:
            st['subjects'] = [s.strip() for s in args.subjects.split(',') if s.strip()]
        p = os.path.join(stylepack.STYLE_DIR, f'{st["id"]}.json')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        print(f'  已生成风格包 → {p}')
    return agg


def cmd_build(args):
    subjects = [s.strip() for s in args.subjects.split(',')] if args.subjects else None
    templates = [s.strip() for s in args.templates.split(',')] if args.templates else None
    r = builder.build(args.style, args.out, n=args.n, subjects=subjects, templates=templates,
                      seed=args.seed, prefix=args.prefix, series=args.series, refs=args.refs,
                      cs=args.cs, do_zip=not args.no_zip)
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as f:
            json.dump(dict(out_dir=r['out_dir'], series=r['series'], count=len(r['entries']),
                           originality=r['originality'], designs=[
                               {k: e[k] for k in ('id', 'name', 'subject', 'template', 'seed')} | dict(stats=e['stats'])
                               for e in r['entries']]), f, ensure_ascii=False, indent=2)
    return r


def cmd_auto(args):
    builder.preflight_output_dir(args.out)
    agg = analyze.run(args.refs,
                      name=args.name or os.path.basename(os.path.abspath(args.refs)))
    st = stylepack.from_dna(agg, name=args.name or '参考图风格', color_set=args.color_set)
    if args.subjects:
        st['subjects'] = [s.strip() for s in args.subjects.split(',') if s.strip()]
    if args.templates:
        st['templates'] = [s.strip() for s in args.templates.split(',') if s.strip()]
    print(f'\n自动风格包：{st["id"]}（{st["name"]}）  纹理 {st["fill_texture"]}  线宽 {st["line_width"]}')
    r = builder.build(st, args.out, n=args.n, seed=args.seed, prefix=args.prefix,
                      series=args.series or st['name'], refs=args.refs, cs=args.cs, do_zip=not args.no_zip)
    for name, data in (('风格分析.json', agg), ('风格包.json', st)):
        with open(os.path.join(args.out, name), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, allow_nan=False)
    return r


def cmd_audit(args):
    import time
    from PIL import Image, ImageDraw, ImageFont
    from pindou import beadify, motifs, palette
    from pindou.canvas import Canvas
    st = stylepack.get(args.style)
    names = sorted(motifs.MOTIFS)
    B, cols = 7, 8
    cw, ch = 52 * B + 6, 52 * B + 22
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * cw + 6, rows * ch + 6), (250, 249, 246))
    d = ImageDraw.Draw(sheet)
    from pindou.chartkit import font_num, _save
    f = font_num(13)
    for i, n in enumerate(names):
        pal = palette.Palette.from_style(st)
        cv = Canvas(52, 52, pal, seed=7)
        motifs.draw(n, cv, 26, 26, 20.8, st, cv.rng)
        g = beadify.finalize(cv.grid(), border=1, close=1, min_island=24, hole=16,
                             white=cv.pal.index('white') if cv.pal.has('white') else 1)
        im = Image.fromarray(beadify.quick_png(g, pal, B))
        x = 6 + (i % cols) * cw
        y = 6 + (i // cols) * ch
        sheet.paste(im, (x, y))
        d.text((x + 2, y + 52 * B + 2), n, font=f, fill=(60, 60, 60))
    out = args.out or os.path.join(ROOT, 'audit.png')
    _save(sheet, out, dict(Title=f'{st["name"]} 造型对照表', Author='拼豆原创工坊',
                           CreationTime=time.strftime('%Y-%m-%d %H:%M:%S'), Software='pindou-original',
                           Copyright=f'© {time.strftime("%Y")} 原创作品 · 保留所有权利'))
    print(f'{len(names)} 个造型 → {out}')


def cmd_check(args):
    from pathlib import Path
    delivery = builder.delivery_context(args.out)
    gdir = os.path.join(args.out, '网格')
    packs = []
    for fn in sorted(os.listdir(gdir)):
        if not fn.endswith('.txt'):
            continue
        arr, pal = builder.load_grid(Path(gdir, fn).read_text(encoding='utf-8'))
        packs.append((fn[:-4], arr, pal))
    if not packs:
        raise ValueError('网格目录没有可核查作品')
    res = originality.check(packs, args.refs)
    series, style = os.path.basename(os.path.abspath(args.out)), ''
    try:
        with open(os.path.join(args.out, 'catalog.json'), encoding='utf-8') as f:
            cat = json.load(f)
        series = cat.get('series') or series
        style = cat.get('style') or ''
    except Exception:
        pass
    p = originality.write(res, args.out, series, style)
    summary = Path(args.out) / '说明.txt'
    if summary.is_file():
        text = summary.read_text(encoding='utf-8')
        lines = text.splitlines(keepends=True)
        updated = ''.join((f'核查结果：{builder.result_label(res)}（详见 原创性报告.md）\n'
                           if line.startswith('核查结果：') else line) for line in lines)
        if updated != text:
            summary.write_text(updated, encoding='utf-8')
    builder.refresh_delivery(args.out, delivery)
    print(f'核查：{builder.result_label(res)}  报告 → {p}')
    return res


def cmd_motifs(args):
    from pindou import motifs
    cats = {}
    for n, m in motifs.META.items():
        cats.setdefault(m['cat'], []).append((n, m['cn']))
    print(f'共 {len(motifs.MOTIFS)} 个造型：\n')
    for c, items in sorted(cats.items()):
        print(f'  [{c}] ' + '  '.join(f'{n}({cn})' for n, cn in sorted(items)))
    from pindou import comp
    print(f'\n构图模板 {len(comp.TEMPLATES)} 个：' + '  '.join(f'{k}({v})' for k, v in sorted(comp.INFO.items())))
    from pindou import brushes
    print(f'\n填充纹理 {len(brushes.TEXTURES)} 种：' + '  '.join(sorted(brushes.TEXTURES)))


def cmd_selftest(args):
    import tempfile
    import time
    from pindou import beadify
    t = time.time()
    print('1/3 生成三种风格的样张…')
    for sid in ('ink_tattoo', 'kawaii_pastel', 'pop_art'):
        try:
            st = stylepack.get(sid)
        except SystemExit:
            continue
        specs = recipes.plan(st, n=3, seed=2)
        for s in specs:
            r = recipes.compose(s, st)
            assert beadify.connected(r['grid']) == 1, f'{sid} {s["id"]} 不是一整片'
        print(f'   {sid}: 3 款通过（整片连通）')
    print('2/3 出图…')
    with tempfile.TemporaryDirectory(prefix='pindou_') as tmp:
        r = builder.build('ink_tattoo', tmp, n=2, seed=3, quiet=True, do_zip=False)
        assert os.path.isfile(r['report'])
        print('   色号图/原画/效果图/总览/报告 已验证（临时文件已清理）')
    print('3/3 复现性…')
    s = recipes.plan(stylepack.get('ink_tattoo'), n=1, seed=9)[0]
    a = recipes.compose(s, stylepack.get('ink_tattoo'))['grid']
    b = recipes.compose(s, stylepack.get('ink_tattoo'))['grid']
    assert (a == b).all(), '同种子结果不一致'
    print('   同种子逐格一致 [OK]')
    print(f'\n自检通过（{time.time() - t:.1f}s）')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='pindou', description='任意风格 → 原创拼豆图纸')
    sub = ap.add_subparsers(dest='cmd')

    s = sub.add_parser('styles', help='列出风格包')
    s.set_defaults(fn=cmd_styles)

    s = sub.add_parser('analyze', help='分析参考图，输出风格 DNA')
    s.add_argument('refs')
    s.add_argument('--out')
    s.add_argument('--name')
    s.add_argument('--save-style', help='同时生成一个风格包（写进 styles/）')
    s.add_argument('--subjects', help='给自动风格包指定题材，逗号分隔')
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser('build', help='按风格包生成整套作品')
    s.add_argument('--style', required=True)
    s.add_argument('--n', type=int, default=12)
    s.add_argument('--out', required=True)
    s.add_argument('--subjects')
    s.add_argument('--templates')
    s.add_argument('--seed', type=int, default=1)
    s.add_argument('--prefix', default='PO')
    s.add_argument('--series')
    s.add_argument('--refs', help='参考图目录（只用于原创性核查）')
    s.add_argument('--cs', type=int, default=28, help='色号图每格像素')
    s.add_argument('--no-zip', action='store_true')
    s.add_argument('--json')
    s.set_defaults(fn=cmd_build)

    s = sub.add_parser('auto', help='参考图 → 自动风格包 → 整套作品')
    s.add_argument('refs')
    s.add_argument('--out', required=True)
    s.add_argument('--n', type=int, default=12)
    s.add_argument('--name')
    s.add_argument('--subjects')
    s.add_argument('--templates')
    s.add_argument('--color-set', default=None)
    s.add_argument('--seed', type=int, default=1)
    s.add_argument('--prefix', default='PO')
    s.add_argument('--series')
    s.add_argument('--cs', type=int, default=28)
    s.add_argument('--no-zip', action='store_true')
    s.set_defaults(fn=cmd_auto)

    s = sub.add_parser('motifs', help='列出全部造型/构图/纹理')
    s.set_defaults(fn=cmd_motifs)

    s = sub.add_parser('audit', help='全部造型对照表')
    s.add_argument('--style', default='ink_tattoo')
    s.add_argument('--out')
    s.set_defaults(fn=cmd_audit)

    s = sub.add_parser('check', help='重跑原创性核查')
    s.add_argument('out')
    s.add_argument('--refs')
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser('selftest', help='自检')
    s.set_defaults(fn=cmd_selftest)

    args = ap.parse_args(argv)
    if not getattr(args, 'fn', None):
        ap.print_help()
        return 1
    try:
        result = args.fn(args)
    except (ValueError, OSError, KeyError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 2
    if isinstance(result, dict):
        check_result = result.get('originality', result)
        if check_result.get('pass_') is False:
            return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
