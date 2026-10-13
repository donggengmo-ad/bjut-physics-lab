"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_09_franck_hertz'
TITLE = '实验九：弗兰克-赫兹实验'
DESCRIPTION = '\n            ##### 数据说明：\n            - $V_{G2K}$：加速电压，单位 V\n            - $I_p$：板极电流，单位 $\\times 10$ nA\n            - 电压参数：$V_f = 3.75$ V，$V_p = 6.96$ V，$V_{G1} = 1.87$ V\n            ##### 注意事项：\n            - 程序自动识别 $I_p$ 的极大值（波峰）\n            - 用逐差法处理前偶数个波峰对应的 $V_{G2K}$，求出第一激发电位 $V_g$\n            - $V_{G理} = 11.55$ V\n        '
DEFAULT_DATA = {'数据表': {'V_G2K(V)': [6.0,
                      8.0,
                      10.0,
                      12.0,
                      12.6,
                      14.0,
                      16.0,
                      18.0,
                      20.0,
                      22.0,
                      24.0,
                      26.0,
                      28.0,
                      30.0,
                      32.0,
                      33.2,
                      34.0,
                      36.0,
                      38.0,
                      39.4,
                      40.0,
                      42.0,
                      44.0,
                      44.5,
                      46.0,
                      48.0,
                      50.0,
                      51.3,
                      52.0,
                      54.0,
                      56.0,
                      58.0,
                      60.0,
                      62.0,
                      62.7,
                      64.0,
                      66.0,
                      68.0,
                      69.2,
                      70.0,
                      72.0,
                      74.0,
                      75.6,
                      76.0,
                      78.0,
                      80.0,
                      81.2,
                      82.0,
                      84.0,
                      86.0,
                      88.0,
                      90.0,
                      92.0,
                      94.0,
                      96.0,
                      97.5],
         'Ip(×10nA)': [0.05,
                       0.42,
                       2.3,
                       4.7,
                       6.47,
                       8.7,
                       10.23,
                       10.9,
                       9.7,
                       7.03,
                       11.51,
                       19.5,
                       23.9,
                       19.0,
                       10.1,
                       6.8,
                       9.2,
                       20.7,
                       30.0,
                       32.2,
                       31.5,
                       19.9,
                       7.0,
                       6.6,
                       14.2,
                       28.0,
                       38.8,
                       40.3,
                       32.2,
                       22.4,
                       8.7,
                       18.0,
                       34.0,
                       46.0,
                       47.0,
                       45.0,
                       30.0,
                       15.6,
                       15.0,
                       23.4,
                       38.9,
                       50.9,
                       54.4,
                       53.6,
                       43.4,
                       27.3,
                       26.0,
                       28.4,
                       41.5,
                       56.2,
                       62.9,
                       58.7,
                       47.0,
                       41.7,
                       48.5,
                       57.6]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

KEY = '数据表'
VOLTAGE = 'V_G2K(V)'
CURRENT = 'Ip(×10nA)'


def find_peaks(voltage,current):
    indices = [i for i in range(1,len(current)-1) if current[i]>current[i-1] and current[i]>current[i+1]]
    # 保留原实验的末点候选约定，算法专业校订独立记录。
    if len(current)>=2 and current[-1]>current[-2]:
        indices.append(len(current)-1)
    return np.asarray(voltage)[indices], np.asarray(current)[indices]


def validate(inputs):
    frame=inputs.tables[KEY]
    return [ValidationIssue('电压测量点不能重复。',KEY,int(row),VOLTAGE)
            for row in frame.index[frame[VOLTAGE].notna() & frame[VOLTAGE].duplicated()]]


def compute(inputs):
    frame = inputs.tables[KEY].sort_values(VOLTAGE).reset_index(drop=True).copy()
    voltage,current = frame[VOLTAGE].to_numpy(dtype=float),frame[CURRENT].to_numpy(dtype=float)
    peaks_v,peaks_i = find_peaks(voltage,current)
    # 缺少横坐标的读数不能形成可用于逐差法的波峰。
    keep=np.isfinite(peaks_v)&np.isfinite(peaks_i)
    peaks_v,peaks_i=peaks_v[keep],peaks_i[keep]
    n_peaks=len(peaks_v)//2*2
    peaks_v,peaks_i=peaks_v[:n_peaks],peaks_i[:n_peaks]
    n=n_peaks//2
    differences=peaks_v[n:]-peaks_v[:n]
    vg=float(differences.sum())/(n*n) if n else math.nan
    error=abs(vg-11.55)/11.55*100
    peaks=pd.DataFrame({'序号':range(1,n_peaks+1),VOLTAGE:peaks_v,CURRENT:peaks_i})
    notes=[] if n else ['至少需要两个有效波峰才能用逐差法计算激发电位。']
    return ResultBundle({KEY:frame,'波峰识别结果':peaks},
        dict(peaks_v=peaks_v,peaks_i=peaks_i,n=n,differences=differences,vg=vg,error=error),notes,
        (Metric('第一激发电位',significant(vg,4),'V'),Metric('相对误差',significant(error,3),'%'),Metric('参与计算的波峰',str(n_peaks))))


def explain(inputs,result):
    r=result.values
    doc=Explanation()
    doc.markdown('**1. 波峰识别与逐差法**')
    doc.caption('取前偶数个波峰参与逐差法；波峰坐标见“结果表格”。')
    doc.latex(r'V_g=\frac1{n^2}\sum_{i=1}^n(V_{n+i}-V_i)')
    if not r['n']:
        doc.info('波峰不足，暂不能计算第一激发电位。')
        return doc
    terms=' + '.join(f'({r["peaks_v"][r["n"]+i]:.1f}-{r["peaks_v"][i]:.1f})' for i in range(r['n']))
    doc.latex(rf'V_g=\frac{{{terms}}}{{{r["n"]}^2}}={r["vg"]:.2f}\,\mathrm{{V}}')
    doc.markdown('**2. 与理论值比较**')
    doc.latex(r'E_r=\frac{|V_g-V_{g,\mathrm{理}}|}{V_{g,\mathrm{理}}}\times100\%')
    doc.latex(rf'E_r=\frac{{|{r["vg"]:.2f}-11.55|}}{{11.55}}\times100\%={r["error"]:.1f}\%')
    return doc


def build_plot(inputs,result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    frame=result.tables[KEY]
    r=result.values
    fig=Figure(figsize=(8,5.4),layout='constrained',facecolor='white')
    FigureCanvasAgg(fig)
    ax=fig.subplots()
    ax.plot(frame[VOLTAGE],frame[CURRENT],color='#0969DA',marker='o',markersize=3,linewidth=1.2,label='Measurements')
    ax.scatter(r['peaks_v'],r['peaks_i'],color='#D55E00',marker='D',s=30,zorder=3,label=f'Peaks ({2*r["n"]})')
    for v,i in zip(r['peaks_v'],r['peaks_i']):
        ax.annotate(f'{v:.1f} V',(v,i),xytext=(0,7),textcoords='offset points',ha='center',fontsize=8)
    ax.set(xlabel=r'$V_{G2K}$ / V',ylabel=r'$I_p$ / (10 nA)',title='Franck–Hertz curve',facecolor='white')
    ax.legend();ax.grid(alpha=.25)
    ax.spines[['top','right']].set_visible(False)
    return fig


def get_spec():
    frame=default_tables()[KEY]
    return ExperimentSpec(ID,TITLE,'上册',9,'识别电流曲线波峰，用逐差法计算第一激发电位。',DESCRIPTION,
        (TableSpec(KEY,KEY,frame,(ColumnSpec(VOLTAGE,minimum=0.),ColumnSpec(CURRENT,minimum=0.)),variable_rows=True),),(),
        compute,explain,validate=validate,build_plot=build_plot,plot_kind='matplotlib',
        plot_caption='蓝色为测量曲线，橙色菱形为参与逐差法的波峰；缺测处不连线。')
