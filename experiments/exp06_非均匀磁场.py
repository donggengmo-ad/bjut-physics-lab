"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_06_magnetic_field'
TITLE = '实验六：非均匀磁场测量'
DESCRIPTION = '\n            ##### 数据说明：  \n            - x：距原点距离，单位cm\n            - Um：毫伏表读数，单位mV\n            - Bm测、Bm计、Er与实验报告一一对应\n            ##### 注意事项：  \n            - 表格里Er是小数，显示计算时乘以100%了，注意区分\n            - Bm测与Bm计的单位是 $10 ^ {{-5}} T$\n            - 初始数据是我当时测的，很明显有问题，不要用！！我这节课作业才得6分orz\n        '
DEFAULT_DATA = {'数据表': {'x': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
         'Um': [66.5, 65.5, 62.7, 58.5, 53.4, 47.8, 37.0, 32.3, 28.1, 24.5]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

KEY = '数据表'


def compute(inputs):
    frame = inputs.tables[KEY].copy()
    um = frame['Um'].to_numpy(dtype=float)
    x = frame['x'].to_numpy(dtype=float)
    measured = um*1e-3*5.958e-4/(6100*(11.7e-3)**2)*1e5
    theoretical = 12.57e-7*6100*.01*1e-3/(np.sqrt(2)*(.01+(x*1e-2)**2)**1.5)*1e5
    frame['Bm测'], frame['Bm计'] = measured, theoretical
    frame['Er'] = abs(measured-theoretical)/theoretical
    maximum = float(np.nanmax(measured)) if np.isfinite(measured).any() else math.nan
    return ResultBundle({KEY: frame}, summary=(Metric('最大测量磁感应强度', significant(maximum, 4), '×10⁻⁵ T'),))


def format_tables(inputs, result):
    display = result.tables[KEY].copy()
    for column in ('Bm测','Bm计'):
        display[column] = display[column].map(lambda v: f'{v:.2f}' if math.isfinite(v) else '—')
    display['Er'] = display['Er'].map(lambda v: f'{v:.3f}' if math.isfinite(v) else '—')
    return [DisplayTable(KEY,display)]


def explain(inputs, result):
    doc = Explanation()
    doc.markdown('**磁感应强度与相对误差**')
    doc.latex(r'B_{m,\mathrm{测}}=5.958\times10^{-4}\frac{U_m}{Nd_0^2}')
    doc.latex(r'B_{m,\mathrm{计}}=\frac{\mu_0N_0\bar R^2I}{\sqrt2(\bar R^2+x^2)^{3/2}}')
    doc.latex(r'E_r=\frac{|B_{m,\mathrm{测}}-B_{m,\mathrm{计}}|}{B_{m,\mathrm{计}}}\times100\%')
    valid = result.tables[KEY].dropna(subset=['Um'])
    sample = valid.loc[valid['x']==1]
    if sample.empty: sample = valid.head(1)
    if sample.empty:
        doc.info('填写毫伏表读数后显示代入过程。')
        return doc
    row = sample.iloc[0]
    doc.caption(f'以 x={row["x"]:g} cm 的记录为例；表中 Er 为小数，下式为百分数。')
    doc.latex(rf'B_{{m,\mathrm{{测}}}}=5.958\times10^{{-4}}\frac{{{row["Um"]:g}\times10^{{-3}}}}{{6100\times(11.7\times10^{{-3}})^2}}={row["Bm测"]:.2f}\times10^{{-5}}\,\mathrm{{T}}')
    doc.latex(rf'B_{{m,\mathrm{{计}}}}=\frac{{12.57\times10^{{-7}}\times6100\times0.1^2\times10^{{-3}}}}{{\sqrt2[0.1^2+({row["x"]:g}\times10^{{-2}})^2]^{{3/2}}}}={row["Bm计"]:.2f}\times10^{{-5}}\,\mathrm{{T}}')
    doc.latex(rf'E_r=\frac{{|{row["Bm测"]:.2f}-{row["Bm计"]:.2f}|}}{{{row["Bm计"]:.2f}}}\times100\%={row["Er"]*100:.1f}\%')
    return doc


def build_plot(inputs, result):
    import plotly.graph_objects as go
    frame = result.tables[KEY]
    fig = go.Figure()
    for column, dash, symbol in [('Bm测','solid','circle'),('Bm计','dash','diamond')]:
        fig.add_scatter(x=frame['x'],y=frame[column],mode='lines+markers',name=column,
                        line={'dash':dash},marker={'symbol':symbol},connectgaps=False)
    fig.update_layout(title='非均匀磁场 Bm–x 曲线',xaxis_title='位置 x / cm',yaxis_title='磁感应强度 Bm / (10⁻⁵ T)')
    return fig


def get_spec():
    frame = default_tables()[KEY]
    return ExperimentSpec(ID,TITLE,'上册',6,'由毫伏表读数计算磁感应强度，比较空间分布与理论值。',DESCRIPTION,
        (TableSpec(KEY,KEY,frame,(ColumnSpec('x'),ColumnSpec('Um',minimum=0.)),('x',)),),(),
        compute,explain,format_tables=format_tables,build_plot=build_plot)
