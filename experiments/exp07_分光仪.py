"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_07_spectrometer'
TITLE = '实验七：分光计的调节和使用'
DESCRIPTION = '\n            ##### 数据说明：  \n            - AB1：游标I 测出的 AB面法线 $$ \\theta $$ 角  \n            - AB2：游标II 测出的 AB面法线 $$ \\theta $$ 角  \n            - AC1：游标I 测出的 AC面法线 $$ \\theta $$ 角  \n            - AC2：游标II 测出的 AC面法线 $$ \\theta $$ 角  \n            - phi1：$$ AB1 + 360 \\degree - AC1 $$\n            - phi2：$$ AB2 - AC2 $$\n            - phi：$$ \\frac{1}{2} \\times (phi1 + phi2)  $$\n            ##### 注意事项：  \n            - 填入浮点数 x.y 表示 x度y分，例如 30.15 表示 30度15分  \n            - 注意填入顺序，数值大概是 AB1 < AC2 < AB2 < AC1，可能跟你实际测量结果顺序不一样\n            - 初始值是我当时测的，仅供参考，可能不准\n        '
DEFAULT_DATA = {'数据表': {'测量次数': [1, 2, 3, 4, 5, 6],
         'AB1': [56.12, 56.09, 56.1, 56.13, 56.12, 56.13],
         'AB2': [236.06, 236.04, 236.05, 236.08, 236.06, 236.08],
         'AC1': [296.05, 296.07, 296.06, 296.05, 296.09, 296.06],
         'AC2': [116.05, 116.08, 116.08, 116.06, 116.13, 116.08]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

from core.angles import parse_angle, angle_text
from core.numerics import finite_mean, sample_std

KEY = '数据表'
ANGLE_COLUMNS = ('AB1','AB2','AC1','AC2')


def angle_defaults():
    frame = default_tables()[KEY]
    for column in ANGLE_COLUMNS:
        frame[column] = frame[column].map(lambda v: f'{v:.2f}')
    return frame


def compute(inputs):
    frame = inputs.tables[KEY].copy()
    angles = frame[list(ANGLE_COLUMNS)].apply(lambda col: col.map(parse_angle))
    # 沿用实验中 AB1 < AC2 < AB2 < AC1 的读数方向。
    frame['phi1'] = angles['AB1'] - angles['AC1'] + 360
    frame['phi2'] = angles['AB2'] - angles['AC2']
    frame['phi'] = (frame['phi1']+frame['phi2'])/2
    mean = finite_mean(frame['phi'])
    std = sample_std(frame['phi'])
    uncertainty = math.sqrt(std**2+(1/60)**2)
    apex = 180-mean
    count = int(frame['phi'].notna().sum())
    notes = [] if count==6 else [f'有效双游标记录 {count}/6；不足两组时不能估算样本标准差。']
    return ResultBundle({KEY:frame},dict(mean=mean,apex=apex,std=std,uncertainty=uncertainty,count=count),notes,
        (Metric('棱镜顶角 A',angle_text(apex,latex=False)),Metric('角度不确定度',angle_text(uncertainty,latex=False))))


def format_tables(inputs,result):
    display = result.tables[KEY].copy()
    for column in ANGLE_COLUMNS:
        display[column] = display[column].map(lambda v: angle_text(parse_angle(v),latex=False))
    for column in ('phi1','phi2','phi'):
        display[column] = display[column].map(lambda v: angle_text(v,latex=False))
    return [DisplayTable(KEY,display)]


def explain(inputs,result):
    r = result.values
    doc = Explanation()
    doc.markdown('**1. 游标角度与棱镜顶角**')
    doc.latex(r'\phi_1=AB_1+360^\circ-AC_1,\quad\phi_2=AB_2-AC_2,\quad\phi=\frac{\phi_1+\phi_2}{2}')
    doc.latex(r'\bar\phi=\frac1n\sum_i\phi_i,\quad A=180^\circ-\bar\phi')
    if r['count']:
        terms = '+'.join(angle_text(v) for v in result.tables[KEY]['phi'].dropna())
        doc.latex(rf'\bar\phi=\frac{{{terms}}}{{{r["count"]}}}={angle_text(r["mean"])}')
        doc.latex(rf'A=180^\circ-{angle_text(r["mean"])}={angle_text(r["apex"])}')
    else:
        doc.info('每次测量需填写四个角位置，完整记录才能参与计算。')
    doc.markdown('**2. 角度不确定度**')
    doc.latex(r'S_\phi=\sqrt{\frac{\sum_i(\phi_i-\bar\phi)^2}{n-1}},\quad\Delta_\phi=\sqrt{S_\phi^2+(1^\prime)^2}')
    if math.isfinite(r['std']):
        doc.latex(rf'S_\phi={angle_text(r["std"])},\quad\Delta_\phi={angle_text(r["uncertainty"])}')
    return doc


def get_spec():
    frame = angle_defaults()
    return ExperimentSpec(ID,TITLE,'上册',7,'以双游标角位置求棱镜顶角及不确定度。',DESCRIPTION,
        (TableSpec(KEY,KEY,frame,tuple(ColumnSpec(c,'number' if c=='测量次数' else 'angle',
             help=None if c=='测量次数' else '度.分，例如 30.10 表示 30°10′。') for c in frame),('测量次数',)),),(),
        compute,explain,format_tables=format_tables)
