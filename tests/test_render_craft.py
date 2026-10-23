"""手工小网格验证绘制、几何和拼豆工艺，不依赖随机作品截图。"""
import math
import time
import unittest

import numpy as np

from pindou import beadify, brushes, geom
from pindou.canvas import Canvas, lin_density, rad_density
from pindou.palette import Palette


def palette():
    return Palette({'white': 'H02', 'mid': 'H04', 'line': 'H07'})


class RenderCraftTests(unittest.TestCase):
    def test_026_canvas_rejects_unusable_dimensions(self):
        for args in ((0, 5, 1), (-2, 5, 1), (5, 5, 0), (0.1, 5, 0.1)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                Canvas(args[0], args[1], palette(), zoom=args[2])

    def test_027_invalid_stroke_and_dot_sizes_are_rejected(self):
        cv = Canvas(5, 5, palette())
        with self.assertRaises(ValueError):
            cv.stroke([(1, 1), (3, 3)], w=-1)
        with self.assertRaises(ValueError):
            cv.circle(2, 2, -0.5)
        with self.assertRaises(ValueError):
            cv.ring(2, 2, 1, float('nan'))

    def test_028_sampling_parameters_are_positive_integers(self):
        cv = Canvas(4, 4, palette())
        for fn in (lambda: cv.grid(0), lambda: cv.mask([(0, 0), (2, 0), (0, 2)], S=0),
                   lambda: cv.art(px=2, ss=0)):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn()

    def test_029_snapped_cells_use_half_open_bounds(self):
        cv = Canvas(4, 4, palette())
        cv.pixels([(1, 1), (-1, 2), (4, 3)])
        self.assertEqual(cv.grid(S=1).tolist(), [[0, 0, 0, 0], [0, 3, 0, 0],
                                               [0, 0, 0, 0], [0, 0, 0, 0]])

    def test_030_explicit_pixels_appear_in_original_art(self):
        cv = Canvas(4, 4, palette())
        cv.pixels([(1, 2)])
        im = np.asarray(cv.art(px=8, ss=1))
        self.assertEqual(tuple(im[20, 12]), (0, 0, 0))

    def test_031_random_effects_replay_identically(self):
        cv = Canvas(14, 14, palette(), seed=103)
        cv.stipple(np.ones((14, 14), bool), .5, spacing=False)
        first = cv.grid()
        self.assertTrue(np.array_equal(first, cv.grid()))
        cv2 = Canvas(14, 14, palette(), seed=18)
        cv2.rect(0, 0, 14, 14, 'white')
        cv2.shade(np.ones((14, 14), bool), .5, ['white', 'line'], jitter=1)
        self.assertTrue(np.array_equal(cv2.grid(), cv2.grid()))

    def test_032_effect_inputs_are_snapshots(self):
        mask = np.ones((4, 4), bool)
        density = np.ones((4, 4))
        cv = Canvas(4, 4, palette())
        cv.stipple(mask, density, spacing=False)
        mask[:] = False
        density[:] = 0
        self.assertEqual(int(np.count_nonzero(cv.grid())), 16)
        field = np.ones((4, 4))
        cv2 = Canvas(4, 4, palette())
        cv2.rect(0, 0, 4, 4, 'white')
        cv2.shade(np.ones((4, 4), bool), field, ['white', 'line'], dither=0)
        field[:] = 0
        self.assertTrue((cv2.grid() == 3).all())

    def test_033_effect_inputs_fail_before_render(self):
        cv = Canvas(4, 4, palette())
        for fn in (lambda: cv.stipple(np.ones((4, 4), bool), 1.1),
                   lambda: cv.stipple(np.ones((3, 4), bool), .5),
                   lambda: cv.shade(np.ones((4, 4), bool), .5, []),
                   lambda: cv.shade(np.ones((4, 4), bool), np.nan, ['line'])):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn()

    def test_034_density_fields_reject_undefined_axes(self):
        with self.assertRaises(ValueError):
            lin_density((3, 3), (1, 1), (1, 1), 0, 1)
        with self.assertRaises(ValueError):
            rad_density((3, 3), (1, 1), 2, 1, 0, 1)
        with self.assertRaises(ValueError):
            rad_density((3, 3), (1, 1), 0, 2, 0, 1, gamma=-1)

    def test_035_points_reject_nonfinite_and_malformed_rows(self):
        for pts in ([[0, 1, 2, 3]], [[0, np.nan]], [[0, np.inf]]):
            with self.subTest(pts=pts), self.assertRaises(ValueError):
                geom.P(pts)

    def test_036_resampling_keeps_corners(self):
        out = geom.resample([(0, 0), (1, 0), (1, 2)], step=2)
        self.assertTrue(np.any(np.all(out == (1, 0), axis=1)))
        self.assertLessEqual(float(np.max(np.linalg.norm(np.diff(out, axis=0), axis=1))), 2)

    def test_037_geometry_rejects_negative_sampling_steps(self):
        for fn in (lambda: geom.resample([(0, 0), (2, 0)], -1),
                   lambda: geom.spline([(0, 0), (1, 2), (2, 0)], -1),
                   lambda: geom.arc(0, 0, 2, 0, math.pi, step=-1),
                   lambda: geom.spiral(0, 0, 3, 1, 0, 2, step=-1)):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn()

    def test_038_closed_spline_finishes_at_start(self):
        out = geom.spline([(0, 0), (3, 0), (2, 2)], closed=True)
        np.testing.assert_allclose(out[-1], out[0], atol=1e-12)

    def test_039_widths_follow_distance_not_vertex_number(self):
        pts = np.array([(0, 0), (1, 0), (10, 0)], float)
        np.testing.assert_allclose(geom.widths_for(pts, [0, 10]), [0, 1, 10])
        np.testing.assert_allclose(geom.widths_for(pts, lambda u: u * 10), [0, 1, 10])

    def test_040_normals_handle_single_and_repeated_vertices(self):
        normal, tangent = geom.normals([(2, 3)])
        np.testing.assert_array_equal(normal, [[0, 0]])
        np.testing.assert_array_equal(tangent, [[0, 0]])
        normal, tangent = geom.normals([(0, 0), (0, 0), (0, 0), (1, 0)])
        np.testing.assert_array_equal(tangent, [[1, 0]] * 4)
        np.testing.assert_array_equal(normal, [[0, 1]] * 4)

    def test_041_hull_preserves_single_unique_point(self):
        out = geom.hull([(2, 3), (2, 3)])
        np.testing.assert_array_equal(out, [[2, 3]])
        self.assertEqual(geom.hull([]).shape, (0, 2))

    def test_042_body_sampling_count_is_honored(self):
        out = geom.body_along([(0, 0), (10, 0)], 2, n=5)
        self.assertEqual(out.shape, (10, 2))
        np.testing.assert_allclose(out[:5, 0], [0, 2.5, 5, 7.5, 10])

    def test_043_hole_filling_accepts_binary_integer_masks(self):
        mask = np.ones((3, 3), np.uint8)
        mask[1, 1] = 0
        out = beadify.fill_holes(mask, 1)
        self.assertTrue(out.all())
        self.assertEqual(out.dtype, np.bool_)
        self.assertEqual(beadify.fill_holes(np.zeros((0, 3), bool)).shape, (0, 3))

    def test_044_finalize_rejects_destructive_parameters(self):
        grid = np.zeros((5, 5), np.int8)
        grid[2, 2] = 3
        for kw in ({'border': -1}, {'close': -1}, {'min_island': -1},
                   {'hole': -1}, {'bridge_max': np.nan}, {'white': 0}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                beadify.finalize(grid, **kw)

    def test_045_bridge_can_keep_a_chain_of_nearby_islands(self):
        g = np.zeros((3, 13), np.int8)
        g[1, 1:4] = 3
        g[1, 6] = 2
        g[1, 9] = 2
        out = beadify.finalize(g, border=0, close=0, min_island=1, hole=0, bridge_max=3)
        self.assertEqual(int(out[1, 9]), 2)
        self.assertEqual(beadify.connected(out), 1)
        self.assertTrue((out[1, 1:10] > 0).all())

    def test_046_empty_pattern_has_no_work_estimate(self):
        info = beadify.stats(np.zeros((52, 52), np.int8), palette())
        self.assertEqual(info['beads'], 0)
        self.assertEqual(info['boards'], 0)
        self.assertEqual(info['star_n'], 0)
        self.assertEqual(info['time'], '0 小时')

    def test_098_counts_merge_roles_using_the_same_bead_code(self):
        pal = Palette({'white': 'H02', 'light': 'H02', 'line': 'H07'})
        info = beadify.stats(np.array([[1, 1, 2, 3]], np.int8), pal)
        self.assertEqual(info['counts'], {'H02': 3, 'H07': 1})
        self.assertEqual(info['beads'], 4)
        self.assertEqual(info['colors'], 2)

    def test_invalid_grid_never_silently_loses_beads(self):
        pal = palette()
        for grid in (np.array([[9]], np.int8), np.array([[-1]], np.int8),
                     np.array([[1.5]]), np.array([[np.nan]])):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                beadify.stats(grid, pal)
        with self.assertRaises(ValueError):
            beadify.connected(np.zeros((2, 2, 2), np.int8))
        for fn in (beadify.finalize, beadify.singles, beadify.connected,
                   lambda g: beadify.to_codes(g, pal), lambda g: beadify.quick_png(g, pal)):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn(np.array([[-1]], np.int8))

    def test_048_difficulty_parameters_cannot_invert_rating(self):
        for diff in ({'bead_div': -1}, {'single_div': 0}, {'star_div': np.nan},
                     {'color_coef': -1}, {'board_coef': np.inf}, [], {'bead_div': '100'}):
            with self.subTest(diff=diff), self.assertRaises(ValueError):
                beadify.stats(np.array([[1]], np.int8), palette(), diff)

    def test_049_default_gradient_spans_the_shape_at_any_zoom(self):
        for zoom in (1, 2):
            with self.subTest(zoom=zoom):
                cv = Canvas(12, 12, palette(), zoom=zoom)
                cv.rect(2, 2, 10, 10, 'white')
                brushes.gradient_fill(cv, [(2, 2), (10, 2), (10, 10), (2, 10)],
                                      ['white', 'line'], lo=0, hi=1)
                grid = cv.grid()
                self.assertEqual(int(grid[int(3 * zoom), int(3 * zoom)]), 1)
                self.assertEqual(int(grid[int(8 * zoom), int(8 * zoom)]), 3)

    def test_050_brush_spacing_fails_instead_of_looping(self):
        cv = Canvas(6, 6, palette())
        poly = [(0, 0), (5, 0), (5, 5), (0, 5)]
        # 负排线间距原版静默漏画；零点阵/棋盘间距原版会无限循环。
        with self.assertRaises(ValueError):
            brushes.hatch(cv, poly, gap=-1)
        with self.assertRaises(ValueError):
            brushes.scales(cv, poly, r=1, gap=-3)
        for fn in (lambda: brushes.dots(cv, poly, gap=0),
                   lambda: brushes.checker(cv, poly, cell=0),
                   lambda: brushes.seigaiha(cv, poly, r=0),
                   lambda: brushes.halftone(cv, poly, gap=0),
                   lambda: brushes.waves(cv, poly, period=0)):
            with self.subTest(fn=fn), self.assertRaises(ValueError):
                fn()

    def test_singles_and_preview_keep_known_pixel_results(self):
        g = np.array([[1, 1, 0], [0, 3, 2]], np.int8)
        self.assertEqual(beadify.singles(g), 2)
        im = beadify.quick_png(g, palette(), B=2)
        self.assertEqual(im.shape, (4, 6, 3))
        self.assertEqual(tuple(im[3, 3]), (0, 0, 0))
        self.assertEqual(tuple(im[1, 5]), (238, 235, 230))
        with self.assertRaises(ValueError):
            beadify.quick_png(g, palette(), B=0)

    def test_047_preview_is_pixel_identical_with_less_work(self):
        pal = palette()
        grid = np.random.default_rng(12).integers(0, len(pal), (156, 156), dtype=np.int8)

        def old_preview():
            out = np.zeros((1248, 1248, 3), np.uint8)
            for i in range(len(pal)):
                mask = np.kron((grid == i).astype(np.uint8), np.ones((8, 8), np.uint8)).astype(bool)
                out[mask] = pal.tone_rgb(i) if i else (238, 235, 230)
            out[::8, :] = (out[::8, :] * .88).astype(np.uint8)
            out[:, ::8] = (out[:, ::8] * .88).astype(np.uint8)
            return out

        np.testing.assert_array_equal(beadify.quick_png(grid, pal, 8), old_preview())
        # 同一进程、相同输入比较相对用时，避免依赖机器绝对速度。
        costs = []
        for fn in (old_preview, lambda: beadify.quick_png(grid, pal, 8)):
            samples = []
            for _ in range(5):
                start = time.perf_counter()
                fn()
                samples.append(time.perf_counter() - start)
            costs.append(float(np.median(samples)))
        self.assertLess(costs[1], costs[0] * .7, f'旧路径 {costs[0]:.6f}s，新路径 {costs[1]:.6f}s')


if __name__ == '__main__':
    unittest.main()
