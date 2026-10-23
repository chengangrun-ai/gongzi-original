"""一键构建：方案 → 网格 → 色号图/原画/效果图 → 总览 → 目录 → 原创性报告 → zip。"""
import json
import hashlib
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import beadify, chartkit, originality, recipes, stylepack
from .palette import PAPER, short

CH = {0: '.', 'white': 'W', 'light': 'L', 'mid': 'M', 'dark': 'D', 'line': 'K', 'accent': 'R', 'accent2': 'S', 'bg': 'B'}


def ch_of(role):
    return CH.get(role, role[:1].upper())


def safe(s):
    name = re.sub(r'[\\/:*?"<>|\s\x00-\x1f]+', '_', str(s)).strip('_. ') or 'x'
    if re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', name.split('.')[0]):
        name = '_' + name
    return name[:120].rstrip('. ') or 'x'


def _symbols(pal):
    result, taken = {0: '.'}, {'.'}
    for i, role in enumerate(pal.roles[1:], 1):
        symbol = CH.get(role)
        if symbol is None or symbol in taken:
            symbol = next(chr(n) for n in range(0x100, 0x2000)
                          if not chr(n).isspace() and chr(n) not in taken)
        result[i] = symbol
        taken.add(symbol)
    return result


def grid_text(spec, grid, pal):
    """网格源文件：3 行文件头 + 每行一排豆。这就是可举证的"作品原件"。"""
    grid = np.asarray(grid)
    if grid.ndim != 2 or not grid.size or grid.dtype.kind not in 'iu' or grid.min() < 0 or grid.max() >= len(pal):
        raise ValueError('网格必须为非空二维整数，色号索引必须存在于配色中')
    symbols = _symbols(pal)
    legend = ' '.join(f'{symbols[i]}={pal.code(r)}' for i, r in enumerate(pal.roles[1:], 1))
    head = [f'# 作品：{spec["id"]} {spec["name"]}',
            f'# 配方：{spec["subject"]}/{spec["template"]}/{spec["format"]} seed={spec["seed"]} '
            f'{grid.shape[1]}x{grid.shape[0]}',
            f'# 图例：. = 不放豆   {legend}']
    rows = []
    for j in range(grid.shape[0]):
        rows.append(''.join(symbols[int(v)] for v in grid[j]))
    return '\n'.join(head + rows) + '\n'


def parse_grid(text):
    lines = [l for l in text.lstrip('\ufeff').splitlines() if l.strip()]
    head = [l for l in lines if l.startswith('#')]
    body = [l for l in lines if not l.startswith('#')]
    if not body or any(len(row) != len(body[0]) for row in body):
        raise ValueError('网格行宽不一致，必须是非空矩形')
    legend = _legend(head)
    unknown = set(''.join(body)) - set(legend) - {'.'}
    if unknown:
        raise ValueError(f'网格有未在图例中定义的符号：{sorted(unknown)}')
    declared = re.search(r'\b(\d+)x(\d+)\s*$', '\n'.join(head), re.MULTILINE)
    if declared and (int(declared[1]), int(declared[2])) != (len(body[0]), len(body)):
        raise ValueError('网格尺寸与文件头不一致')
    return head, body


def _legend(head):
    from .palette import card
    result = {}
    legend_lines = [line for line in head if re.match(r'^#\s*(?:图例|legend)\s*[:：]', line, re.IGNORECASE)]
    for symbol, code in re.findall(r'([^\s=])\s*=\s*([A-Z]+\d+)(?![\w])', '\n'.join(legend_lines)):
        if symbol in result or symbol == '.':
            raise ValueError(f'图例符号重复或冲突：{symbol}')
        if code not in card():
            raise ValueError(f'图例色号不存在：{code}')
        result[symbol] = code
    return result


def load_grid(text):
    """统一读取网格；按真实色号还原，不依赖角色顺序。"""
    from .palette import Palette
    head, body = parse_grid(text)
    legend = _legend(head)
    codes = list(dict.fromkeys(legend.values()))
    if not codes:
        raise ValueError('网格图例没有有效色号')
    pal = Palette.from_codes(codes)
    values = {symbol: pal.index_of_code(code) for symbol, code in legend.items()}
    values['.'] = 0
    grid = np.array([[values[ch] for ch in row] for row in body], dtype=np.int32)
    return grid, pal


def result_label(res):
    if not res['pass_']:
        return '未通过' if res.get('status') != 'incomplete' else '核查未完成'
    if not res.get('has_refs'):
        return ('单款无法做款间查重，参考图未核查' if res.get('pair_status') == 'not_applicable'
                else '仅款间查重通过，参考图未核查')
    return '数值核查通过，仍需人工复核'


def preflight_output_dir(out_dir):
    """build 和 auto 共用的写入前检查；旧风格凭据也不能覆盖。"""
    root = Path(out_dir)
    targets = ('catalog.json', 'manifest.json', '目录.csv', '原创性报告.json',
               '原创性报告.md', '说明.txt', '风格分析.json', '风格包.json')
    occupied = root.exists() and not root.is_dir()
    occupied |= any((root / name).exists() for name in targets)
    if root.is_dir():
        occupied |= any(re.fullmatch(r'总览_\d+\.png', p.name) for p in root.iterdir())
    for sub in ('色号图', '原画', '效果图', '网格'):
        path = root / sub
        if path.exists() and (not path.is_dir() or any(path.iterdir())):
            occupied = True
    if occupied:
        raise FileExistsError('输出目录已有作品或风格资料，请使用新的输出目录，避免覆盖或混入旧款')


def delivery_context(out_dir):
    """重查前验证旧交付清单，只识别该清单管理的交付压缩包。"""
    root = Path(out_dir).resolve()
    manifest_path = root / 'manifest.json'
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(manifest, dict) or not isinstance(manifest.get('files'), list):
        raise ValueError('交付清单格式错误')
    root_files = {'目录.csv', 'catalog.json', '原创性报告.json', '原创性报告.md', '说明.txt', '风格包.json'}
    sub_files = {'色号图': '.png', '原画': '.png', '效果图': '.png', '网格': '.txt'}
    files, names = [], set()
    for item in manifest['files']:
        name = item.get('path') if isinstance(item, dict) else None
        if not isinstance(name, str) or not name or '\\' in name or ':' in name:
            raise ValueError('交付清单含非法路径')
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('交付清单含非法路径')
        allowed = ((len(path.parts) == 1 and (name in root_files or re.fullmatch(r'总览_\d+\.png', name))) or
                   (len(path.parts) == 2 and sub_files.get(path.parts[0]) == path.suffix.lower()))
        source = root / path
        resolved = source.resolve(strict=True)
        identity = str(resolved).casefold()
        if (not allowed or not resolved.is_relative_to(root) or resolved != source or
                not source.is_file() or source.is_symlink() or identity in names):
            raise ValueError('交付清单只能包含目录内不重复的受管理交付文件')
        names.add(identity)
        files.append(source)
    if 'archive' in manifest:
        archive = manifest['archive']
    else:
        params = manifest.get('parameters', {})
        series = params.get('series') if isinstance(params, dict) else None
        archive = f'{safe(series)}_全套.zip' if isinstance(series, str) and series else None
    if archive is not None:
        if (not isinstance(archive, str) or Path(archive).name != archive or '\\' in archive or
                ':' in archive or not archive.lower().endswith('.zip')):
            raise ValueError('交付压缩包名称非法')
        target = root / archive
        if target.exists() and (not target.is_file() or target.is_symlink()):
            raise ValueError('交付压缩包必须是目录内的普通文件')
        if not target.exists():
            archive = None
        elif 'archive' not in manifest:
            # 旧清单没记录是否曾打包；同名用户 ZIP 不能仅凭名字认领。
            try:
                with zipfile.ZipFile(target) as z:
                    embedded = json.loads(z.read('manifest.json'))
                if (not isinstance(embedded, dict) or embedded.get('parameters') != manifest.get('parameters') or
                        embedded.get('files') != manifest['files']):
                    archive = None
            except (zipfile.BadZipFile, KeyError, ValueError):
                archive = None
    return manifest, files, archive


def refresh_delivery(out_dir, context):
    """报告和说明更新后刷新其校验；其余成员及用户压缩包保持原状。"""
    if context is None:
        return
    manifest, files, archive = context
    root = Path(out_dir).resolve()
    for item in manifest['files']:
        if item['path'] in {'原创性报告.json', '原创性报告.md', '说明.txt'}:
            data = (root / item['path']).read_bytes()
            item.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    manifest_path = root / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    if archive is not None:
        chartkit.write_zip(root, archive, include=files + [manifest_path])


def build(style, out_dir, n=12, subjects=None, templates=None, seed=1, prefix='PO',
          series=None, refs=None, cs=28, art_px=16, mockup_b=13, do_zip=True,
          quiet=False, ids=None):
    t0 = time.time()
    st = stylepack.get(style) if isinstance(style, str) else stylepack.normalize(style)
    series = series or st.get('name') or '原创系列'
    out_dir = os.path.abspath(out_dir)
    for name, value, low, high in [('cs', cs, 12, 100), ('art_px', art_px, 1, 64), ('mockup_b', mockup_b, 1, 64)]:
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f'{name} 必须是 {low}–{high} 之间的整数')
    specs = recipes.plan(st, n=n, subjects=subjects, templates=templates, seed=seed, prefix=prefix, ids=ids)
    if not specs:
        raise ValueError('n 必须是正整数')
    for spec in specs:
        sid = spec['id']
        if not isinstance(sid, str) or safe(sid) != sid:
            raise ValueError(f'作品编号不能用于文件名：{sid!r}')
    preflight_output_dir(out_dir)
    for sub in ('色号图', '原画', '效果图', '网格'):
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)
    entries, packs = [], []
    for spec in specs:
        r = recipes.compose_best(spec, st)
        g, pal, cv = r['grid'], r['pal'], r['canvas']
        spec['name'] = spec['name'] or spec['subject']
        spec['seed'] = spec['seed']
        # 网格源文件
        gp = os.path.join(out_dir, '网格', f'{spec["id"]}.txt')
        with open(gp, 'w', encoding='utf-8') as f:
            f.write(grid_text(spec, g, pal))
        pat = chartkit.Pattern(g, pal)
        meta = dict(Title=f'{spec["id"]} {spec["name"]}', Author='拼豆原创工坊',
                    Copyright=f'© {time.strftime("%Y")} 原创作品 · 保留所有权利',
                    Description=f'{series} · {spec["subject"]}/{spec["template"]}/{spec["format"]} '
                                f'seed={spec["seed"]} {pat.total} 颗 {pat.ncol} 色',
                    CreationTime=time.strftime('%Y-%m-%d %H:%M:%S'), Software='pindou-original')
        base = f'{spec["id"]}_{safe(spec["name"])}'
        chart = os.path.join(out_dir, '色号图', base + '_色号图.png')
        art = os.path.join(out_dir, '原画', base + '_原画.png')
        mock = os.path.join(out_dir, '效果图', base + '_效果图.png')
        stt = r['stats']
        chartkit.color_chart(pat, chart, meta, CS=cs,
                             title=f'{spec["id"]}  {spec["name"]}',
                             subtitle=f'{series} · {stylepack.FORMAT_INFO[spec["format"]]} · '
                                      f'{pat.ncol} 色 / {pat.total} 颗 · 难度 {stt["stars"]} · {stt["time"]}',
                             footer=[f'原创设计：{series} · 由代码生成（seed {spec["seed"]}），可逐格复现',
                                     '图纸仅供个人手工制作，未经许可请勿商用、转载或二次分发'],
                             legend_note='红实线 = 每 10 格   灰虚线 = 每 5 格   格内为色号   空白格不放豆')
        chartkit.art_image(cv, g, art, meta, px=art_px)
        chartkit.bead_mockup(pat, mock, meta, B=mockup_b, title=f'{spec["id"]} {spec["name"]}')
        e = dict(id=spec['id'], name=spec['name'], subject=spec['subject'], template=spec['template'],
                 seed=spec['seed'], format=spec['format'], stats=stt, chart=chart, art=art, mock=mock, grid=gp,
                 palette=pal.to_dict())
        entries.append(e)
        packs.append((spec['id'], g, pal))
        if not quiet:
            print(f'  {spec["id"]} {spec["name"]}  {spec["subject"]}/{spec["template"]}/{spec["format"]}  '
                  f'{stt["beads"]} 颗 {stt["colors"]} 色 {stt["stars"]}')
    # 总览
    sheets = []
    per = 25
    for k in range(0, len(entries), per):
        part = entries[k:k + per]
        p = os.path.join(out_dir, f'总览_{k // per + 1}.png')
        chartkit.contact_sheet([(e['mock'], f'{e["id"]} {e["name"]}') for e in part], p, cols=5,
                               cell=320, title=f'{series} · 总览 {k // per + 1}',
                               meta=dict(meta, Title=f'{series} · 总览 {k // per + 1}'))
        sheets.append(p)
    # 目录
    chartkit.write_catalog(entries, out_dir, series, st.get('id'))
    # 原创性
    res = originality.check(packs, refs)
    rep = originality.write(res, out_dir, series, st.get('name'))
    # 说明
    with open(os.path.join(out_dir, '说明.txt'), 'w', encoding='utf-8') as f:
        f.write(f'{series}\n\n')
        f.write(f'共 {len(entries)} 款，风格「{st.get("name")}」（{st.get("id")}）。\n')
        f.write('每款都包含：色号图（照着拼）、原画（展示/封面）、效果图（程序模拟效果）、网格源文件。\n')
        f.write(f'核查结果：{result_label(res)}（详见 原创性报告.md）\n')
        f.write('本系列由程序按风格规律从零绘制，参考图只用于统计风格，未取用任何像素。\n')
    # 记录实际交付文件及完整参数；不记录参考图的本机路径。
    files = [Path(e[k]) for e in entries for k in ('chart', 'art', 'mock', 'grid')]
    files += [Path(p) for p in sheets]
    files += [Path(out_dir) / name for name in ('目录.csv', 'catalog.json', '原创性报告.json', '原创性报告.md', '说明.txt')]
    manifest_path = Path(out_dir) / 'manifest.json'
    archive = f'{safe(series)}_全套.zip' if do_zip else None
    manifest = dict(version=3, created_at=datetime.now(timezone.utc).isoformat(), archive=archive,
                    parameters=dict(style=st, n=n, seed=seed, prefix=prefix, series=series,
                                    specs=specs, cs=cs, art_px=art_px, mockup_b=mockup_b),
                    files=[dict(path=p.relative_to(out_dir).as_posix(), bytes=p.stat().st_size,
                                sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)])
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    # zip
    zp = None
    if do_zip:
        zp = chartkit.write_zip(out_dir, archive, include=files + [manifest_path])
    if not quiet:
        print(f'完成：{len(entries)} 款 · {time.time() - t0:.1f}s · {out_dir}')
        print(f'核查：{result_label(res)}  最像参考图 NCC={res["worst_ref_ncc"]}  '
              f'款间最高 NCC={res["worst_pair"]["ncc"]}')
    return dict(out_dir=out_dir, entries=entries, sheets=sheets, report=rep, originality=res, zip=zp,
                style=st.get('id'), series=series, manifest=str(manifest_path), seconds=round(time.time() - t0, 1))
