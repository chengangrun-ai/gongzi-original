import argparse
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import numpy as np
from PIL import Image
from pindou import build, chartkit, cli, palette


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pal = palette.Palette({'white': 'A01', 'line': 'B01'})

    def entry(self, name='作品'):
        return dict(id='PO001', name=name, subject='flower', template='badge', seed=11,
                    chart=str(self.root / '色号图' / 'a.png'), art=str(self.root / '原画' / 'a.png'),
                    mock=str(self.root / '效果图' / 'a.png'), grid=str(self.root / '网格' / 'PO001.txt'),
                    stats=dict(format='S', colors=2, beads=5, singles=1, stars='2星',
                               size_cm=[26, 26], time='30分钟'))

    def test_076_cli_selftest_runs_in_gbk_terminal(self):
        # Exercise the full entry point in a real legacy Windows output encoding.
        env = dict(os.environ, PYTHONIOENCODING='gbk')
        p = subprocess.run([sys.executable, 'scripts/pindou.py', 'selftest'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        self.assertEqual(p.returncode, 0, p.stderr.decode('gbk', errors='replace'))

    def test_077_check_failure_produces_nonzero_cli_exit(self):
        from unittest.mock import patch
        with patch.object(cli, 'cmd_check', return_value={'pass_': False}):
            self.assertEqual(cli.main(['check', str(self.root)]), 2)

    def test_078_catalog_quotes_commas_quotes_and_newlines(self):
        chartkit.write_catalog([self.entry('花,"月"\n夜')], self.root, '系列', 'ink')
        with (self.root / '目录.csv').open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(rows[1]), 12)
        self.assertEqual(rows[1][1], '花,"月"\n夜')

    def test_079_catalog_neutralizes_formula_names(self):
        chartkit.write_catalog([self.entry('=1+1')], self.root, '系列', 'ink')
        with (self.root / '目录.csv').open(encoding='utf-8-sig', newline='') as f:
            self.assertEqual(list(csv.reader(f))[1][1], "'=1+1")

    def test_080_catalog_contains_portable_artifact_paths(self):
        chartkit.write_catalog([self.entry()], self.root, '系列', 'ink')
        cat = json.loads((self.root / 'catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(cat['designs'][0]['files']['grid'], '网格/PO001.txt')

    def test_081_catalog_keeps_physical_format(self):
        chartkit.write_catalog([self.entry()], self.root, '系列', 'ink')
        cat = json.loads((self.root / 'catalog.json').read_text(encoding='utf-8'))
        self.assertEqual(cat['designs'][0]['format'], 'S')

    def test_081_subject_survives_white_border_cleanup(self):
        from pindou import recipes, stylepack
        st = stylepack.get('lowpoly')
        spec = recipes.plan(st, n=1, seed=23)[0]
        result = recipes.compose(spec, st)
        original = result['canvas'].grid()
        # Frame alone fills the rim; the deer must remain in the central area.
        self.assertGreater(np.count_nonzero(result['grid'][12:40, 12:40]), 100)
        self.assertGreaterEqual(np.count_nonzero(result['grid'][original != 0]),
                                np.count_nonzero(original) * 0.55)

    def test_082_ragged_grid_rejected(self):
        with self.assertRaisesRegex(ValueError, '行|矩形|宽'):
            build.parse_grid('# 图例：W=A01\nW.\nW\n')

    def test_083_unknown_grid_symbol_rejected(self):
        with self.assertRaisesRegex(ValueError, '符号|图例'):
            build.parse_grid('# 图例：W=A01\nWX\n')

    def test_084_conflicting_legend_rejected(self):
        with self.assertRaisesRegex(ValueError, '重复|冲突'):
            build.parse_grid('# 图例：W=A01 W=B01\nW\n')

    def test_085_declared_dimensions_checked(self):
        with self.assertRaisesRegex(ValueError, '尺寸'):
            build.parse_grid('# 配方：flower/badge/S seed=1 52x52\n# 图例：W=A01\nW\n')

    def test_086_grid_export_rejects_invalid_palette_index(self):
        spec = dict(id='A', name='花', subject='flower', template='badge', format='S', seed=1)
        with self.assertRaisesRegex(ValueError, '索引|色号'):
            build.grid_text(spec, np.array([[5]], dtype=np.int8), self.pal)

    def test_087_grid_loader_roundtrips_bead_codes(self):
        text = '# 配方：flower/badge/S seed=1 3x2\n# 图例：W=A01 K=B01\nW.K\nKKW\n'
        load = getattr(build, 'load_grid', None)
        self.assertTrue(callable(load), '缺少统一网格读取器')
        grid, pal = load(text)
        self.assertEqual([[pal.code(int(v)) if v else '.' for v in row] for row in grid],
                         [['A01', '.', 'B01'], ['B01', 'B01', 'A01']])

    def test_grid_title_cannot_define_palette(self):
        text = '# 作品：W=B01\n# 图例：W=A01\nW\n'
        grid, pal = build.load_grid(text)
        self.assertEqual(pal.code(int(grid[0, 0])), 'A01')

    def test_fern_is_drawn_at_requested_center(self):
        from pindou import motifs, stylepack
        from pindou.canvas import Canvas
        st = stylepack.get('ink_tattoo')
        pal = palette.Palette.from_style(st)
        cv = Canvas(52, 52, pal, seed=7)
        motifs.draw('fern', cv, 26, 26, 20, st, cv.rng)
        grid = cv.grid()
        ys, xs = np.nonzero(grid)
        self.assertGreater(len(xs), 150)
        self.assertGreater(float(xs.mean()), 17)
        self.assertGreater(float(ys.mean()), 15)

    def test_088_check_empty_directory_is_error(self):
        (self.root / '网格').mkdir()
        with self.assertRaisesRegex(ValueError, '没有|为空'):
            cli.cmd_check(argparse.Namespace(out=str(self.root), refs=None))

    def test_089_windows_reserved_filename_is_safe(self):
        for name in ('CON', 'nul.txt', 'LPT1', '末尾.', '../'):
            with self.subTest(name=name):
                out = build.safe(name)
                self.assertFalse(out.endswith('.'))
                self.assertNotIn(out.split('.')[0].upper(), {'CON', 'NUL', 'LPT1'})
                self.assertNotIn('/', out)

    def test_090_invalid_build_leaves_no_output(self):
        out = self.root / 'not-created'
        with self.assertRaises((ValueError, SystemExit)):
            build.build('ink_tattoo', out, n=0, quiet=True)
        self.assertFalse(out.exists())

    def test_091_existing_output_is_not_overwritten(self):
        (self.root / 'catalog.json').write_text('old', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            build.build('ink_tattoo', self.root, n=1, quiet=True)
        self.assertEqual((self.root / 'catalog.json').read_text(), 'old')

    def test_092_zip_excludes_private_and_unrelated_files(self):
        (self.root / '参考图').mkdir()
        (self.root / '参考图' / 'private.png').write_bytes(b'private')
        (self.root / 'secret.txt').write_text('private')
        (self.root / '说明.txt').write_text('public')
        out = chartkit.write_zip(self.root, 'delivery.zip')
        with zipfile.ZipFile(out) as z:
            self.assertEqual(z.namelist(), ['说明.txt'])

    def test_093_zip_rejects_traversal_member_name(self):
        src = self.root / '说明.txt'
        src.write_text('public')
        with self.assertRaises(ValueError):
            chartkit.write_zip(self.root, 'x.zip', extra=[(src, '../outside.txt')])

    def test_094_failed_zip_preserves_previous_archive(self):
        target = self.root / 'x.zip'
        target.write_bytes(b'previous')
        with self.assertRaises(FileNotFoundError):
            chartkit.write_zip(self.root, 'x.zip', extra=[(self.root / 'missing', 'more.txt')])
        self.assertEqual(target.read_bytes(), b'previous')

    def test_095_manifest_verifies_delivered_bytes(self):
        result = build.build('ink_tattoo', self.root, n=1, subjects=['flower'], templates=['badge'],
                             cs=12, art_px=2, mockup_b=3, do_zip=False, quiet=True)
        manifest = json.loads((self.root / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['parameters']['n'], 1)
        self.assertEqual(manifest['parameters']['specs'][0]['id'], 'PO001')
        self.assertIn('style', manifest['parameters'])
        for item in manifest['files']:
            self.assertEqual(hashlib.sha256((self.root / item['path']).read_bytes()).hexdigest(), item['sha256'])
        self.assertEqual(result['manifest'], str(self.root / 'manifest.json'))

    def test_096_png_save_creates_parent_and_keeps_metadata(self):
        target = self.root / 'nested' / 'image.png'
        chartkit._save(Image.new('RGB', (2, 2)), target, {'Title': '小样'})
        with Image.open(target) as im:
            self.assertEqual(im.info['Title'], '小样')

    def test_097_contact_sheet_does_not_resize_callers_image(self):
        im = Image.new('RGB', (200, 100), 'red')
        chartkit.contact_sheet([(im, '小样')], self.root / 'sheet.png', cell=80)
        self.assertEqual(im.size, (200, 100))

    def test_098_pattern_aggregates_same_code_across_roles(self):
        pal = palette.Palette({'white': 'A01', 'line': 'A01'})
        p = chartkit.Pattern(np.array([[1, 2, 2]]), pal)
        self.assertEqual(p.cnt['A01'], 3)
        self.assertEqual(p.total, 3)

    def test_099_overview_preserves_build_metadata(self):
        # Exercise build's metadata propagation; helper-only tests miss this bug.
        result = build.build('ink_tattoo', self.root, n=1, subjects=['flower'], templates=['badge'],
                             cs=12, art_px=2, mockup_b=3, do_zip=False, quiet=True)
        with Image.open(result['sheets'][0]) as im:
            self.assertEqual(im.info['Author'], '拼豆原创工坊')
            self.assertIn('CreationTime', im.info)

    def test_100_handoff_collects_new_modules_tests_and_docs(self):
        spec = importlib.util.spec_from_file_location('handoff', 'scripts/pack_handoff.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertIn('tests/test_delivery.py', mod.FILES)
        self.assertIn('AGENTS.md', mod.FILES)
        module_path = Path('scripts/restore_handoff.py')
        restore_spec = importlib.util.spec_from_file_location('restore_handoff_test', module_path)
        restore_mod = importlib.util.module_from_spec(restore_spec)
        restore_spec.loader.exec_module(restore_mod)
        content = b'first\n```\nlast\n'
        digest = hashlib.sha256(content).hexdigest()
        archive = self.root / 'archive.md'
        archive.write_text(f'<!-- file: a/b.txt sha256={digest} eol=1 -->\n````\n' + content.decode() + '````\n', encoding='utf-8')
        restore_mod.restore(archive, self.root / 'restored')
        self.assertEqual((self.root / 'restored/a/b.txt').read_bytes(), content)
        with self.assertRaises(FileExistsError):
            restore_mod.restore(archive, self.root / 'restored')
        archive.write_text(f'<!-- file: ../outside.txt sha256={digest} eol=1 -->\n````\n' + content.decode() + '````\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            restore_mod.restore(archive, self.root / 'unsafe')
        self.assertFalse((self.root / 'unsafe').exists())


if __name__ == '__main__':
    unittest.main()
