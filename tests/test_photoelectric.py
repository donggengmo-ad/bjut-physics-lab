import unittest

import numpy as np
import pandas as pd

from core.files import backup_bytes, read_backup
from experiments import get_spec
from experiments.exp_lower_07_光电效应 import CURRENT, FREQUENCY, READING, STOP, STOP_TABLE, VOLTAGE, WAVELENGTH, iv_table


class PhotoelectricTest(unittest.TestCase):
    def setUp(self):
        self.spec = get_spec('lower_07_photoelectric')
        self.inputs = self.spec.initial_state(blank=True)

    def test_report_metadata_and_blank(self):
        table = self.inputs.tables[STOP_TABLE]
        self.assertEqual(table[WAVELENGTH].tolist(), [365.0, 404.7, 435.8, 546.1, 577.0])
        self.assertEqual(table[FREQUENCY].tolist(), [8.214, 7.407, 6.879, 5.490, 5.196])
        self.assertTrue(table[STOP].isna().all())
        for aperture in (4, 2):
            frame = self.inputs.tables[iv_table(aperture)]
            self.assertEqual(len(frame), 40)
            self.assertTrue(frame.isna().all().all())
        self.assertIsNone(self.spec.compute(self.inputs).values['fit'])

    def test_signed_slope_planck_error_and_no_imputation(self):
        frame = self.inputs.tables[STOP_TABLE]
        frame.loc[[0, 1, 3, 4], STOP] = [-1.62, -1.29, -.51, -.38]
        before = frame.copy()
        result = self.spec.compute(self.inputs)
        pd.testing.assert_frame_equal(frame, before)
        fit = result.values['fit']
        x = np.array([8.214, 7.407, 5.490, 5.196])
        y = np.array([-1.62, -1.29, -.51, -.38])
        a, b = np.linalg.lstsq(np.column_stack([x, np.ones_like(x)]), y, rcond=None)[0]
        h = a * 1e-14 * -1.602e-19
        self.assertAlmostEqual(fit.slope * 1e14, a)
        self.assertAlmostEqual(fit.intercept, b)
        self.assertAlmostEqual(fit.planck / 1e-34, h / 1e-34)
        self.assertAlmostEqual(fit.error_pct, abs(h / 6.626e-34 - 1) * 100)
        self.assertEqual(result.values['stop'].index.tolist(), [0, 1, 3, 4])
        frame[STOP] *= -1
        wrong_sign = self.spec.compute(self.inputs)
        self.assertLess(wrong_sign.values['fit'].planck, 0)
        self.assertTrue(any('核对截止电压' in note for note in wrong_sign.notes))

    def test_measured_defaults(self):
        inputs = self.spec.initial_state()
        self.assertEqual(inputs.parameters['distance_stop'], 400.0)
        self.assertEqual(inputs.parameters['distance_iv'], 400.0)
        self.assertEqual(inputs.tables[STOP_TABLE][STOP].tolist(), [-1.783, -1.426, -1.246, -.678, -.560])
        for aperture in (4, 2):
            self.assertEqual(inputs.parameters[f'current_unit_{aperture}'], 1e-11)
            frame = inputs.tables[iv_table(aperture)]
            self.assertEqual(frame.dropna().shape, (31, 2))
            self.assertTrue(frame.iloc[31:].isna().all().all())
        result = self.spec.compute(inputs)
        self.assertAlmostEqual(result.values['fit'].error_pct, 2.7945128394)
        u, i4, i2 = result.values['comparison']
        self.assertEqual(u, 30)
        self.assertAlmostEqual(i4 / 1e-11, 137.5)
        self.assertAlmostEqual(i2 / 1e-11, 41.3)

    def test_two_ranges_zero_gap_and_backup(self):
        self.inputs.parameters['current_unit_4'] = 1e-10
        four = self.inputs.tables[iv_table(4)]
        two = self.inputs.tables[iv_table(2)]
        four.loc[:3, [VOLTAGE, READING]] = [(-1, 0), (0, 1), (1, np.nan), (2, 3)]
        two.loc[:1, [VOLTAGE, READING]] = [(-1, 0), (2, 8)]
        restored = read_backup(self.spec, backup_bytes(self.spec, self.inputs))
        result = self.spec.compute(restored)
        curves = result.values['curves']
        self.assertEqual(curves[4].loc[0, CURRENT], 0)
        self.assertTrue(np.isnan(curves[4].loc[2, CURRENT]))
        voltage, i4, i2 = result.values['comparison']
        self.assertEqual(voltage, 2)
        self.assertAlmostEqual(i4 / 1e-10, 3)
        self.assertAlmostEqual(i2 / 1e-11, 8)
        figure = self.spec.build_plot(restored, result)
        try:
            self.assertEqual(len(figure.axes[1].lines), 2)
            self.assertTrue(np.isnan(figure.axes[1].lines[0].get_ydata()[2]))
        finally:
            figure.clear()
        restored.parameters['current_unit_2'] = None
        result = self.spec.compute(restored)
        self.assertIsNone(result.values['comparison'])
        self.assertTrue(result.values['curves'][2][CURRENT].isna().all())
