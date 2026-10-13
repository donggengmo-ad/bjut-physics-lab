import math
import unittest

import numpy as np
import pandas as pd

from experiments.exp_lower_06_密立根油滴 import (
    CHARGE_COEFFICIENT,
    CORRECTION_COEFFICIENT,
    DROPS,
    MEASUREMENT,
    TIME_ROWS,
    calculate_drop,
    latex_number,
)
from experiment_case import ExperimentCase, open_app, select_view

def Experiment():
    return ExperimentCase('lower_06_millikan_oil_drop')



class MillikanCalculations(unittest.TestCase):
    def test_experiment_is_registered_as_lower_volume_six(self):
        experiment = Experiment()
        self.assertEqual(experiment.volume, '下册')
        self.assertEqual(experiment.number, 6)
        self.assertEqual(experiment.name, '实验六：密立根油滴实验')

    def test_book_parameter_simplification(self):
        self.assertAlmostEqual(CHARGE_COEFFICIENT, 9.2726891439376e-15)
        self.assertAlmostEqual(CORRECTION_COEFFICIENT, 0.02266168946266495)

    def test_supplied_raw_data_are_defaults(self):
        frame = Experiment().initial_df['表 6-1：密立根油滴法的实验数据记录']
        self.assertEqual(list(frame[MEASUREMENT]), ['U / V', *TIME_ROWS])
        self.assertEqual(frame['油滴一'].tolist(), [102, 30.9, 29.4, 29.47, 29.09, 28.73])
        self.assertEqual(frame['油滴二'].tolist(), [290, 11.18, 11.19, 11.03, 11.28, 11.05])
        self.assertEqual(frame['油滴三'].tolist(), [160, 11.71, 11.69, 11.93, 11.72, 11.75])

    def test_average_charge_reverse_verification_and_error(self):
        result = calculate_drop(200, [9.8, 10.0, 10.2, 9.9, 10.1])
        self.assertAlmostEqual(result['mean_time'], 10.0)
        self.assertAlmostEqual(result['radius'], 1.1334235305506007e-06)
        self.assertAlmostEqual(result['charge'], 1.321565282261138e-18)
        self.assertAlmostEqual(result['n_calculated'], 8.249471175163158)
        self.assertEqual(result['n_integer'], 8)
        self.assertAlmostEqual(result['measured_e'], result['charge'] / 8)
        expected_error = abs(result['charge'] / 8 - 1.602e-19) / 1.602e-19 * 100
        self.assertAlmostEqual(result['relative_error'], expected_error)

    def test_missing_voltage_still_calculates_average(self):
        result = calculate_drop(np.nan, [1, 2, np.nan, 3, np.nan])
        self.assertEqual(result['mean_time'], 2)
        self.assertTrue(math.isnan(result['charge']))
        self.assertTrue(math.isnan(result['measured_e']))

    def test_direct_average_override_recalculates_all_results(self):
        experiment = Experiment()
        experiment.inputs.parameters['mean_油滴一'] = 30.0
        experiment.fill_data()
        expected = calculate_drop(102, [30.0])
        actual = experiment.results['油滴一']
        self.assertEqual(actual['mean_time'], 30.0)
        self.assertAlmostEqual(actual['charge'], expected['charge'])
        self.assertEqual(actual['n_integer'], expected['n_integer'])
        self.assertAlmostEqual(actual['measured_e'], expected['measured_e'])
        self.assertAlmostEqual(actual['relative_error'], expected['relative_error'])
        self.assertAlmostEqual(experiment.automatic_means['油滴一'], 29.518)
        table_61 = experiment.final_df['表 6-1：密立根油滴法的实验数据记录']
        self.assertEqual(table_61.iloc[-1]['油滴一'], 30.0)

    def test_invalid_measurements_are_rejected(self):
        with self.assertRaises(ValueError):
            calculate_drop(100, [1, 0, 2])
        with self.assertRaises(ValueError):
            calculate_drop(-1, [1, 2])
        with self.assertRaises(ValueError):
            calculate_drop(math.inf, [1, 2])

    def test_required_tables_and_columns(self):
        experiment = Experiment()
        frame = experiment.initial_df[experiment.input_key].copy()
        frame.loc[0, list(DROPS)] = [200, 210, 220]
        for row in range(1, 6):
            frame.loc[row, list(DROPS)] = [10 + row / 10, 11 + row / 10, 12 + row / 10]
        experiment.set_initial_df(frame, experiment.input_key)
        experiment.fill_data()

        self.assertEqual(list(experiment.final_df), [
            '表 6-1：密立根油滴法的实验数据记录',
            '表 6-2：“倒过来验证”电荷量数据',
        ])
        table_61 = experiment.final_df['表 6-1：密立根油滴法的实验数据记录']
        self.assertEqual(table_61.iloc[-1][MEASUREMENT], '平均下降时间 / s')
        table_62 = experiment.final_df['表 6-2：“倒过来验证”电荷量数据']
        self.assertEqual(list(table_62.columns), [
            '油滴', 'Uᵢ / V', '平均 t̄gᵢ / s', 'qᵢ / C',
            'n计算ᵢ = qᵢ/e标', 'n整数ᵢ', 'e测ᵢ = qᵢ/n整数ᵢ / C',
        ])
        self.assertTrue(table_62['qᵢ / C'].notna().all())

    def test_csv_shape_and_finite_validation(self):
        experiment = Experiment()
        frame = experiment.initial_df[experiment.input_key].copy()
        bad_columns = frame.rename(columns={DROPS[0]: '错误列'})
        with self.assertRaises(ValueError):
            experiment.set_initial_df(bad_columns, experiment.input_key)
        bad_value = frame.copy()
        bad_value.loc[1, DROPS[0]] = math.inf
        with self.assertRaises(ValueError):
            experiment.set_initial_df(bad_value, experiment.input_key)

    def test_blank_ui_renders_required_content(self):
        eid = 'lower_06_millikan_oil_drop'
        app = open_app(eid)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(len(app.dataframe), 1)
        self.assertEqual(len(app.table), 2)
        self.assertIn(r'$U_i/\mathrm{V}$', app.table[1].value.columns)
        self.assertIn(r'\times10^{-19}', app.table[1].value.iloc[0][r'$q_i/\mathrm{C}$'])
        self.assertEqual(app.table[0].value.iloc[-1]['油滴一'], '$29.5$')
        self.assertEqual(app.table[0].value.iloc[-1]['油滴二'], '$11.15$')
        self.assertEqual(app.table[0].value.iloc[-1]['油滴三'], '$11.76$')
        self.assertEqual(app.table[1].value.iloc[1][r'$q_i/\mathrm{C}$'], r'$7.70\times10^{-19}$')
        self.assertEqual(latex_number(1e-19), r'1.00\times10^{-19}')
        self.assertEqual(latex_number(1,digits=2), '1.0')
        select_view(app,eid,'计算过程')
        session = app.session_state['lab_sessions'][eid]
        self.assertAlmostEqual(session.result.values['results']['油滴一']['mean_time'],29.518)
        self.assertAlmostEqual(session.result.values['results']['油滴二']['mean_time'],11.146)
        formulas = [element.value for element in app.latex]
        self.assertTrue(any(r'q_i=\frac{9.27' in formula for formula in formulas))
        self.assertTrue(all(formula.count('$$')==2 for formula in formulas))
        self.assertFalse(any('e-19' in formula or 'e-07' in formula for formula in formulas))
        self.assertTrue(any(r'\approx0.91\%' in formula for formula in formulas))
        self.assertTrue(any(r'\approx3.8\%' in formula for formula in formulas))
        self.assertEqual(len(app.number_input), 3)
        app.number_input(key=f'{eid}:parameter:mean_油滴一:0').set_value(30.0).run()
        self.assertEqual(app.session_state['lab_sessions'][eid].result.values['results']['油滴一']['mean_time'],30.0)
        app.number_input(key=f'{eid}:parameter:mean_油滴一:0').set_value(None).run()
        self.assertAlmostEqual(app.session_state['lab_sessions'][eid].result.values['results']['油滴一']['mean_time'],29.518)
        select_view(app,eid,'实验说明')
        text = '\n'.join(element.value for element in app.markdown)
        self.assertIn('分析与讨论',text)
        self.assertIn(r'\rho=981',text)
        self.assertIn(r'\eta=1.83',text)


if __name__ == '__main__':
    unittest.main()
