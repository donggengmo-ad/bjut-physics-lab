import json
import math
import unittest
from unittest.mock import patch

import pandas as pd
from core.files import backup_bytes, read_backup, csv_bytes, read_csv, result_archive
from core.session import ExperimentSession
from core.validation import normalize
from experiments import EXPERIMENTS, get_spec
from experiment_case import open_app, select_view


class PublicContracts(unittest.TestCase):
    def test_all_defaults_and_blanks_are_pure_and_renderable(self):
        for entry in EXPERIMENTS:
            spec = get_spec(entry.id)
            for blank in (False, True):
                with self.subTest(experiment=entry.id, blank=blank):
                    state = spec.initial_state(blank=blank)
                    before = backup_bytes(spec,state)
                    clean, issues = normalize(spec,state)
                    self.assertFalse(issues)
                    clean_before = backup_bytes(spec, clean)
                    result = spec.compute(clean)
                    spec.explain(clean,result)
                    if spec.format_tables:
                        spec.format_tables(clean,result)
                    self.assertEqual(before,backup_bytes(spec,state))
                    self.assertEqual(clean_before,backup_bytes(spec,clean))

    def test_all_csv_and_backup_roundtrips(self):
        for entry in EXPERIMENTS:
            spec=get_spec(entry.id); state=spec.initial_state()
            restored=read_backup(spec,backup_bytes(spec,state))
            self.assertEqual(backup_bytes(spec,state),backup_bytes(spec,restored))
            for table in spec.tables:
                for index in (False,True):
                    parsed=read_csv(spec,table.id,state.tables[table.id].to_csv(index=index).encode(),state)
                    expected,_=normalize(spec,state)
                    pd.testing.assert_frame_equal(parsed,expected.tables[table.id],check_dtype=False)

    def test_revisions_invalid_drafts_and_isolated_sessions(self):
        spec=get_spec('lower_05_sound_speed'); a=ExperimentSession.create(spec);b=ExperimentSession.create(spec)
        a.evaluate(spec);result=a.result
        for _ in range(5): a.evaluate(spec)
        self.assertEqual(a.calculation_count,1)
        self.assertIs(a.result,result)
        table=spec.tables[0];column=table.columns[1].name
        bad=a.inputs.tables[table.id].copy();bad.at[0,column]=math.inf
        a.exports['results']=result_archive(result)
        a.edit_table(table.id,bad);a.evaluate(spec)
        self.assertEqual(a.status,'输入需修正');self.assertIsNone(a.result);self.assertFalse(a.exports)
        self.assertEqual(a.issues[0].row,0);self.assertEqual(a.issues[0].column,column)
        self.assertTrue(math.isfinite(b.inputs.tables[table.id].at[0,column]))
        restored=read_backup(spec,backup_bytes(spec,a.inputs))
        self.assertTrue(normalize(spec,restored)[1])
        a.replace(spec.initial_state());a.evaluate(spec)
        self.assertIsNotNone(a.result);self.assertEqual(a.calculation_count,2)

    def test_bad_backup_and_csv_do_not_mutate(self):
        spec=get_spec('lower_04_diffraction_grating');state=spec.initial_state();before=backup_bytes(spec,state)
        payload=json.loads(before)
        for mutation in ({'schema_version':99},{'experiment_id':'wrong'},{'tables':{}},{'parameters':[]}):
            with self.assertRaises(ValueError):read_backup(spec,json.dumps({**payload,**mutation}).encode())
        with self.assertRaises(ValueError):read_csv(spec,spec.tables[0].id,b'wrong\n1\n',state)
        self.assertEqual(before,backup_bytes(spec,state))

    def test_angles_and_override_survive_backup(self):
        spec=get_spec('lower_04_diffraction_grating');state=spec.initial_state()
        from experiments.exp_lower_04_衍射光栅 import ANGLES
        state.tables[spec.tables[0].id].at[1,ANGLES[0]]='30.10'
        state.parameters['length_mm']=12.
        restored=read_backup(spec,backup_bytes(spec,state))
        self.assertEqual(restored.tables[spec.tables[0].id].at[1,ANGLES[0]],'30.10')
        spec=get_spec('lower_06_millikan_oil_drop');state=spec.initial_state();state.parameters['mean_油滴一']=30.
        result=spec.compute(read_backup(spec,backup_bytes(spec,state)))
        self.assertEqual(result.values['results']['油滴一']['mean_time'],30.)

    def test_fixed_identifier_and_negative_validation(self):
        for eid in ('lower_05_sound_speed','lower_06_millikan_oil_drop'):
            spec=get_spec(eid);state=spec.initial_state();table=spec.tables[0]
            state.tables[table.id].iat[1,0]=state.tables[table.id].iat[0,0]
            self.assertTrue(normalize(spec,state)[1])

    def test_geometry_and_mass_edits_drive_elasticity(self):
        from experiments.exp02_弹性模量 import GEOMETRY
        spec=get_spec('upper_02_elasticity');state=spec.initial_state();base=spec.compute(state)
        state.tables[GEOMETRY].loc[0,'测量值']*=2
        updated=spec.compute(state)
        self.assertAlmostEqual(updated.values['elastic'],base.values['elastic']*2)
        state.tables[GEOMETRY].loc[6,'测量值']*=2
        updated=spec.compute(state)
        self.assertAlmostEqual(updated.values['force'],base.values['force']*2)
        self.assertAlmostEqual(updated.values['elastic'],base.values['elastic']*4)

    def test_torsion_equation_uses_same_k_as_results(self):
        spec=get_spec('upper_03_torsion');result=spec.compute(spec.initial_state())
        r=result.values;t=r['periods']
        expected=4*math.pi**2*r['theory']['塑料圆柱']/(t['塑料圆柱_T1(s)']**2-t['金属载物盘_T0(s)']**2)
        self.assertAlmostEqual(r['k'],expected)
        self.assertAlmostEqual(r['measured']['塑料圆柱'],r['theory']['塑料圆柱'])

    def test_flat_frank_curve_has_no_peak_and_plot_still_works(self):
        spec=get_spec('upper_09_franck_hertz');state=spec.initial_state()
        table=spec.tables[0];state.tables[table.id][table.columns[1].name]=1.
        result=spec.compute(state)
        spec.explain(state,result)
        figure=spec.build_plot(state,result);figure.clear()
        self.assertTrue(result.tables['波峰识别结果'].empty)

    def test_plotly_report_keeps_numeric_curves_and_cutoff_lines(self):
        import plotly.io as pio
        from core.plots import report_from_plotly
        from ui.charts import figure_bytes
        spec=get_spec('lower_02_resonance');state=spec.initial_state();result=spec.compute(state)
        plot=pio.from_json(pio.to_json(spec.build_plot(state,result)))
        report=report_from_plotly(plot)
        try:
            line=report.axes[0].lines[0]
            self.assertEqual(len(line.get_xdata()),30)
            self.assertAlmostEqual(line.get_ydata()[0],.65)
            self.assertEqual(len(report.axes[0].lines),8)
            self.assertTrue(figure_bytes(report,'png').startswith(b'\x89PNG'))
            self.assertIn(b'<svg',figure_bytes(report,'svg'))
        finally: report.clear()

    def test_no_matplotlib_manager_growth(self):
        import matplotlib.pyplot as plt
        count=len(plt.get_fignums())
        for eid in ('upper_09_franck_hertz','lower_04_diffraction_grating'):
            spec=get_spec(eid);state=spec.initial_state();result=spec.compute(state)
            for _ in range(12):
                fig=spec.build_plot(state,result);fig.clear()
        self.assertEqual(len(plt.get_fignums()),count)


class WorkbenchEntry(unittest.TestCase):
    def test_all_pages_views_default_and_blank(self):
        for entry in EXPERIMENTS:
            with self.subTest(experiment=entry.id):
                app=open_app(entry.id)
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                for view in ('计算过程','实验说明','结果表格'):
                    select_view(app,entry.id,view)
                    self.assertFalse(app.exception)
                count=app.session_state['lab_sessions'][entry.id].calculation_count
                self.assertEqual(count,1)
                app.session_state['lab_sessions'][entry.id].replace(get_spec(entry.id).initial_state(blank=True))
                app.run()
                self.assertFalse(app.exception);self.assertFalse(app.error)
                self.assertEqual(app.session_state['lab_sessions'][entry.id].status,'未填写')

    def test_navigation_keeps_parameter_table_and_view(self):
        eid='upper_02_elasticity';app=open_app(eid)
        app.number_input[0].set_value(-.025).run()
        app.session_state[f'{eid}:table:1:0']={'edited_rows':{0:{'测量值':804.}},'added_rows':[],'deleted_rows':[]}
        app.run();select_view(app,eid,'计算过程')
        expected=app.session_state['lab_sessions'][eid].result.values['elastic']
        app.switch_page('app_pages/lower_02_resonance.py').run()
        app.switch_page(f'app_pages/{eid}.py').run()
        self.assertFalse(app.exception)
        session=app.session_state['lab_sessions'][eid]
        self.assertEqual(session.inputs.parameters['d0'],-.025)
        self.assertEqual(session.inputs.tables['RLb'].at[0,'测量值'],804.)
        self.assertEqual(session.result.values['elastic'],expected)
        self.assertEqual(session.active_view,'计算过程')

    def test_inactive_plots_are_not_built_and_download_ignores_rerun(self):
        eid='upper_02_elasticity'
        with patch('ui.charts.render_chart') as render:
            app=open_app(eid);select_view(app,eid,'计算过程')
            self.assertEqual(render.call_count,0)
            app.button(key=f'{eid}:prepare_files').click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['lab_sessions'][eid].calculation_count,1)
            self.assertTrue(all(x.proto.ignore_rerun for x in app.get('download_button')))
            select_view(app,eid,'图表');self.assertEqual(render.call_count,1)

    def test_restored_invalid_parameters_remain_editable(self):
        eid='upper_02_elasticity';app=open_app(eid)
        state=app.session_state['lab_sessions'][eid].inputs.copy()
        state.parameters['d0']='bad'
        app.session_state['lab_sessions'][eid].replace(state);app.run()
        self.assertFalse(app.exception);self.assertTrue(app.error)
        app.text_input(key=f'{eid}:parameter:d0:1').set_value('-0.02').run()
        self.assertFalse(app.exception);self.assertFalse(app.error)
        self.assertIsNotNone(app.session_state['lab_sessions'][eid].result)

    def test_plot_preparation_on_all_supported_pages(self):
        for entry in EXPERIMENTS:
            spec=get_spec(entry.id)
            if spec.build_plot is None: continue
            with self.subTest(experiment=entry.id):
                app=open_app(entry.id);select_view(app,entry.id,'图表')
                self.assertFalse(app.exception)
                app.button(key=f'{entry.id}:prepare_plot').click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state['lab_sessions'][entry.id].calculation_count,1)
                self.assertEqual(len(app.get('download_button')),2)

    def test_invalid_draft_hides_old_results(self):
        eid='lower_06_millikan_oil_drop';app=open_app(eid)
        app.session_state[f'{eid}:table:0:0']={'edited_rows':{1:{'油滴一':-1.}},'added_rows':[],'deleted_rows':[]}
        app.run()
        self.assertFalse(app.exception);self.assertTrue(app.error)
        self.assertFalse(app.table);self.assertFalse(app.metric)
        self.assertIsNone(app.session_state['lab_sessions'][eid].result)
        app.button(key=f'{eid}:prepare_files').click().run()
        self.assertEqual(len(app.get('download_button')),2)
