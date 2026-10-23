import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile

import numpy as np
from PIL import Image

from pindou import build, cli, originality, palette
from pindou.canvas import Canvas


class ReviewFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def auto_args(self, out):
        refs = self.root / 'refs'
        refs.mkdir(exist_ok=True)
        Image.new('RGB', (4, 4), 'black').save(refs / 'ref.png')
        return argparse.Namespace(refs=str(refs), out=str(out), n=1, name='测试',
                                  subjects='flower', templates='badge', color_set=None,
                                  seed=1, prefix='PO', series=None, cs=12, no_zip=True)

    def minimal_build(self, out, **options):
        return build.build('ink_tattoo', out, n=1, subjects=['flower'], templates=['badge'],
                           cs=12, art_px=1, mockup_b=1, quiet=True, **options)

    def test_auto_rejects_old_output_before_touching_style_evidence(self):
        out = self.root / 'old'
        out.mkdir()
        originals = {'catalog.json': b'OLD_CATALOG', '风格包.json': b'KEEP_STYLE',
                     '风格分析.json': b'KEEP_ANALYSIS'}
        for name, data in originals.items():
            (out / name).write_bytes(data)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(FileExistsError):
            cli.cmd_auto(self.auto_args(out))
        self.assertEqual({p.name: p.read_bytes() for p in out.iterdir()}, originals)

    def test_auto_and_build_both_preserve_old_style_only_output(self):
        for mode in ('auto', 'build'):
            with self.subTest(mode=mode):
                out = self.root / mode
                out.mkdir()
                (out / '风格包.json').write_bytes(b'KEEP_STYLE')
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(FileExistsError):
                    cli.cmd_auto(self.auto_args(out)) if mode == 'auto' else self.minimal_build(out)
                self.assertEqual(list(out.iterdir()), [out / '风格包.json'])
                self.assertEqual((out / '风格包.json').read_bytes(), b'KEEP_STYLE')

    def test_auto_can_build_in_fresh_output_and_keeps_its_analysis(self):
        out = self.root / 'fresh'
        with contextlib.redirect_stdout(io.StringIO()):
            result = cli.cmd_auto(self.auto_args(out))
        self.assertEqual(len(result['entries']), 1)
        self.assertEqual(json.loads((out / '风格分析.json').read_text(encoding='utf-8'))['count'], 1)
        self.assertEqual(json.loads((out / '风格包.json').read_text(encoding='utf-8'))['name'], '测试')

    def test_291_color_canvas_preserves_high_grid_indices(self):
        pal = palette.Palette.from_codes(palette.resolve_set('mard291'))
        cv = Canvas(3, 1, pal)
        for x, index in enumerate((127, 128, 291)):
            cv.pixels([(x, 0)], index)
        self.assertEqual(cv.grid(S=1).tolist(), [[127, 128, 291]])

    def test_291_color_canvas_can_render_art_and_grid_overlay(self):
        pal = palette.Palette.from_codes(palette.resolve_set('mard291'))
        cv = Canvas(1, 1, pal)
        cv.rect(0, 0, 1, 1, 291)
        for grid in (None, np.array([[291]], dtype=np.int16)):
            with self.subTest(overlay=grid is not None):
                art = cv.art(px=2, ss=1, grid=grid)
                self.assertEqual(art.size, (2, 2))
                self.assertEqual(art.getpixel((0, 0)), tuple(pal.tone_rgb(291)))

    def test_small_palette_canvas_keeps_int8_grid_and_same_art(self):
        pal = palette.Palette({'line': 'H07'})
        cv = Canvas(1, 1, pal)
        cv.rect(0, 0, 1, 1, 'line')
        self.assertEqual(cv.grid(S=1).dtype, np.dtype('int8'))
        self.assertEqual(cv.grid(S=1).tolist(), [[1]])
        self.assertEqual(cv.art(px=2, ss=1).getpixel((0, 0)), tuple(pal.tone_rgb(1)))

    def test_check_refreshes_manifest_and_managed_zip_without_other_changes(self):
        out = self.root / 'delivery'
        result = self.minimal_build(out, series='含/特殊名', do_zip=True)
        manifest_path = out / 'manifest.json'
        previous_manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        before = {p.relative_to(out).as_posix(): p.read_bytes() for p in out.rglob('*') if p.is_file()}
        (out / 'private.txt').write_bytes(b'PRIVATE')
        private_zip = out / 'my-own.zip'
        private_zip.write_bytes(b'KEEP_PRIVATE_ZIP')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=None))
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        for item in manifest['files']:
            data = (out / item['path']).read_bytes()
            self.assertEqual(item['bytes'], len(data), item['path'])
            self.assertEqual(item['sha256'], hashlib.sha256(data).hexdigest(), item['path'])
        reports = {'原创性报告.json', '原创性报告.md'}
        self.assertEqual([item for item in manifest['files'] if item['path'] not in reports],
                         [item for item in previous_manifest['files'] if item['path'] not in reports])
        for name, data in before.items():
            if name not in reports | {'manifest.json', Path(result['zip']).name}:
                self.assertEqual((out / name).read_bytes(), data, name)
        self.assertEqual(private_zip.read_bytes(), b'KEEP_PRIVATE_ZIP')
        with zipfile.ZipFile(result['zip']) as z:
            self.assertEqual(set(z.namelist()), {item['path'] for item in manifest['files']} | {'manifest.json'})
            for name in z.namelist():
                self.assertEqual(z.read(name), (out / name).read_bytes(), name)

    def test_check_without_managed_zip_leaves_user_archives_alone(self):
        out = self.root / 'no-archive'
        self.minimal_build(out, do_zip=False)
        user_zip = out / 'personal.zip'
        user_zip.write_bytes(b'KEEP_PERSONAL')
        series = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))['parameters']['series']
        derived_zip = out / f'{build.safe(series)}_全套.zip'
        derived_zip.write_bytes(b'USER_ARCHIVE_AFTER_NO_ZIP_BUILD')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=None))
        self.assertEqual({p.name for p in out.glob('*.zip')}, {'personal.zip', derived_zip.name})
        self.assertEqual(user_zip.read_bytes(), b'KEEP_PERSONAL')
        self.assertEqual(derived_zip.read_bytes(), b'USER_ARCHIVE_AFTER_NO_ZIP_BUILD')

    def test_check_updates_summary_when_reference_scan_is_incomplete(self):
        for with_manifest in (True, False):
            with self.subTest(with_manifest=with_manifest):
                out = self.root / str(with_manifest)
                self.minimal_build(out, do_zip=with_manifest)
                if not with_manifest:
                    (out / 'manifest.json').unlink()
                with contextlib.redirect_stdout(io.StringIO()):
                    result = cli.cmd_check(argparse.Namespace(out=str(out), refs=str(self.root / 'missing-refs')))
                summary = (out / '说明.txt').read_text(encoding='utf-8')
                self.assertIn('核查结果：核查未完成', summary)
                self.assertIn(build.result_label(result), summary)
                if with_manifest:
                    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
                    for item in manifest['files']:
                        self.assertEqual(item['sha256'], hashlib.sha256((out / item['path']).read_bytes()).hexdigest())

    def test_check_legacy_manifest_refreshes_only_series_archive(self):
        out = self.root / 'legacy'
        result = self.minimal_build(out, series='旧/系列', do_zip=True)
        path = out / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest.pop('archive', None)
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        other = out / 'other.zip'
        other.write_bytes(b'KEEP')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=str(self.root / 'missing-refs')))
        with zipfile.ZipFile(result['zip']) as z:
            self.assertEqual(z.read('原创性报告.json'), (out / '原创性报告.json').read_bytes())
            self.assertEqual(z.read('manifest.json'), path.read_bytes())
        self.assertEqual(other.read_bytes(), b'KEEP')

    def test_check_explicit_archive_does_not_touch_series_named_user_zip(self):
        out = self.root / 'explicit'
        result = self.minimal_build(out, do_zip=True)
        original_zip = Path(result['zip'])
        named = out / 'named-delivery.zip'
        original_zip.rename(named)
        original_zip.write_bytes(b'KEEP_USER_ZIP')
        path = out / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['archive'] = named.name
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=str(self.root / 'missing-refs')))
        self.assertEqual(original_zip.read_bytes(), b'KEEP_USER_ZIP')
        with zipfile.ZipFile(named) as z:
            self.assertEqual(z.read('原创性报告.json'), (out / '原创性报告.json').read_bytes())

    def test_check_rejects_private_manifest_member_before_rewriting_reports(self):
        out = self.root / 'tampered'
        self.minimal_build(out, do_zip=True)
        private = out / 'private.txt'
        private.write_bytes(b'PRIVATE')
        path = out / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['files'].append({'path': 'private.txt', 'bytes': 7,
                                  'sha256': hashlib.sha256(b'PRIVATE').hexdigest()})
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        before = {p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=None))
        self.assertEqual({p.name: p.read_bytes() for p in out.iterdir() if p.is_file()}, before)

    def test_check_legacy_manifest_does_not_claim_same_named_user_archive(self):
        out = self.root / 'legacy-no-zip'
        self.minimal_build(out, do_zip=False)
        path = out / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest.pop('archive', None)
        path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        user_zip = out / f'{build.safe(manifest["parameters"]["series"])}_全套.zip'
        user_zip.write_bytes(b'KEEP_USER_ARCHIVE')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.cmd_check(argparse.Namespace(out=str(out), refs=None))
        self.assertEqual(user_zip.read_bytes(), b'KEEP_USER_ARCHIVE')

    def test_delivery_manifest_cannot_alias_private_directory(self):
        out = self.root / 'linked'
        private = out / '参考图'
        private.mkdir(parents=True)
        (private / 'private.txt').write_bytes(b'PRIVATE')
        try:
            os.symlink(private, out / '网格', target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('当前系统不允许创建测试目录链接')
        (out / 'manifest.json').write_text(json.dumps({'archive': None, 'files': [
            {'path': '网格/private.txt', 'bytes': 7, 'sha256': hashlib.sha256(b'PRIVATE').hexdigest()}
        ]}, ensure_ascii=False), encoding='utf-8')
        with self.assertRaises(ValueError):
            build.delivery_context(out)

    def test_single_design_label_does_not_claim_pair_comparison_passed(self):
        pal = palette.Palette({'line': 'H07'})
        single = originality.check([('A', np.ones((1, 1), np.int32), pal)])
        self.assertEqual(single['pair_status'], 'not_applicable')
        label = build.result_label(single)
        self.assertIn('单款', label)
        self.assertIn('参考图未核查', label)
        self.assertNotIn('通过', label)
        multi = originality.check([('A', np.array([[1, 0], [0, 1]]), pal),
                                   ('B', np.array([[1, 1], [1, 1]]), pal)])
        self.assertEqual(multi['pair_status'], 'passed')
        self.assertIn('款间查重通过', build.result_label(multi))

    def restore_module(self):
        spec = importlib.util.spec_from_file_location('restore_review_test', 'scripts/restore_handoff.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def handoff(self, names):
        data = b'first\n'
        sha = hashlib.sha256(data).hexdigest()
        archive = self.root / 'handoff.md'
        archive.write_text(''.join(f'<!-- file: {name} sha256={sha} eol=1 -->\n```\nfirst\n```\n'
                                   for name in names), encoding='utf-8')
        return archive

    def test_restore_rejects_member_parent_conflicts_before_any_write(self):
        restore = self.restore_module().restore
        for i, names in enumerate((['safe.txt', 'a', 'a/b.txt'], ['safe.txt', 'a/b.txt', 'a'])):
            with self.subTest(names=names):
                dest = self.root / f'restore-{i}'
                with self.assertRaises((ValueError, OSError)):
                    restore(self.handoff(names), dest)
                self.assertFalse(dest.exists(), '路径预检查失败前不应开始还原')

    def test_restore_rejects_existing_file_parent_before_any_write(self):
        dest = self.root / 'existing'
        dest.mkdir()
        (dest / 'a').write_bytes(b'KEEP')
        with self.assertRaises((ValueError, FileExistsError, NotADirectoryError)):
            self.restore_module().restore(self.handoff(['safe.txt', 'a/b.txt']), dest)
        self.assertEqual([p.name for p in dest.iterdir()], ['a'])
        self.assertEqual((dest / 'a').read_bytes(), b'KEEP')

    def test_audit_png_contains_complete_source_metadata(self):
        from unittest.mock import patch
        from pindou import motifs
        target = self.root / 'audit.png'
        # One real motif renders the same metadata boundary without the full sheet cost.
        with patch.dict(motifs.MOTIFS, {'flower': motifs.MOTIFS['flower']}, clear=True):
            with contextlib.redirect_stdout(io.StringIO()):
                cli.cmd_audit(argparse.Namespace(style='ink_tattoo', out=str(target)))
        with Image.open(target) as im:
            for key in ('Title', 'Author', 'CreationTime', 'Software', 'Copyright'):
                self.assertTrue(im.info.get(key), key)


if __name__ == '__main__':
    unittest.main()
