import io
import math
import pathlib
import unittest

import pandas as pd

from experiments.exp_lower_05_声速测量 import (
    D_PHASE, D_RESONANCE, INDEX, L_PHASE, L_RESONANCE, Experiment,
)

APP = str(pathlib.Path(__file__).resolve().parents[1] / 'app.py')

# 表 5-1 手写数据，Δlᵢ 由 l_{i+5} − lᵢ 独立复算，两列均值与记录页的 23.762 / 23.110 一致。
INTERFERENCE = [1.03, 5.80, 10.50, 15.25, 20.03, 24.74, 29.61, 34.35, 38.96, 43.76]
PHASE = [1.28, 5.89, 10.60, 15.12, 19.65, 24.29, 29.07, 33.46, 38.22, 43.05]
DELTA_INTERFERENCE = [23.71, 23.81, 23.85, 23.71, 23.73]
DELTA_PHASE = [23.01, 23.18, 22.86, 23.10, 23.40]

# 表 5-1 表头的环境参数。
FREQUENCY_KHZ = 37.1
TEMPERATURE_C = 27.7
SATURATED_1E5PA = 0.0378
HUMIDITY_PERCENT = 62.0

# 手册公式的独立复算：v = 331.45√((1+t/T0)(1+0.3192 rPₛ/P))。
THEORETICAL = 331.45 * math.sqrt(
    (1 + TEMPERATURE_C / 273.15)
    * (1 + 0.3192 * (HUMIDITY_PERCENT / 100) * SATURATED_1E5PA * 1e5 / 1.013e5)
)
WAVE_INTERFERENCE = 2 * (sum(DELTA_INTERFERENCE) / 5) / 5
WAVE_PHASE = 2 * (sum(DELTA_PHASE) / 5) / 5
SPEED_INTERFERENCE = WAVE_INTERFERENCE * FREQUENCY_KHZ
SPEED_PHASE = WAVE_PHASE * FREQUENCY_KHZ


class SoundSpeedExperiment(unittest.TestCase):
    def setUp(self):
        self.experiment = Experiment()
        self.experiment.fill_data()

    def test_difference_and_mean_match_manual_record(self):
        self.assertEqual(list(self.experiment.initial_df[self.experiment.key][L_RESONANCE]), INTERFERENCE)
        self.assertEqual(list(self.experiment.initial_df[self.experiment.key][L_PHASE]), PHASE)
        for method, expected in (('共振干涉法', DELTA_INTERFERENCE), ('相位比较法', DELTA_PHASE)):
            for actual, reference in zip(self.experiment.deltas[method], expected):
                self.assertAlmostEqual(actual, reference, places=9)
        self.assertAlmostEqual(self.experiment.means['共振干涉法'], 23.762)
        self.assertAlmostEqual(self.experiment.means['相位比较法'], 23.110)

    def test_wavelength_from_successive_difference(self):
        self.assertAlmostEqual(self.experiment.wavelengths['共振干涉法'], 9.5048, places=9)
        self.assertAlmostEqual(self.experiment.wavelengths['相位比较法'], 9.244, places=9)

    def test_theoretical_speed_follows_manual_formula(self):
        self.assertAlmostEqual(self.experiment.theoretical, THEORETICAL, places=9)
        self.assertAlmostEqual(THEORETICAL, 349.132, places=3)

    def test_measured_speed_and_relative_error(self):
        self.assertAlmostEqual(self.experiment.measured['共振干涉法'], SPEED_INTERFERENCE, places=9)
        self.assertAlmostEqual(self.experiment.measured['相位比较法'], SPEED_PHASE, places=9)
        self.assertAlmostEqual(SPEED_INTERFERENCE, 352.6281, places=4)
        self.assertAlmostEqual(SPEED_PHASE, 342.9524, places=4)
        self.assertAlmostEqual(self.experiment.errors['共振干涉法'], 1.001, places=3)
        self.assertAlmostEqual(self.experiment.errors['相位比较法'], 1.770, places=3)

    def test_result_table_mirrors_manual_layout(self):
        table = self.experiment.final_df[self.experiment.key]
        self.assertEqual(list(table.columns),
                         [INDEX, L_RESONANCE, L_PHASE, D_RESONANCE, D_PHASE])
        self.assertEqual(len(table), 11)  # 10 行测量数据 + 平均值行
        for column in (D_RESONANCE, D_PHASE):
            self.assertTrue(all(table[column].iloc[:5]))          # 前五行有逐差值
            self.assertEqual(list(table[column].iloc[5:10]), [''] * 5)  # 后五行按手册留空
        self.assertEqual(table[INDEX].iloc[10], '平均值 Δl̄')
        self.assertIn('23.762', table[D_RESONANCE].iloc[10])
        self.assertIn('23.110', table[D_PHASE].iloc[10])

    def test_missing_measurement_is_not_treated_as_zero(self):
        edited = self.experiment.initial_df[self.experiment.key].copy()
        edited.loc[9, L_PHASE] = math.nan
        self.experiment.set_initial_df(edited, self.experiment.key)
        self.experiment.fill_data()
        delta = self.experiment.deltas['相位比较法']
        self.assertTrue(math.isnan(delta[4]))
        # 均值为 4 个有效逐差值的平均，而不是把缺失项当 0 的 5 项平均。
        self.assertAlmostEqual(self.experiment.means['相位比较法'],
                               sum(DELTA_PHASE[:4]) / 4, places=9)

    def test_blank_table_leaves_results_undefined(self):
        blank = self.experiment.initial_df[self.experiment.key].copy()
        blank[[L_RESONANCE, L_PHASE]] = math.nan
        self.experiment.set_initial_df(blank, self.experiment.key)
        self.experiment.fill_data()
        for method in ('共振干涉法', '相位比较法'):
            self.assertTrue(math.isnan(self.experiment.wavelengths[method]))
            self.assertTrue(math.isnan(self.experiment.measured[method]))
            self.assertTrue(math.isnan(self.experiment.errors[method]))

    def test_edit_recalculates_wavelength_and_speed(self):
        edited = self.experiment.initial_df[self.experiment.key].copy()
        edited.loc[9, L_RESONANCE] = 44.76  # 末行加 1 mm，第五个逐差值随之加 1 mm。
        self.experiment.set_initial_df(edited, self.experiment.key)
        self.experiment.fill_data()
        self.assertAlmostEqual(self.experiment.deltas['共振干涉法'][4], 24.73, places=9)
        self.assertAlmostEqual(self.experiment.means['共振干涉法'], 23.962, places=9)
        self.assertAlmostEqual(self.experiment.wavelengths['共振干涉法'], 9.5848, places=9)
        self.assertAlmostEqual(self.experiment.measured['共振干涉法'], 9.5848 * FREQUENCY_KHZ, places=9)

    def test_csv_roundtrip_and_validation(self):
        frame = self.experiment.initial_df[self.experiment.key]
        imported = pd.read_csv(io.StringIO(frame.to_csv(index=False)))
        self.experiment.set_initial_df(imported, self.experiment.key)
        pd.testing.assert_frame_equal(frame, imported, check_dtype=False)

    def test_validation_rejects_wrong_shape(self):
        key = self.experiment.key
        frame = self.experiment.initial_df[key].copy()
        with self.assertRaises(ValueError):
            self.experiment.set_initial_df(pd.DataFrame({'wrong': [1]}), key)
        with self.assertRaises(ValueError):
            self.experiment.set_initial_df(frame.iloc[:9].copy(), key)
        renumbered = frame.copy()
        renumbered.loc[0, INDEX] = 11
        with self.assertRaises(ValueError):
            self.experiment.set_initial_df(renumbered, key)
        negative = frame.copy()
        negative.loc[0, L_RESONANCE] = -1.0
        with self.assertRaises(ValueError):
            self.experiment.set_initial_df(negative, key)

    def test_experiment_is_registered_as_lower_volume_five(self):
        self.assertEqual(self.experiment.volume, '下册')
        self.assertEqual(self.experiment.number, 5)
        self.assertEqual(self.experiment.name, '实验五：声速的测量')
        self.assertTrue(callable(getattr(self.experiment, 'plot', None)))

    def test_app_keeps_plot_section_with_a_no_plot_notice(self):
        from streamlit.testing.v1 import AppTest

        at = AppTest.from_file(APP, default_timeout=30)
        at.session_state['select_exp'] = 'lower_05_sound_speed'
        at.run()
        self.assertFalse(at.exception)
        self.assertFalse(at.error)
        headings = [element.value for element in at.subheader]
        self.assertIn('数据处理', headings)
        self.assertIn('绘图', headings)
        notices = [element.value for element in at.info]
        self.assertTrue(any('本章节无需绘图' in str(value) for value in notices),
                        f'绘图段未显示无绘图提示：{notices}')

    def test_significant_digits_follow_manual_rule(self):
        # 手册要求注意测量结果的有效位数、误差取两位有效数字。
        # 两种方法的位数必须一致：1.0% 不能退化成 1%，343.0 m/s 不能写成 343 m/s。
        from streamlit.testing.v1 import AppTest

        def page():
            import streamlit as st
            from experiments.exp_lower_05_声速测量 import Experiment

            if 'sound_speed_error' not in st.session_state:
                st.session_state.sound_speed_error = Experiment()
            exp = st.session_state.sound_speed_error
            exp.fill_data()
            exp.calculate()

        at = AppTest.from_function(page, default_timeout=10).run()
        self.assertFalse(at.exception)
        formulas = [str(element.value) for element in at.latex]

        def rendered(text):
            self.assertTrue(any(text in value for value in formulas), f'缺少 {text}')

        rendered('=1.0\\%')            # 共振干涉法相对误差，两位有效数字。
        rendered('=1.8\\%')            # 相位比较法相对误差。
        rendered('=352.6\\,\\mathrm{m/s}')
        rendered('=343.0\\,\\mathrm{m/s}')
        rendered('=0.0095048\\,\\mathrm{m}')
        rendered('=0.0092440\\,\\mathrm{m}')

    def test_ui_shows_only_manual_parameters(self):
        from streamlit.testing.v1 import AppTest

        def page():
            import streamlit as st
            from experiments.exp_lower_05_声速测量 import Experiment

            if 'sound_speed' not in st.session_state:
                st.session_state.sound_speed = Experiment()
            exp = st.session_state.sound_speed
            exp.render_inputs()
            exp.fill_data()
            exp.calculate()

        at = AppTest.from_function(page, default_timeout=10).run()
        self.assertFalse(at.exception)
        # 表头只有 f、t、Pₛ、r 四个参数，大气压是常数而不是新增输入项。
        self.assertEqual(len(at.number_input), 4)
        self.assertAlmostEqual(at.session_state.sound_speed.measured['共振干涉法'],
                               SPEED_INTERFERENCE, places=9)


if __name__ == '__main__':
    unittest.main()
