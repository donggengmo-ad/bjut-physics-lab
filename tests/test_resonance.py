import io
import math
import unittest

import numpy as np
import pandas as pd

from experiments.exp_lower_02_交流电路谐振 import (
    CURRENT, FREQ, UR, analyze_curve, scan_table,
)
from experiment_case import ExperimentCase, open_app, select_view

def Experiment():
    return ExperimentCase('lower_02_resonance')



class ResonanceCalculations(unittest.TestCase):
    def setUp(self):
        self.exp = Experiment()
        self.exp.fill_data()

    def test_supplied_data_and_units(self):
        for resistance in (100, 500):
            table = self.exp.final_df[self.exp.scan_keys[resistance]]
            self.assertEqual(len(table), 30)
            self.assertEqual(table[FREQ].iloc[0], 1400)
            self.assertEqual(table[FREQ].iloc[-1], 3400)
            self.assertEqual(self.exp.measured_f0[resistance], 2240)
        table100 = self.exp.final_df[self.exp.scan_keys[100]]
        table500 = self.exp.final_df[self.exp.scan_keys[500]]
        self.assertAlmostEqual(table100[UR].iloc[0], 65)
        self.assertAlmostEqual(table100[CURRENT].iloc[0], 0.65)
        self.assertAlmostEqual(table500[UR].iloc[12], 1097)
        self.assertAlmostEqual(table500[CURRENT].iloc[12], 2.194)
        self.assertAlmostEqual(self.exp.theoretical_f0, 2250.7907903927653)

    def test_automatic_cutoffs_and_q(self):
        # 从用户数据的包围点独立计算，电压使用 V、频率使用 Hz。
        expected = {
            100: (
                2100 + 100 * (0.803 / math.sqrt(2) - 0.442) / (0.731 - 0.442),
                2300 + 100 * (0.803 / math.sqrt(2) - 0.700) / (0.439 - 0.700),
                (11.904154565430094, 12.00, 12.05, 10.815142566836027),
            ),
            500: (
                1900 + 100 * (1.097 / math.sqrt(2) - 0.703) / (0.812 - 0.703),
                2500 + 100 * (1.097 / math.sqrt(2) - 0.826) / (0.745 - 0.826),
                (2.7259320785911627, 2.715, 2.718, 3.762114596768661),
            ),
        }
        for resistance, (lower, upper, q) in expected.items():
            curve = self.exp.curves[resistance]
            self.assertAlmostEqual(curve['f1'], lower)
            self.assertAlmostEqual(curve['f2'], upper)
            self.assertAlmostEqual(curve['bandwidth'], upper - lower)
            for actual, reference in zip(self.exp.q[resistance], q):
                self.assertAlmostEqual(actual, reference)

    def test_exact_crossings_and_peak_at_edge(self):
        table = pd.DataFrame({FREQ: [100, 200, 300, 400, 500],
                              CURRENT: [1, 2, 2 * math.sqrt(2), 2, 1]})
        result = analyze_curve(table)
        self.assertAlmostEqual(result['f1'], 200)
        self.assertAlmostEqual(result['f2'], 400)
        self.assertAlmostEqual(result['bandwidth'], 200)
        result = analyze_curve(table.iloc[2:])
        self.assertEqual(result['f0'], 300)  # 峰值在边缘仍按最大值记录频率。
        self.assertTrue(math.isnan(result['bandwidth']))

    def test_ambiguous_crossings_do_not_produce_bandwidth(self):
        table = pd.DataFrame({FREQ: [100, 200, 300, 400, 500, 600],
                              CURRENT: [1, 3, 1, 4, 2, 1]})
        result = analyze_curve(table)
        self.assertIsNotNone(result['cutoff_error'])
        self.assertTrue(math.isnan(result['f1']))
        self.assertTrue(math.isnan(result['bandwidth']))

    def test_repeated_peak_top_without_cutoff_coverage(self):
        values = [945, 946, 947, 947, 947, 947, 946, 945]
        table = scan_table(pd.DataFrame({FREQ: list(range(2200, 2280, 10)), UR: values}), 500)
        result = analyze_curve(table)
        self.assertEqual(result['peak_frequencies'], (2220, 2230, 2240, 2250))
        self.assertAlmostEqual(result['imax'], 947 / 500)
        self.assertTrue(math.isnan(result['f0']))
        self.assertTrue(math.isnan(result['bandwidth']))
        self.assertIsNotNone(result['peak_error'])
        self.assertIsNotNone(result['cutoff_error'])

    def test_repeated_peak_preserves_cutoffs_and_plot_labels(self):
        # 将用户峰顶片段嵌入测试用完整扫描，不修改默认测量记录。
        key = self.exp.scan_keys[500]
        table = self.exp.initial_df[key].copy()
        values = [945, 946, 947, 947, 947, 947, 946, 945]
        table.loc[table[FREQ].between(2200, 2300), UR] = values + [944, 943, 942]
        self.exp.set_initial_df(table, key)
        self.exp.fill_data()
        result = self.exp.curves[500]
        level_mv = 947 / math.sqrt(2)
        lower = 1800 + (level_mv - 608) * 100 / (703 - 608)
        upper = 2700 + (level_mv - 671) * 100 / (605 - 671)
        self.assertAlmostEqual(result['f1'], lower)
        self.assertAlmostEqual(result['f2'], upper)
        self.assertAlmostEqual(result['bandwidth'], upper - lower)
        self.assertIsNone(result['cutoff_error'])
        self.assertTrue(math.isnan(result['f0']))
        self.assertTrue(math.isnan(self.exp.q[500][3]))
        self.assertTrue(all(math.isfinite(v) for v in self.exp.q[500][:3]))
        labels = [a for a in self.exp.build_plot().layout.annotations
                  if a.xref == 'x' and a.text.startswith('R=500 Ω')]
        self.assertEqual(len(labels), 2)
        for label, expected in zip(labels, [lower, upper]):
            self.assertAlmostEqual(label.x, expected)
        pd.testing.assert_frame_equal(self.exp.initial_df[key], table, check_dtype=False)

    def test_separated_repeated_peaks_do_not_bridge_passbands_or_missing_values(self):
        for middle in (1, math.nan, 4 / math.sqrt(2)):
            with self.subTest(middle=middle):
                table = pd.DataFrame({FREQ: [100, 200, 300, 400, 500],
                                      CURRENT: [1, 4, middle, 4, 1]})
                result = analyze_curve(table)
                self.assertIsNotNone(result['cutoff_error'])
                self.assertTrue(math.isnan(result['bandwidth']))

    def test_gap_between_crossing_and_peak_invalidates_only_affected_side(self):
        for values, missing_field, valid_field in [
            ([1, 3, math.nan, 4, 2, 1], 'f1', 'f2'),
            ([1, 2, 4, math.nan, 3, 1], 'f2', 'f1'),
        ]:
            with self.subTest(values=values):
                curve = analyze_curve(pd.DataFrame({FREQ: np.arange(1, 7) * 100, CURRENT: values}))
                self.assertTrue(math.isnan(curve[missing_field]))
                self.assertTrue(math.isfinite(curve[valid_field]))
                self.assertTrue(math.isnan(curve['bandwidth']))

    def test_tangent_contacts_are_not_cutoff_boundaries(self):
        level = 4 / math.sqrt(2)
        curve = analyze_curve(pd.DataFrame({FREQ: np.arange(1, 8) * 100,
                                            CURRENT: [3, level, 3, 4, 3, level, 3]}))
        self.assertTrue(math.isnan(curve['f1']))
        self.assertTrue(math.isnan(curve['f2']))
        self.assertTrue(math.isnan(curve['bandwidth']))

    def test_peak_at_scan_edge_keeps_other_cutoff(self):
        for values, missing_field, valid_field in [
            ([4, 3, 2, 1], 'f1', 'f2'),
            ([1, 2, 3, 4], 'f2', 'f1'),
            ([4, 4, 2, 1], 'f1', 'f2'),
        ]:
            with self.subTest(values=values):
                curve = analyze_curve(pd.DataFrame({FREQ: [100, 200, 300, 400], CURRENT: values}))
                self.assertTrue(math.isnan(curve[missing_field]))
                self.assertTrue(math.isfinite(curve[valid_field]))
                self.assertTrue(math.isnan(curve['bandwidth']))

    def test_half_power_plateau_is_ambiguous_but_exact_endpoint_is_valid(self):
        peak = 2 * math.sqrt(2)
        curve = analyze_curve(pd.DataFrame({FREQ: [100, 200, 300, 400, 500, 600],
                                            CURRENT: [1, 2, 2, peak, 2, 1]}))
        self.assertTrue(math.isnan(curve['f1']))
        self.assertEqual(curve['f2'], 500)
        curve = analyze_curve(pd.DataFrame({FREQ: [100, 200, 300], CURRENT: [2, peak, 2]}))
        self.assertEqual((curve['f1'], curve['f2'], curve['bandwidth']), (100, 300, 200))

    def test_empty_flat_and_short_scans_do_not_invent_bandwidth(self):
        for values in ([], [math.nan] * 5, [0] * 5, [1] * 5, [3], [2, 3]):
            with self.subTest(values=values):
                curve = analyze_curve(pd.DataFrame({FREQ: np.arange(1, len(values) + 1) * 100,
                                                    CURRENT: values}))
                self.assertTrue(math.isnan(curve['bandwidth']))
                self.assertIsNotNone(curve['cutoff_error'])

    def test_missing_samples_outside_passband_do_not_destroy_valid_cutoffs(self):
        curve = analyze_curve(pd.DataFrame({FREQ: np.arange(1, 8) * 100,
                                            CURRENT: [math.nan, 1, 3, 4, 3, 1, math.nan]}))
        self.assertTrue(math.isfinite(curve['bandwidth']))
        self.assertIsNone(curve['cutoff_error'])

    def test_close_but_unequal_peaks_remain_distinct(self):
        curve = analyze_curve(pd.DataFrame({FREQ: [100, 200, 300, 400],
                                            CURRENT: [1, 4, 4 + 1e-10, 1]}))
        self.assertEqual(curve['f0'], 300)
        self.assertIsNone(curve['peak_error'])
        self.assertTrue(math.isfinite(curve['bandwidth']))

    def test_separated_equal_maxima_in_one_connected_passband(self):
        curve = analyze_curve(pd.DataFrame({FREQ: [100, 200, 300, 400, 500],
                                            CURRENT: [1, 4, 3, 4, 1]}))
        self.assertTrue(math.isnan(curve['f0']))
        self.assertTrue(math.isfinite(curve['bandwidth']))
        self.assertIsNone(curve['cutoff_error'])

    def test_seeded_scans_match_independent_interpolation(self):
        rng = np.random.default_rng(20261017)
        for case in range(200):
            plateau_size = int(rng.integers(1, 7))
            currents = np.array([.2, .6, .9] + [1.] * plateau_size + [.85, .5, .1])
            currents *= float(rng.uniform(.001, 100))
            frequencies = np.cumsum(rng.uniform(1, 150, len(currents))) + 100
            table = pd.DataFrame({FREQ: frequencies, CURRENT: currents})
            before = table.copy(deep=True)
            curve = analyze_curve(table)
            level = max(currents) / math.sqrt(2)
            lower = frequencies[1] + (level - currents[1]) / (currents[2] - currents[1]) * (frequencies[2] - frequencies[1])
            i = 3 + plateau_size
            upper = frequencies[i] + (level - currents[i]) / (currents[i+1] - currents[i]) * (frequencies[i+1] - frequencies[i])
            with self.subTest(case=case, plateau_size=plateau_size):
                self.assertAlmostEqual(curve['f1'], lower)
                self.assertAlmostEqual(curve['f2'], upper)
                self.assertAlmostEqual(curve['bandwidth'], upper - lower)
                self.assertEqual(math.isfinite(curve['f0']), plateau_size == 1)
                pd.testing.assert_frame_equal(before, table)

    def test_scan_rejects_nonfinite_negative_or_duplicate_inputs(self):
        for column, value in [(UR, math.inf), (UR, -math.inf), (UR, -1),
                               (FREQ, math.inf), (FREQ, math.nan), (FREQ, 0), (FREQ, 100)]:
            with self.subTest(column=column, value=value):
                table = pd.DataFrame({FREQ: [100, 200, 300], UR: [1, 3, 1]})
                table.loc[1, column] = value
                with self.assertRaises(ValueError):
                    scan_table(table, 500)

    def test_edge_cases_flow_through_session_explanation_and_report_exports(self):
        from core.session import ExperimentSession
        from core.plots import report_from_plotly
        from ui.charts import figure_bytes
        scenarios = {
            'blank': [], 'zero': [0] * 6, 'flat': [400] * 6,
            'single': [400], 'repeated': [100, 400, 400, 100],
            'left_edge': [400, 300, 100], 'right_edge': [100, 300, 400],
            'disconnected': [100, 400, math.nan, 400, 100],
            'gap_before_peak': [100, 300, math.nan, 400, 100],
            'tangent': [300, 400 / math.sqrt(2), 300, 400, 300, 400 / math.sqrt(2), 300],
        }
        spec = self.exp.spec
        session = ExperimentSession.create(spec)
        for name, values in scenarios.items():
            with self.subTest(scenario=name):
                for key in self.exp.scan_keys.values():
                    frame = session.inputs.tables[key].copy()
                    frame[UR] = values + [math.nan] * (len(frame) - len(values))
                    session.edit_table(key, frame)
                session.evaluate(spec)
                self.assertIsNotNone(session.result)
                self.assertFalse(any(issue.severity == 'error' for issue in session.issues))
                doc = spec.explain(session.normalized, session.result)
                for block in doc.blocks:
                    if block.kind == 'latex':
                        self.assertNotIn('nan', str(block.body).lower())
                        self.assertNotIn('inf', str(block.body).lower())
                plot = spec.build_plot(session.normalized, session.result)
                expected = [curve[field] for curve in session.result.values['curves'].values()
                            for field in ('f1', 'f2') if math.isfinite(curve[field])]
                labels = [a for a in plot.layout.annotations if a.xref == 'x' and a.yref == 'y']
                self.assertEqual([a.x for a in labels], expected)
                report = report_from_plotly(plot)
                try:
                    png = figure_bytes(report, 'png')
                    svg = figure_bytes(report, 'svg')
                    self.assertTrue(png.startswith(b'\x89PNG'))
                    self.assertIn(b'<svg', svg)
                    for label in labels:
                        self.assertIn(label.text.split('<br>')[1].encode(), svg)
                finally:
                    report.clear()

    def test_incomplete_scan_leaves_q4_blank_but_computes_other_q_values(self):
        for resistance in (100, 500):
            key = self.exp.scan_keys[resistance]
            self.exp.set_initial_df(self.exp.initial_df[key].iloc[12:].copy(), key)
        self.exp.fill_data()
        for resistance in (100, 500):
            self.assertTrue(math.isnan(self.exp.q[resistance][3]))
            self.assertTrue(all(math.isfinite(v) for v in self.exp.q[resistance][:3]))

    def test_missing_values_do_not_become_zero_or_bridge_a_gap(self):
        table = pd.DataFrame({FREQ: [100, 200, 300, 400, 500],
                              UR: [10, math.nan, 40, 20, 10]})
        current = scan_table(table, 100)
        self.assertTrue(math.isnan(current[CURRENT].iloc[1]))
        curve = analyze_curve(current)
        self.assertTrue(math.isnan(curve['f1']))
        self.assertTrue(math.isnan(curve['bandwidth']))

    def test_csv_roundtrip_and_validation(self):
        for key, frame in self.exp.initial_df.items():
            imported = pd.read_csv(io.StringIO(frame.to_csv(index=False)))
            self.exp.set_initial_df(imported, key)
            pd.testing.assert_frame_equal(frame, imported, check_dtype=False)
        key = self.exp.scan_keys[100]
        with self.assertRaises(ValueError):
            self.exp.set_initial_df(pd.DataFrame({'wrong': [1]}), key)
        invalid = self.exp.initial_df[key].copy()
        invalid.loc[1, FREQ] = invalid.loc[0, FREQ]
        with self.assertRaises(ValueError):
            self.exp.set_initial_df(invalid, key)

    def test_edit_recalculates_resonance_frequency(self):
        key = self.exp.scan_keys[500]
        edited = self.exp.initial_df[key].copy()
        edited.loc[edited[FREQ] == 2250, UR] = 1200
        self.exp.set_initial_df(edited, key)
        self.exp.fill_data()
        self.assertEqual(self.exp.measured_f0[500], 2250)
        self.assertAlmostEqual(self.exp.q[500][3], 2250 / self.exp.curves[500]['bandwidth'])

    def test_plot_and_required_tables(self):
        fig = self.exp.build_plot()
        self.assertEqual(len(self.exp.final_df), 4)
        self.assertEqual(len(fig.data), 2)
        self.assertEqual(len(fig.data[0].x), 30)
        self.assertIn('Hz', fig.layout.xaxis.title.text)
        self.assertIn('mA', fig.layout.yaxis.title.text)
        self.assertEqual(len(fig.layout.shapes), 6)
        vertical_lines = [s for s in fig.layout.shapes if s.x0 == s.x1]
        expected = [self.exp.curves[r][field] for r in (100, 500) for field in ('f1', 'f2')]
        self.assertEqual([s.x0 for s in vertical_lines], expected)
        for line in vertical_lines:
            self.assertEqual(line.y0, 0)
            self.assertEqual(line.line.dash, 'dash')
            tick_index = list(fig.layout.xaxis.tickvals).index(line.x0)
            self.assertIn(f'{line.x0:.2f}', fig.layout.xaxis.ticktext[tick_index])
        self.assertEqual(fig.layout.yaxis.range[0], 0)

    def test_cutoff_labels_survive_report_export(self):
        from core.plots import report_from_plotly
        fig = self.exp.build_plot()
        labels = [a for a in fig.layout.annotations if a.xref == 'x' and a.yref == 'y']
        self.assertEqual(len(labels), 4)
        for label, (resistance, field) in zip(labels, [(r, f) for r in (100, 500) for f in ('f1', 'f2')]):
            curve = self.exp.curves[resistance]
            self.assertEqual((label.x, label.y), (curve[field], curve['level']))
            self.assertIn(f'R={resistance} Ω', label.text)
            self.assertIn(f'{"f₁" if field == "f1" else "f₂"}={curve[field]:.2f} Hz', label.text)
        report = report_from_plotly(fig)
        try:
            text = '\n'.join(item.get_text() for item in report.axes[0].texts)
            for label in labels:
                self.assertIn(label.text.replace('<br>', '\n'), text)
        finally:
            report.clear()

    def test_ui_calculates_cutoffs_after_voltage_edit(self):
        eid = 'lower_02_resonance'
        at = open_app(eid)
        self.assertFalse(at.exception)
        self.assertEqual(len(at.number_input), 1)
        session = at.session_state['lab_sessions'][eid]
        self.assertAlmostEqual(session.result.values['q'][500][3], 3.762114596768661)
        key = session.result.values['scan_keys'][500]
        index = list(session.inputs.tables).index(key)
        at.session_state[f'{eid}:table:{index}:0'] = {'edited_rows': {13: {UR:1200.0}}, 'added_rows': [], 'deleted_rows': []}
        at.run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        result = at.session_state['lab_sessions'][eid].result
        self.assertEqual(result.values['measured_f0'][500], 2250)
        self.assertAlmostEqual(result.values['q'][500][3],2250/result.values['curves'][500]['bandwidth'])


if __name__ == '__main__':
    unittest.main()
