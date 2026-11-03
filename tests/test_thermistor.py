import io
import json
import math
from pathlib import Path
import unittest
import warnings
import zipfile

import numpy as np
import pandas as pd

from core.files import backup_bytes, read_backup, read_csv, result_archive
from core.session import ExperimentSession
from core.validation import normalize
from experiments import get_spec
from experiments.exp_lower_08_热敏电阻温度计 import (
    ID, ENV, DESIGN, CAL, SCAN, NAME, UNIT, VALUE, POINT, TEMP, CURRENT,
    bridge_current, fit_calibration, principle_diagrams, round_hundreds,
)
from experiment_case import open_app, select_view


def complete_state():
    state = get_spec(ID).initial_state()
    temperatures = np.arange(75.,24.,-5.)
    state.tables[SCAN][TEMP] = [*temperatures, 36.]
    state.tables[SCAN][CURRENT] = [*(6*temperatures-150), 66.6]
    state.tables[CAL][VALUE] = [5090., 1.88]
    return state


class ThermistorCalculations(unittest.TestCase):
    def setUp(self):
        self.spec = get_spec(ID)

    def test_photo_records_and_unfilled_cells_are_preserved(self):
        state = self.spec.initial_state()
        self.assertEqual(state.tables[ENV][VALUE].tolist(), [24,157.8,0,300,5090,800])
        self.assertEqual(state.tables[DESIGN][VALUE].tolist(), [2900,2900,5090,2.0])
        self.assertEqual(state.tables[CAL][VALUE].tolist(), [5100,2.32])
        self.assertEqual(state.tables[SCAN].loc[0,[TEMP,CURRENT]].tolist(), [75,300])
        self.assertEqual(state.tables[SCAN][TEMP].iloc[:11].tolist(),list(np.arange(75.,24.,-5.)))
        self.assertEqual(state.tables[SCAN][CURRENT].iloc[:9].tolist(),[300,290,269,235,204,161,133,95,70])
        self.assertTrue(state.tables[SCAN][CURRENT].iloc[9:11].isna().all())
        self.assertEqual(state.tables[SCAN].iloc[11][[TEMP,CURRENT]].tolist(),[32,43])
        result = self.spec.compute(state)
        self.assertEqual(result.values['fit']['n'], 9)
        self.assertTrue(result.values['palm_extrapolated'])
        self.assertAlmostEqual(result.values['fit']['slope'],6.17)
        self.assertAlmostEqual(result.values['palm_temperature'],30.328651179542582)
        self.assertEqual(result.summary[2].value,'30.3')
        self.assertEqual(result.summary[3].value,'5.2')
        self.assertEqual(state.tables[DESIGN][VALUE].iloc[3], 2.0)

    def test_default_tables_equal_authoritative_user_backup(self):
        path=Path(__file__).resolve().parents[1]/'experiments/examples/lower_08_thermistor.json'
        payload=json.loads(path.read_text())
        state=self.spec.initial_state()
        for key,table in payload['tables'].items():
            expected=pd.DataFrame(table['rows'],columns=table['columns'])
            pd.testing.assert_frame_equal(state.tables[key],expected,check_dtype=False)

    def test_default_plot_uses_one_continuous_extended_fit_line(self):
        state=self.spec.initial_state();result=self.spec.compute(state)
        figure=self.spec.build_plot(state,result)
        try:
            ax=figure.axes[0];self.assertEqual(len(ax.lines),1)
            line=ax.lines[0];fit=result.values['fit']
            self.assertLess(line.get_xdata()[0],fit['temperature_range'][0])
            self.assertAlmostEqual(line.get_xdata()[0],result.values['palm_temperature'])
            self.assertTrue(np.allclose(line.get_ydata(),fit['slope']*line.get_xdata()+fit['intercept']))
            self.assertEqual(len(ax.collections[0].get_offsets()),9)
            self.assertEqual(len(ax.collections[1].get_offsets()),1)
        finally:figure.clear()

    def test_bridge_current_matches_independent_nodal_solution(self):
        rng = np.random.default_rng(27)
        for _ in range(100):
            r1,r2,rt,rs,rg = rng.uniform(50,10000,5)
            voltage = rng.uniform(.01,5)
            matrix = [[1/r1+1/rt+1/rg,-1/rg],[-1/rg,1/r2+1/rs+1/rg]]
            a,b = np.linalg.solve(matrix,[voltage/r1,voltage/r2])
            self.assertAlmostEqual(bridge_current(r1,r2,rt,rs,rg,voltage),(b-a)/rg,places=13)
        self.assertEqual(bridge_current(2900,2900,5090,5090,157.8,2),0)
        self.assertGreater(bridge_current(2900,2900,800,5090,157.8,2),0)

    def test_design_voltage_and_dynamic_dependence(self):
        state=self.spec.initial_state();result=self.spec.compute(state)
        self.assertEqual(result.values['r_mean'],2945)
        self.assertEqual(result.values['r_selected'],2900)
        self.assertEqual(round_hundreds(12345),12300)
        self.assertEqual(round_hundreds(1250),1300)
        self.assertEqual(result.values['balance_rs'],5090)
        required=result.values['e_required']
        self.assertAlmostEqual(required,1.87647796961659)
        self.assertAlmostEqual(bridge_current(2900,2900,800,5090,157.8,required),300e-6)
        state.tables[ENV].loc[3,VALUE]=150
        self.assertAlmostEqual(self.spec.compute(state).values['e_required'],required/2)
        state.tables[DESIGN].loc[0,VALUE]=5800
        self.assertEqual(self.spec.compute(state).values['balance_rs'],2545)

    def test_linear_fit_palm_inversion_and_error_use_unrounded_values(self):
        result=self.spec.compute(complete_state());r=result.values
        self.assertEqual((r['fit']['slope'],r['fit']['intercept']), (6,-150))
        self.assertAlmostEqual(r['palm_temperature'],36.1)
        self.assertAlmostEqual(r['relative_error'],100/360)
        self.assertEqual(result.summary[2].value,'36.1')
        self.assertEqual(result.summary[3].value,'0.28')
        display=self.spec.format_tables(complete_state(),result)[-1].frame
        self.assertEqual(display['T计 / ℃'].iloc[0],'36.1')
        self.assertEqual(display['相对误差 Er / %'].iloc[0],'0.28')

    def test_noisy_fit_agrees_with_independent_regression(self):
        state=complete_state();frame=state.tables[SCAN]
        rng=np.random.default_rng(123)
        frame.loc[:10,CURRENT]+=rng.normal(0,.4,11)
        fit=self.spec.compute(state).values['fit']
        x=frame.loc[:10,TEMP].to_numpy();y=frame.loc[:10,CURRENT].to_numpy()
        slope,intercept=np.linalg.lstsq(np.column_stack([x,np.ones(len(x))]),y,rcond=None)[0]
        self.assertAlmostEqual(fit['slope'],slope)
        self.assertAlmostEqual(fit['intercept'],intercept)
        self.assertTrue(np.allclose(fit['curve_y'],slope*fit['curve_x']+intercept))

    def test_partial_pairs_duplicates_order_and_zero_current(self):
        frame=pd.DataFrame({TEMP:[75,50,50,25,math.nan,35],CURRENT:[300,150,150,0,20,math.nan]})
        before=frame.copy(deep=True);fit=fit_calibration(frame)
        self.assertEqual(fit['n'],4)
        self.assertEqual((fit['slope'],fit['intercept']),(6,-150))
        pd.testing.assert_frame_equal(before,frame)
        shuffled=fit_calibration(frame.iloc[::-1])
        self.assertEqual(shuffled['slope'],fit['slope'])

    def test_fewer_than_two_distinct_temperatures_cannot_fit(self):
        for x,y in [([],[]),([math.nan],[20]),([75],[300]),([50,50],[100,120])]:
            with self.subTest(x=x):
                fit=fit_calibration(pd.DataFrame({TEMP:x,CURRENT:y}))
                self.assertIsNotNone(fit['error'])

    def test_palm_row_is_never_used_as_a_calibration_point(self):
        state=complete_state()
        original=self.spec.compute(state).values['fit']
        self.assertEqual(original['n'],11)
        state.tables[SCAN].loc[11,[TEMP,CURRENT]]=[40,290]
        updated=self.spec.compute(state).values['fit']
        self.assertEqual((updated['n'],updated['slope'],updated['intercept']),
                         (original['n'],original['slope'],original['intercept']))
        state=self.spec.initial_state()
        state.tables[SCAN].loc[1:10,CURRENT]=math.nan
        state.tables[SCAN].loc[11,[TEMP,CURRENT]]=[35,60]
        self.assertIsNotNone(self.spec.compute(state).values['fit']['error'])

    def test_constant_current_cannot_invert_temperature(self):
        state=complete_state();state.tables[SCAN][CURRENT]=100.
        r=self.spec.compute(state).values
        self.assertEqual(r['fit']['slope'],0)
        self.assertTrue(math.isnan(r['palm_temperature']))
        self.assertIn('斜率为 0',r['palm_error'])

    def test_user_allowed_extrapolation_and_exact_endpoints(self):
        for current,extrapolated in [(-1,True),(301,True),(0,False),(300,False)]:
            with self.subTest(current=current):
                state=complete_state();state.tables[SCAN].loc[11,CURRENT]=current
                r=self.spec.compute(state).values
                self.assertTrue(math.isfinite(r['palm_temperature']))
                self.assertEqual(r['palm_extrapolated'],extrapolated)
                self.assertAlmostEqual(r['palm_temperature'],(current+150)/6)

    def test_zero_reference_temperature_keeps_temperature_but_not_error(self):
        state=complete_state();state.tables[SCAN].loc[11,TEMP]=0
        r=self.spec.compute(state).values
        self.assertAlmostEqual(r['palm_temperature'],36.1)
        self.assertTrue(math.isnan(r['relative_error']))

    def test_calibration_values_are_not_filled_from_estimates(self):
        state=complete_state();state.tables[CAL].loc[:1,VALUE]=math.nan
        r=self.spec.compute(state).values
        self.assertTrue(math.isnan(r['rs']))
        self.assertTrue(math.isnan(r['e_cal']))
        self.assertAlmostEqual(r['palm_temperature'],36.1)

    def test_negative_slope_and_out_of_range_measurements_are_not_rewritten(self):
        state=complete_state();state.tables[SCAN][CURRENT]*=-1
        before=backup_bytes(self.spec,state)
        r=self.spec.compute(state)
        self.assertLess(r.values['fit']['slope'],0)
        self.assertTrue(any('斜率为负' in note for note in r.notes))
        self.assertTrue(any('量程' in note for note in r.notes))
        self.assertEqual(before,backup_bytes(self.spec,state))

    def test_illegal_and_missing_inputs_have_different_outcomes(self):
        for key,row,value in [(ENV,1,0),(DESIGN,0,-1),(CAL,0,-1),(SCAN,0,math.inf)]:
            state=self.spec.initial_state();column= CURRENT if key==SCAN else VALUE
            state.tables[key].loc[row,column]=value
            self.assertTrue(normalize(self.spec,state)[1])
        state=self.spec.initial_state(blank=True)
        self.assertFalse(normalize(self.spec,state)[1])
        self.assertTrue(math.isnan(self.spec.compute(state).values['e_required']))

    def test_backup_csv_and_full_result_export(self):
        state=complete_state();before=backup_bytes(self.spec,state)
        restored=read_backup(self.spec,before)
        self.assertEqual(before,backup_bytes(self.spec,restored))
        for table in self.spec.tables:
            imported=read_csv(self.spec,table.id,state.tables[table.id].to_csv(index=False).encode(),state)
            pd.testing.assert_frame_equal(imported,state.tables[table.id],check_dtype=False)
        result=self.spec.compute(state)
        self.spec.explain(state,result);self.spec.format_tables(state,result)
        self.assertEqual(before,backup_bytes(self.spec,state))
        with zipfile.ZipFile(io.BytesIO(result_archive(result))) as z:
            export=pd.read_csv(io.BytesIO(z.read(z.namelist()[-1])))
        self.assertAlmostEqual(export['T计 / ℃'].iloc[0],result.values['palm_temperature'])

    def test_plot_and_principle_diagrams_are_portable_and_have_no_glyph_errors(self):
        from ui.charts import figure_bytes
        from core.fonts import report_fonts
        state=complete_state();result=self.spec.compute(state)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            figure=self.spec.build_plot(state,result)
            try:
                self.assertEqual(len(figure.axes[0].collections[0].get_offsets()),11)
                self.assertTrue(np.allclose(figure.axes[0].lines[0].get_ydata(),result.values['fit']['curve_y']))
                self.assertIn('(6)',figure.axes[0].texts[0].get_text())
                self.assertTrue(figure_bytes(figure,'png').startswith(b'\x89PNG'))
                self.assertNotIn(b'<text',figure_bytes(figure,'svg'))
            finally:figure.clear()
            for svg in principle_diagrams(tuple(report_fonts().families)):
                self.assertIn('<svg',svg);self.assertNotIn('<text',svg)
        self.assertFalse([w for w in caught if 'Glyph' in str(w.message)])

    def test_revision_invalidates_old_fit_and_export(self):
        session=ExperimentSession.create(self.spec);session.replace(complete_state());session.evaluate(self.spec)
        session.exports['plot:png']=b'old'
        table=session.inputs.tables[SCAN].copy();table.loc[0,CURRENT]=math.inf
        session.edit_table(SCAN,table);session.evaluate(self.spec)
        self.assertIsNone(session.result);self.assertFalse(session.exports)

    def test_entry_all_views_and_draft_navigation(self):
        app=open_app(ID)
        self.assertFalse(app.exception)
        for view in ('计算过程','实验说明','图表','结果表格'):
            select_view(app,ID,view);self.assertFalse(app.exception)
        session=app.session_state['lab_sessions'][ID]
        session.replace(complete_state());app.run()
        self.assertEqual(app.session_state['lab_sessions'][ID].result.summary[2].value,'36.1')
        app.switch_page('app_pages/lower_02_resonance.py').run()
        app.switch_page('app_pages/lower_08_thermistor.py').run()
        self.assertEqual(app.session_state['lab_sessions'][ID].inputs.tables[SCAN].loc[11,CURRENT],66.6)


if __name__ == '__main__':
    unittest.main()
