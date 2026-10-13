"""独立进程运行：python scripts/benchmark_workbench.py ROOT baseline|candidate OUTPUT。"""
import json
import math
import importlib
import statistics
import sys
import time
from pathlib import Path

root=Path(sys.argv[1]).resolve()
mode=sys.argv[2]
sys.path.insert(0,str(root))
from streamlit.testing.v1 import AppTest

IDS=['upper_02_elasticity','lower_02_resonance','lower_04_diffraction_grating']
OLD_IDS=['experiments.exp02_弹性模量',*IDS[1:]]
result={'grating_fixture':'ideal d=2000 nm; 1-minute rounded angles; length=12 mm', 'mode':mode,'root':str(root),'samples':7,'clock':'perf_counter','timings':{}}
app=AppTest.from_file(str(root/'app.py'),default_timeout=60)


def measured(action):
    start=time.perf_counter();action();elapsed=time.perf_counter()-start
    if app.exception:raise RuntimeError([e.message for e in app.exception])
    if app.error:raise RuntimeError([e.value for e in app.error])
    return elapsed


grating_prepared=False


def prepare_grating():
    global grating_prepared
    if grating_prepared:return
    module=importlib.import_module('experiments.exp_lower_04_衍射光栅')
    if mode=='baseline':
        experiment=module.Experiment();frame=experiment.initial_df[experiment.input_key].copy()
    else:
        from core.session import ExperimentSession
        from experiments import get_spec
        experiment=ExperimentSession.create(get_spec(IDS[2]));frame=next(iter(experiment.inputs.tables.values())).copy()
    for row in range(1,9):
        phi=math.degrees(math.asin(frame.at[row,module.ORDER]*frame.at[row,module.WAVE]/2000))
        for column,angle in zip(module.ANGLES,(350-phi,170-phi,350+phi,170+phi)):
            degree,minute=divmod(round(angle*60)%(360*60),60)
            frame.at[row,column]=f'{degree}.{minute:02d}'
    if mode=='baseline':
        experiment.set_initial_df(frame,experiment.input_key);experiment.length_mm=12.;experiment.editor_version+=1
        app.session_state['experiment_'+IDS[2]]=experiment
    else:
        state=experiment.inputs.copy();state.tables[next(iter(state.tables))]=frame;state.parameters['length_mm']=12.
        experiment.replace(state)
        app.session_state['lab_sessions'][IDS[2]]=experiment
    grating_prepared=True


def select(index):
    if index==2:prepare_grating()
    if mode=='baseline':
        app.session_state['select_exp']=OLD_IDS[index];app.run()
    else:
        app.switch_page(f'app_pages/{IDS[index]}.py').run()


def summary(samples):
    return {'samples_s':samples,'median_s':statistics.median(samples)}

result['cold_first_request_s']=measured(app.run)
for index,eid in enumerate(IDS):
    record={}
    record['selected_view_request_s']=result['cold_first_request_s'] if index==0 else measured(lambda:select(index))
    record['repeat_view']=summary([measured(app.run) for _ in range(7)])
    widget=app.slider[0] if mode=='baseline' and index==0 else app.number_input[0]
    values=[-.018+j*.001 for j in range(7)] if index==0 else [30.+j for j in range(7)] if index==1 else [12.+j for j in range(7)]
    record['continuous_parameter_edits']=summary([measured(lambda value=value:widget.set_value(value).run()) for value in values])
    record['roundtrip_navigation']=summary([measured(lambda:(select((index+1)%3),select(index))) for _ in range(7)])
    if mode=='candidate':
        app.session_state[f'{eid}:view']='图表'
        record['first_plot_view_s']=measured(app.run)
        record['repeat_plot_view']=summary([measured(app.run) for _ in range(7)])
        session=app.session_state['lab_sessions'][eid]
        record['calculation_count']=session.calculation_count
        record['input_revision']=session.inputs.revision
        app.session_state[f'{eid}:view']='结果表格';app.run()
    else:
        record['first_plot_view_s']=None
        record['plot_note']='旧入口在每次页面运行中绘图，无法单独打开图表；图表成本包含在上述请求。'
    result['timings'][eid]=record
Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({key:{k:v.get('median_s') if isinstance(v,dict) else v for k,v in item.items()} for key,item in result['timings'].items()},ensure_ascii=False,indent=2))
