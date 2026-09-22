import io
import math
import unittest

import pandas as pd

from experiments.exp_lower_02_交流电路谐振 import (
    CURRENT, FREQ, UR, Experiment, analyze_curve, scan_table,
)


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

    def test_ui_calculates_cutoffs_after_voltage_edit(self):
        from streamlit.testing.v1 import AppTest

        def page():
            import streamlit as st
            from experiments.exp_lower_02_交流电路谐振 import Experiment

            if 'experiment' not in st.session_state:
                st.session_state.experiment = Experiment()
            exp = st.session_state.experiment
            exp.render_inputs()
            exp.fill_data()
            exp.calculate()

        at = AppTest.from_function(page, default_timeout=10).run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.number_input), 1)  # 仅 R_L 输入，无人工截止频率项。
        self.assertAlmostEqual(at.session_state.experiment.q[500][3], 3.762114596768661)
        key = at.session_state.experiment.scan_keys[500]
        at.session_state[f'lower_02_resonance_{key}_editor_0'] = {
            'edited_rows': {13: {UR: 1200.0}}, 'added_rows': [], 'deleted_rows': [],
        }
        at.run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        self.assertEqual(at.session_state.experiment.measured_f0[500], 2250)
        curve = at.session_state.experiment.curves[500]
        self.assertAlmostEqual(at.session_state.experiment.q[500][3], 2250 / curve['bandwidth'])


if __name__ == '__main__':
    unittest.main()
