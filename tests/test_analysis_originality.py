"""合成图片回归夹具；不依赖外部参考素材。"""
import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image

from pindou import analyze, originality


class TinyPalette:
    def __len__(self):
        return 3

    def tone_rgb(self, index):
        return (0, 0, 0) if index == 1 else (255, 255, 255)


class AnalysisOriginalityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.pal = TinyPalette()

    def tearDown(self):
        self.temp.cleanup()

    def image(self, name, data, **save):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.asarray(data, np.uint8)).save(path, **save)
        return path

    def design(self, name='A'):
        return (name, np.array([[1, 1, 0], [0, 1, 0], [0, 1, 1]], np.uint8), self.pal)

    def dna(self):
        return analyze.analyze_image(self.image('base.png', np.full((4, 4, 3), 128)))

    def test_051_exif_rotation_is_applied_in_both_image_readers(self):
        a = np.zeros((3, 5, 3), np.uint8)
        a[:, 0] = 255
        exif = Image.Exif()
        exif[274] = 6
        rotated = self.image('rotate.png', a, exif=exif)
        plain = self.image('plain.png', np.rot90(a, 3))
        self.assertEqual(analyze.analyze_image(rotated)['size'], [3, 5])
        np.testing.assert_array_equal(originality.naive_bead(rotated), originality.naive_bead(plain))

    def test_052_transparency_uses_visible_white_composite(self):
        rgba = np.zeros((4, 4, 4), np.uint8)
        rgba[1:3, 1:3] = (255, 0, 0, 255)
        rgb = np.full((4, 4, 3), 255, np.uint8)
        rgb[1:3, 1:3] = (255, 0, 0)
        transparent = self.image('alpha.png', rgba)
        visible = self.image('white.png', rgb)
        np.testing.assert_array_equal(analyze._load(transparent), analyze._load(visible))
        np.testing.assert_array_equal(originality.naive_bead(transparent), originality.naive_bead(visible))

    def test_053_integer_samples_retain_fractional_cluster_center(self):
        colors, shares = analyze.kmeans(np.array([[0, 0, 0], [1, 1, 1]], np.uint8), k=1)
        np.testing.assert_allclose(colors, [[0.5, 0.5, 0.5]])
        np.testing.assert_array_equal(shares, [1.0])

    def test_054_flat_image_has_one_active_color(self):
        dna = self.dna()
        self.assertEqual(len(dna['colors']), 1)
        self.assertEqual(dna['colors'][0]['share'], 1.0)

    def test_055_invalid_cluster_samples_and_controls_are_rejected(self):
        for data in (np.empty((0, 3)), np.array([[1, 2]]), np.array([[np.nan, 0, 0]]), np.array([[256, 0, 0]])):
            with self.subTest(data=str(data)), self.assertRaises(ValueError):
                analyze.kmeans(data)
        for options in ({'k': 0}, {'iters': 0}, {'k': True}, {'seed': -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                analyze.kmeans(np.array([[0, 0, 0]]), **options)

    def test_056_source_dimensions_are_not_sampling_dimensions(self):
        dna = analyze.analyze_image(self.image('large.png', np.zeros((10, 1000, 3))))
        self.assertEqual(dna['size'], [1000, 10])
        self.assertEqual(dna['analysis_size'], [640, 6])
        self.assertEqual(dna['aspect'], 100.0)

    def test_057_small_and_constant_mirror_symmetry_is_finite(self):
        for size in (1, 4, 16):
            dna = analyze.analyze_image(self.image(f'flat{size}.png', np.full((size, size, 3), 128)))
            self.assertEqual(dna['symmetry'], 1.0)
            json.dumps(dna, allow_nan=False)

    def test_058_two_pixel_stripe_has_detectable_edges(self):
        dna = analyze.analyze_image(self.image('edge.png', [[[0]*3, [255]*3]] * 2))
        self.assertGreater(dna['edge_density'], 0.9)

    def test_059_mud_does_not_join_opposite_canvas_edges(self):
        a = np.full((52, 52, 3), 128, np.uint8)
        a[:, -1] = 255
        dna = analyze.analyze_image(self.image('boundary.png', a))
        self.assertEqual(dna['bead_mud'], 0.019)

    def test_060_background_border_counts_each_corner_once(self):
        a = np.full((3, 3, 3), 255, np.uint8)
        a[::2, ::2] = 0
        self.assertEqual(analyze.analyze_image(self.image('corners.png', a))['bg']['hex'], '#808080')

    def test_061_aggregate_color_center_is_order_independent_and_weighted(self):
        a, b = self.dna(), self.dna()
        a['colors'] = [{'rgb': [120]*3, 'hex': '#787878', 'share': 1.0}]
        b['colors'] = [{'rgb': [130]*3, 'hex': '#828282', 'share': 1.0}]
        forward = analyze.aggregate([a, b])['colors']
        reverse = analyze.aggregate([b, a])['colors']
        self.assertEqual(forward, reverse)
        self.assertEqual(forward[0]['rgb'], [125]*3)

    def test_062_aggregate_result_does_not_alias_input_dna(self):
        dna = self.dna()
        original = copy.deepcopy(dna)
        result = analyze.aggregate([dna])
        result['images'][0]['bg']['share'] = 0.0
        result['colors'][0]['rgb'][0] = 0
        self.assertEqual(dna, original)

    def test_063_aggregate_rejects_nonfinite_or_malformed_dna(self):
        for key, value in (('aspect', 0), ('contrast', np.nan), ('tones', [1, 0]), ('colors', [])):
            dna = self.dna()
            dna[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                analyze.aggregate([dna])

    def test_064_recursive_scan_has_canonical_directory_order(self):
        self.image('z/last.png', np.full((3, 3, 3), 240))
        self.image('a/first.png', np.full((3, 3, 3), 20))
        self.image('B.png', np.full((3, 3, 3), 60))
        self.image('a.png', np.full((3, 3, 3), 100))
        result = analyze.run(self.root, verbose=False)
        self.assertEqual([d['file'] for d in result['images']], ['a.png', 'first.png', 'B.png', 'last.png'])

    def test_065_duplicate_visible_images_do_not_bias_statistics_or_ref_count(self):
        black = np.zeros((4, 4, 3), np.uint8)
        self.image('a.png', black)
        self.image('b.bmp', black)
        self.image('c.png', np.full((4, 4, 3), 255))
        result = analyze.run(self.root, verbose=False)
        self.assertEqual(result['count'], 2)
        self.assertEqual(result['scan']['duplicates_count'], 1)
        self.assertEqual(len(originality.refs_maps(self.root)), 2)

    def test_066_corrupt_image_diagnostics_are_quiet_and_do_not_leak_paths(self):
        self.image('ok.png', np.full((4, 4, 3), 100))
        (self.root / 'broken.png').write_bytes(b'bad image')
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result = analyze.run(self.root, verbose=False)
        self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(result['scan']['failed_count'], 1)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_067_ink_map_rejects_invalid_grid_indices(self):
        for grid in ([], [[-1]], [[3]], [[1.5]], [[np.nan]], [[[1]]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                originality.ink_map(grid, self.pal)

    def test_068_identical_constant_maps_are_duplicates(self):
        self.assertEqual(originality.ncc(np.ones((3, 3)), np.ones((3, 3))), 1.0)
        self.assertEqual(originality.ncc(np.ones((3, 3)), np.zeros((3, 3))), 0.0)
        result = originality.check([('A', np.ones((2, 2), np.uint8), self.pal),
                                    ('B', np.ones((2, 2), np.uint8), self.pal)])
        self.assertFalse(result['pass_'])

    def test_069_similarity_rejects_invalid_map_shapes_and_nonfinite_data(self):
        for a, b in ((np.array([[np.nan]]), np.array([[0]])), (np.array([]), np.array([])), (np.zeros((2, 2)), np.zeros((3, 3)))):
            with self.subTest(a=str(a)), self.assertRaises(ValueError):
                originality.ncc(a, b)
        with self.assertRaises(ValueError):
            originality.dhash(np.array([[2.0]]))

    def test_070_ncc_does_not_overflow_float32_norms(self):
        a = np.array([[0, 1e30], [2e30, 3e30]], np.float32)
        self.assertAlmostEqual(originality.ncc(a, a), 1.0, places=12)

    def test_071_check_rejects_empty_designs_duplicate_ids_and_blank_work(self):
        for designs in ([], [self.design(), self.design()], [('A', np.zeros((2, 2)), self.pal)]):
            with self.subTest(designs=str(designs)), self.assertRaises(ValueError):
                originality.check(designs)

    def test_072_reference_scope_distinguishes_missing_and_failed_checks(self):
        no_refs = originality.check([self.design()])
        self.assertEqual(no_refs['status'], 'limited')
        self.assertIsNone(no_refs['worst_ref_ncc'])
        self.assertIsNone(no_refs['rows'][0]['dhash'])
        invalid = originality.check([self.design()], self.root / 'missing')
        self.assertFalse(invalid['pass_'])
        self.assertEqual(invalid['status'], 'incomplete')
        (self.root / 'bad.png').write_bytes(b'broken')
        broken = originality.check([self.design()], self.root)
        self.assertFalse(broken['pass_'])
        self.assertEqual(broken['scan']['failed_count'], 1)

    def test_073_minimum_ref_hash_uses_all_references(self):
        rng = np.random.default_rng(4)
        a = rng.integers(0, 2, (8, 8))
        self.image('noisy.png', np.repeat(np.clip((1-a+np.random.default_rng(8).normal(0, .3, (8, 8)))*255, 0, 255)[..., None], 3, axis=2))
        row_offsets = np.random.default_rng(0).random((8, 1)) * .75
        self.image('rows.png', np.repeat(((1 - (a * .25 + row_offsets)) * 255)[..., None], 3, axis=2))
        grid = np.where(a, 1, 2).astype(np.uint8)
        result = originality.check([('A', grid, self.pal)], self.root)
        # noisy的NCC约0.801、dHash=14；rows的NCC约0.359、dHash=8。
        self.assertEqual(result['min_ref_dhash'], 8)
        self.assertEqual(result['rows'][0]['min_dhash'], 8)
        self.assertEqual(result['rows'][0]['nearest_ref'], 'noisy.png')
        self.assertEqual(result['rows'][0]['dhash'], 14)
        self.assertEqual(result['rows'][0]['nearest_hash_ref'], 'rows.png')

    def test_074_same_basename_references_have_distinct_private_labels(self):
        self.image('private_a/same.png', np.zeros((3, 3, 3)))
        self.image('private_b/same.png', np.full((3, 3, 3), 255))
        labels = [name for name, _ in originality.refs_maps(self.root)]
        self.assertEqual(len(set(labels)), 2)
        self.assertTrue(all('private_' not in label for label in labels))

    def test_075_markdown_escapes_user_cells_and_states_check_boundary(self):
        result = originality.check([self.design('A|<img>\nB')])
        text = originality.report_md(result, series='<script>|标题', style='x\ny')
        self.assertNotIn('<script>', text)
        self.assertNotIn('A|<img>\nB', text)
        self.assertIn('法律', text)
        self.assertNotIn('999', text)
        self.assertIn('仅款间', text)


if __name__ == '__main__':
    unittest.main()
