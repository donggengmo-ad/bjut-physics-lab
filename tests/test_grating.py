import io
import math
import unittest

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from experiments.exp_lower_04_衍射光栅 import (
    ANGLES, DISPERSION_THEORY, DISPERSION_MEASURED, ORDER, PHI, PHI_I, PHI_II, SPACING, WAVE,
    angle_text, diffraction_angle, parse_angle,
)
from experiment_case import ExperimentCase, open_app, select_view

def Experiment():
    return ExperimentCase('lower_04_diffraction_grating')



def minute_record(degrees):
    degrees, minutes = divmod(round(degrees * 60) % (360 * 60), 60)
    return f'{degrees}.{minutes:02d}'


def sample_experiment():
    """仅供校验：理想 d=2000 nm 的角位置量化到分，不作为默认实验数据。"""
    experiment = Experiment()
    experiment.inputs.parameters['length_mm'] = 12.0
    frame = experiment.initial_df[experiment.input_key].copy()
    for row in range(1, 9):
        phi = math.degrees(math.asin(frame.at[row, ORDER] * frame.at[row, WAVE] / 2000))
        for column, reading in zip(ANGLES, (350 - phi, 170 - phi, 350 + phi, 170 + phi)):
            frame.at[row, column] = minute_record(reading)
    experiment.set_initial_df(frame, experiment.input_key)
    return experiment


class GratingCalculations(unittest.TestCase):
    def test_registration_and_exact_book_rows(self):
        experiment = Experiment()
        self.assertEqual((experiment.volume, experiment.number), ('下册', 4))
        self.assertEqual(experiment.name, '实验四：衍射光栅及其特性')
        frame = experiment.initial_df[experiment.input_key]
        self.assertEqual(len(frame), 9)
        self.assertEqual(frame[WAVE].iloc[1:].tolist(),
                         [435.8, 546.1, 577.0, 579.0] * 2)
        expected_angles = [
            ('235°56′', '55°50′', None, None),
            ('243°25′', '63°20′', '228°28′', '48°22′'),
            ('245°15′', '65°10′', '226°30′', '46°27′'),
            ('245°49′', '65°44′', '225°56′', '45°51′'),
            ('245°53′', '65°50′', '225°53′', '45°47′'),
            ('251°05′', '71°00′', '220°45′', '40°40′'),
            ('254°54′', '74°50′', '216°47′', '36°43′'),
            ('256°00′', '76°57′', '216°32′', '35°30′'),
            ('256°10′', '76°05′', '215°30′', '35°27′'),
        ]
        self.assertEqual(list(frame[list(ANGLES)].itertuples(index=False, name=None)), expected_angles)
        self.assertEqual(experiment.inputs.parameters, {'length_mm': 30.0, 'grating_number': '1'})
        self.assertEqual(experiment.inputs.sources[experiment.input_key], '示例')
        experiment.fill_data()
        self.assertEqual(experiment.spacing_count, 8)

    def test_degree_minute_parsing_and_validation(self):
        for value in ['30.15', '30:15', '30°15′', '30度15分']:
            self.assertAlmostEqual(parse_angle(value), 30.25)
        self.assertAlmostEqual(parse_angle('30.10'), 30 + 10/60)
        self.assertAlmostEqual(parse_angle(30.1), 30 + 10/60)
        self.assertEqual(parse_angle('360.00'), 0)
        self.assertTrue(math.isnan(parse_angle(None)))
        for value in ['30.60', '-1.00', '361', '30.155', 'inf']:
            with self.assertRaises(ValueError):
                parse_angle(value)

    def test_circular_angle_and_quarter_minute(self):
        self.assertEqual(diffraction_angle(350, 10), 10)
        self.assertEqual(diffraction_angle(170, 190), 10)
        self.assertEqual(diffraction_angle(10, 350), 10)
        self.assertTrue(math.isnan(diffraction_angle(math.nan, 10)))
        self.assertEqual(angle_text(1 + 15/3600), r'1^{\circ}00^{\prime}15^{\prime\prime}')
        self.assertEqual(angle_text(10), r'10^{\circ}00^{\prime}')

    def test_spacing_dispersion_and_resolution_units(self):
        experiment = sample_experiment()
        experiment.fill_data()
        frame = experiment.final_df[experiment.input_key]
        expected_spacings = []
        for row in range(1, 9):
            left_i, left_ii, right_i, right_ii = [
                parse_angle(frame.at[row, column]) for column in ANGLES
            ]
            first = min(abs(right_i-left_i), 360-abs(right_i-left_i))/2
            second = min(abs(right_ii-left_ii), 360-abs(right_ii-left_ii))/2
            phi = (first+second)/2
            self.assertAlmostEqual(frame.at[row, PHI], phi)
            expected_spacings.append(frame.at[row, ORDER]*frame.at[row, WAVE]/math.sin(math.radians(phi)))
        mean = sum(expected_spacings)/8
        self.assertEqual(experiment.spacing_count, 8)
        self.assertAlmostEqual(experiment.mean_spacing, mean)
        self.assertLess(abs(mean/2000-1), 0.001)
        self.assertAlmostEqual(experiment.slit_count, 12*1e6/mean)
        interval = experiment.dispersion.iloc[0]
        phi_a, phi_b = frame.at[1, PHI], frame.at[2, PHI]
        self.assertAlmostEqual(interval['ψ实 / (rad/nm)'],
                               math.radians(phi_b-phi_a)/(546.1-435.8))
        theory = experiment.final_df[DISPERSION_THEORY]
        self.assertEqual(theory[ORDER].tolist(), [1, 2])
        self.assertEqual(len(theory), 2)
        self.assertAlmostEqual(theory['ψ理 / (rad/nm)'].iloc[0], 1/mean)
        self.assertAlmostEqual(theory['ψ理 / (rad/nm)'].iloc[1], 2/mean)
        measured = experiment.final_df[DISPERSION_MEASURED]
        self.assertEqual(len(measured), 6)
        self.assertNotIn('ψ理 / (rad/nm)', measured.columns)
        self.assertNotIn('k/d̄ / (rad/nm)', measured.columns)
        self.assertTrue(frame.loc[0, [PHI, SPACING]].isna().all())

    def test_partial_cursor_and_zero_order_do_not_fabricate_results(self):
        experiment = Experiment()
        frame = experiment.initial_df[experiment.input_key].copy()
        frame[list(ANGLES)] = None
        frame.loc[0, list(ANGLES)] = ['350.00', '170.00', '10.00', '190.00']
        frame.loc[1, [ANGLES[0], ANGLES[2]]] = ['350.00', '10.00']
        experiment.set_initial_df(frame, experiment.input_key)
        experiment.fill_data()
        result = experiment.final_df[experiment.input_key]
        self.assertEqual(result.at[1, PHI_I], 10)
        self.assertTrue(math.isnan(result.at[1, PHI_II]))
        self.assertTrue(math.isnan(result.at[1, SPACING]))
        self.assertTrue(math.isnan(experiment.mean_spacing))
        self.assertTrue(math.isnan(experiment.slit_count))

    def test_missing_point_leaves_curve_gap_and_no_bridged_slope(self):
        experiment = sample_experiment()
        frame = experiment.initial_df[experiment.input_key].copy()
        frame.loc[2, list(ANGLES)] = None
        experiment.set_initial_df(frame, experiment.input_key)
        experiment.fill_data()
        self.assertEqual(experiment.spacing_count, 7)
        self.assertTrue(experiment.dispersion.iloc[:2]['ψ实 / (rad/nm)'].isna().all())
        self.assertTrue(math.isfinite(experiment.dispersion.iloc[2]['ψ实 / (rad/nm)']))
        fig = experiment.build_plot()
        try:
            self.assertTrue(math.isnan(fig.axes[0].lines[0].get_ydata()[1]))
        finally:
            plt.close(fig)

    def test_csv_preserves_minutes_and_rejects_invalid_record(self):
        experiment = sample_experiment()
        frame = experiment.initial_df[experiment.input_key].copy()
        frame.at[1, ANGLES[0]] = '30.10'
        imported = pd.read_csv(io.StringIO(frame.to_csv(index=False)),
                               dtype={column: 'string' for column in ANGLES})
        experiment.set_initial_df(imported, experiment.input_key)
        self.assertEqual(experiment.initial_df[experiment.input_key].at[1, ANGLES[0]], '30.10')
        for bad_frame in [frame.iloc[:-1], frame.assign(**{WAVE: 500.0})]:
            with self.assertRaises(ValueError):
                experiment.set_initial_df(bad_frame, experiment.input_key)
        frame.at[1, ANGLES[0]] = '20.70'
        with self.assertRaises(ValueError):
            experiment.set_initial_df(frame, experiment.input_key)

    def test_zero_diffraction_angle_and_missing_length(self):
        experiment = sample_experiment()
        experiment.inputs.parameters['length_mm'] = None
        frame = experiment.initial_df[experiment.input_key].copy()
        frame.loc[1, list(ANGLES)] = ['10.00', '190.00', '10.00', '190.00']
        experiment.set_initial_df(frame, experiment.input_key)
        experiment.fill_data()
        self.assertTrue(math.isnan(experiment.final_df[experiment.input_key].at[1, SPACING]))
        self.assertTrue(math.isnan(experiment.slit_count))
        self.assertTrue(experiment.input_issues)

    def test_plot_has_two_measured_curves_and_units(self):
        experiment = sample_experiment()
        experiment.fill_data()
        fig = experiment.build_plot()
        try:
            ax = fig.axes[0]
            self.assertEqual(len(ax.lines), 2)
            self.assertEqual(list(ax.lines[0].get_xdata()), [435.8, 546.1, 577.0, 579.0])
            np.testing.assert_allclose(ax.lines[1].get_ydata(),
                                       experiment.final_df[experiment.input_key].loc[5:8, PHI])
            self.assertIn('nm', ax.get_xlabel())
            self.assertIn('°', ax.get_ylabel())
            self.assertNotEqual(ax.lines[0].get_marker(), ax.lines[1].get_marker())
            self.assertNotEqual(ax.lines[0].get_linestyle(), ax.lines[1].get_linestyle())
        finally:
            plt.close(fig)

    def test_actual_app_blank_and_filled_states(self):
        from experiments import get_spec

        eid = 'lower_04_diffraction_grating'
        app = open_app(eid)
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        default_session = app.session_state['lab_sessions'][eid]
        self.assertEqual(default_session.inputs.parameters['length_mm'], 30.0)
        self.assertEqual(default_session.inputs.parameters['grating_number'], '1')
        self.assertEqual(default_session.result.values['spacing_count'], 8)
        self.assertEqual(app.number_input[0].value, 30.0)
        self.assertEqual(app.text_input[0].value, '1')
        default_session.replace(get_spec(eid).initial_state(blank=True))
        app.run()
        self.assertEqual(len(app.table), 3)
        self.assertEqual(len(app.table[1].value), 2)
        self.assertEqual(len(app.table[2].value), 6)
        self.assertIn('577.0', app.table[0].value[r'$\lambda/\mathrm{nm}$'].tolist())
        sample = sample_experiment()
        app.session_state['lab_sessions'][eid].replace(sample.inputs)
        app.run()
        self.assertFalse(app.exception)
        self.assertTrue(app.table[0].value[r'$d_i/\mathrm{nm}$'].iloc[1] != '—')
        select_view(app,eid,'计算过程')
        formulas = '\n'.join(item.value for item in app.latex)
        self.assertIn(r'\psi_{\text{实}}', formulas)
        self.assertIn(r'\psi_{\text{理}}', formulas)
        app.number_input(key=f'{eid}:parameter:length_mm:2').set_value(12.0).run()
        self.assertFalse(app.exception)
        self.assertTrue(math.isfinite(app.session_state['lab_sessions'][eid].result.values['slit_count']))
        self.assertIn('分辨本领', '\n'.join(item.value for item in app.markdown))


if __name__ == '__main__':
    unittest.main()
