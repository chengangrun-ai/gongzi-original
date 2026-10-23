"""数据与方案边界回归：每个测试对应一项实际修复。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from pindou import palette, recipes, stylepack


def style(**overrides):
    result = {'palette': {'white': '#FFFFFF', 'mid': '#888888', 'line': '#000000'}}
    result.update(overrides)
    return result


class DataPlanningTests(unittest.TestCase):
    def test_001_normalize_isolates_nested_defaults_and_input(self):
        before = copy.deepcopy(stylepack.DEFAULTS)
        source = style(tags=['local'], difficulty={'bead_div': 900})
        normalized = stylepack.normalize(source)
        normalized['formats']['S'] = 99
        normalized['tags'].append('changed')
        normalized['difficulty']['bead_div'] = 1
        try:
            self.assertEqual(stylepack.DEFAULTS, before)
            self.assertEqual(source['tags'], ['local'])
            self.assertEqual(source['difficulty'], {'bead_div': 900})
        finally:
            stylepack.DEFAULTS.clear()
            stylepack.DEFAULTS.update(before)

    def test_002_missing_color_roles_resolve_to_available_roles(self):
        normalized = stylepack.normalize({'palette': {'line': '#000000'}})
        self.assertEqual(normalized['fill'], 'line')
        self.assertEqual(normalized['shade1'], 'line')
        self.assertEqual(normalized['hi'], 'line')

    def test_003_rejects_unsafe_numeric_style_settings(self):
        for fields in ({'line_width': float('nan')}, {'detail_width': -1},
                       {'accent_rate': 2}, {'splatter': 2.5},
                       {'difficulty': {'bead_div': 0}}, {'weights': {'line': float('inf')}}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                stylepack.normalize(style(**fields))

    def test_004_rejects_invalid_format_distributions(self):
        for distribution in ({'wide': 1}, {'S': -1, 'V': 1}, {'S': 0}, {'S': float('inf')}, {}):
            with self.subTest(distribution=distribution), self.assertRaises(ValueError):
                stylepack.normalize(style(formats=distribution))

    def test_005_rejects_unknown_textures_including_pool(self):
        for fields in ({'fill_texture': 'mistyped'}, {'face_texture': 'mistyped'},
                       {'texture_pool': ['solid', 'mistyped']}, {'texture_pool': 'solid'}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                stylepack.normalize(style(**fields))

    def test_006_palette_schema_reports_misspelled_roles(self):
        for colors in ({'line': '#000000', 'accnet': '#FF0000'}, {'line': '#12345678'}, []):
            with self.subTest(colors=colors), self.assertRaises(ValueError):
                stylepack.normalize({'palette': colors})

    def test_007_rejects_unknown_background_mode(self):
        with self.assertRaises(ValueError):
            stylepack.normalize(style(bg='filled'))

    def test_008_dna_conversion_does_not_modify_source(self):
        dna = {'palette_roles': {'mid': '#888888'}, 'subjects': ['cat']}
        before = copy.deepcopy(dna)
        result = stylepack.from_dna(dna, name='sample')
        result['subjects'].append('bird')
        self.assertEqual(dna, before)
        self.assertEqual(result['palette']['line'], '#1A1A1A')

    def test_009_style_registry_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as folder:
            for filename in ('one.json', 'two.json'):
                Path(folder, filename).write_text(json.dumps({'id': 'same'}), encoding='utf-8')
            with patch.object(stylepack, 'STYLE_DIR', folder), self.assertRaises(ValueError):
                stylepack.list_styles()

    def test_010_plan_requires_a_positive_integer_count(self):
        for count in (0, -2, True, 1.5):
            with self.subTest(count=count), self.assertRaises(ValueError):
                recipes.plan(style(), n=count)

    def test_011_plan_reports_all_unknown_selections(self):
        for fields in ({'subjects': ['cat', 'typo']}, {'templates': ['badge', 'typo']},
                       {'subjects': []}, {'templates': []}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                recipes.plan(style(), n=2, **fields)

    def test_012_single_selection_strings_are_not_split_into_letters(self):
        try:
            rows = recipes.plan(style(), n=2, subjects='cat', templates='badge')
        except (SystemExit, ValueError) as exc:
            self.fail(f'单项字符串本应可用：{exc}')
        self.assertEqual([(r['subject'], r['template']) for r in rows], [('cat', 'badge')] * 2)

    def test_013_duplicate_options_do_not_bias_or_repeat_subjects(self):
        clean = recipes.plan(style(), 4, ['cat', 'moon'], ['badge', 'frame'], seed=3)
        duplicates = recipes.plan(style(), 4, ['cat', 'cat', 'moon'], ['badge', 'badge', 'frame'], seed=3)
        self.assertEqual(duplicates, clean)

    def test_014_each_combination_cycle_is_complete_before_repeating(self):
        rows = recipes.plan(style(), 12, ['cat', 'moon', 'bird'], ['badge', 'frame'], seed=0)
        for offset in (0, 6):
            pairs = {(r['subject'], r['template']) for r in rows[offset:offset + 6]}
            self.assertEqual(len(pairs), 6)

    def test_015_explicit_ids_must_be_complete_unique_and_nonempty(self):
        for identifiers in ([], ['one'], ['one', 'one'], ['A', 'a'], ['one', '  '], 'ab'):
            with self.subTest(identifiers=identifiers), self.assertRaises(ValueError):
                recipes.plan(style(), n=2, ids=identifiers)

    def test_016_seed_validation_and_numpy_integer_seed_are_stable(self):
        for seed in (True, 1.5, -1):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                recipes.plan(style(), n=1, seed=seed)
        seed = np.int64(2**63 - 1)
        rows = recipes.plan(style(), n=1, seed=seed)
        self.assertEqual(rows[0]['seed'], (2**63 - 1) * 1000 + 11)
        self.assertEqual(rows, recipes.plan(style(), n=1, seed=int(seed)))

    def test_017_compose_rejects_invalid_specs_before_drawing(self):
        valid = {'id': 'A', 'subject': 'cat', 'template': 'badge', 'format': 'S', 'seed': 1}
        for changes in ({'subject': 'typo'}, {'template': 'typo'}, {'format': 'wide'}, {'seed': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                recipes.compose(dict(valid, **changes), style(), S=1)

    def test_018_composition_provenance_is_an_independent_snapshot(self):
        source = recipes.plan(style(), n=1, subjects=['cat'], templates=['badge'])[0]
        expected = copy.deepcopy(source)
        result = recipes.compose(source, style(), S=1)
        source['seed'] = 999
        source['tags'].append('changed')
        self.assertEqual(result['spec'], expected)

    def test_019_hex_colors_accept_standard_shorthand_and_reject_extra_bytes(self):
        try:
            self.assertEqual(palette._hex2rgb(' #aB3 '), (170, 187, 51))
        except (TypeError, ValueError) as exc:
            self.fail(f'标准三位色值本应可用：{exc}')
        for value in ('#12345678', '##FFFFFF', '#12', 'red'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                palette._hex2rgb(value)

    def test_020_nearest_preserves_restricted_color_set(self):
        with self.assertRaises(ValueError):
            palette.nearest('#000000', [])
        try:
            code, error = palette.nearest('#000000', ['h7'])
        except (KeyError, ValueError) as exc:
            self.fail(f'色号简写本应被规范化：{exc}')
        self.assertEqual(code, 'H07')
        self.assertAlmostEqual(error, 0, places=4)

    def test_021_rgb_conversion_rejects_nonfinite_and_invalid_shape(self):
        for value in ([[0, 0, float('nan')]], [[-1, 0, 0]], [[256, 0, 0]], [[1, 2], [3, 4], [5, 6]]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                palette.srgb2lab(value)

    def test_022_color_card_callers_cannot_pollute_cached_colors(self):
        original = palette.card()['H07']['rgb']
        snapshot = palette.card()
        try:
            snapshot['H07']['rgb'] = (123, 45, 67)
            self.assertEqual(palette.rgb('H07'), original)
        finally:
            snapshot['H07']['rgb'] = original

    def test_023_palette_access_uses_canonical_codes_and_valid_indices(self):
        pal = palette.Palette({'line': 'h7'})
        self.assertEqual(pal.code('line'), 'H07')
        for index in (-1, len(pal), True, 1.5, None):
            with self.subTest(index=index), self.assertRaises(ValueError):
                pal.index(index)

    def test_024_imported_palette_keeps_more_than_eight_real_colors(self):
        codes = ['H02', 'H03', 'H04', 'H05', 'H07', 'F05', 'A01', 'B01', 'C01', 'D01']
        pal = palette.Palette.from_codes(codes)
        self.assertEqual(len(pal), 11)
        self.assertEqual({pal.code(role) for role in pal.used()}, set(codes))
        self.assertTrue(all(pal.index_of_code(code) > 0 for code in codes))
        full_card = palette.resolve_set('mard291')
        full_palette = palette.Palette.from_codes(full_card)
        self.assertEqual(len(full_palette), 292)
        self.assertEqual({full_palette.code(role) for role in full_palette.used()}, set(full_card))

    def test_025_distinct_color_roles_receive_distinct_real_beads(self):
        pal = palette.Palette.from_style({'palette': {role: '#000000' for role in palette.ROLE_ORDER}})
        self.assertEqual(len(set(pal.codes.values())), 8)
        self.assertEqual({r['code'] for r in pal.report}, set(pal.codes.values()))


if __name__ == '__main__':
    unittest.main()
