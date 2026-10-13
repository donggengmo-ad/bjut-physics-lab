"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_08_newton_rings'
TITLE = '实验八：牛顿环测透镜曲率半径'
DESCRIPTION = '\n            ##### 数据说明：  \n            - 报告册上m 对应 50 > 环的级别 > 45\n            - 报告册上n 对应20 > 环的级别 > 15\n            - 左、右：环的位置\n            - d：50 > 环的级别 > 45 时表示dm；20 > 环的级别 > 15 时表示dn\n            - dm2-dn2：$$ dm^2 - dn^2 $$ ，只在m范围内有意义\n            ##### 注意事项：  \n            - 初始值是我当时测的，仅供参考，可能不准\n        '
DEFAULT_DATA = {'数据表': {'环的级别': [50, 49, 48, 47, 46, 45, 20, 19, 18, 17, 16, 15],
         '左': [30.659,
               30.6,
               30.549,
               30.496,
               30.435,
               30.372,
               28.691,
               28.61,
               28.522,
               28.438,
               28.345,
               28.252],
         '右': [19.375,
               19.43,
               19.482,
               19.545,
               19.59,
               19.658,
               21.339,
               21.417,
               21.502,
               21.58,
               21.681,
               21.767]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

from core.numerics import finite_mean, sample_std, divide

KEY = '数据表'


def compute(inputs):
    frame = inputs.tables[KEY].copy()
    frame['d'] = frame['左']-frame['右']
    d = frame.set_index('环的级别')['d']
    differences = np.array([d.loc[level]**2-d.loc[level-30]**2 for level in range(50,44,-1)])
    frame['dm2-dn2'] = [*differences,*[math.nan]*6]
    mean = finite_mean(differences)
    radius = mean/(120*589.3e-6)
    std = sample_std(differences)
    relative = math.sqrt((.2/589.3)**2+(1/30)**2*.02+divide(std,mean)**2)*100
    uncertainty = radius*relative/100
    count = int(np.isfinite(differences).sum())
    notes = [] if count==6 else [f'有效环级配对 {count}/6；不足两对时不能估算样本标准差。']
    if math.isfinite(radius) and radius <= 0:
        notes.append('平方差平均值非正，请检查左右位置与环级配对；曲率半径暂不可用。')
        radius = uncertainty = math.nan
    return ResultBundle({KEY:frame},dict(mean=mean,radius=radius,std=std,relative=relative,uncertainty=uncertainty,count=count),notes,
        (Metric('曲率半径 R',significant(radius,3,trailing=True),'mm'),
         Metric('不确定度 ΔR',significant(uncertainty,3,trailing=True),'mm')))


def format_tables(inputs,result):
    frame = result.tables[KEY].copy()
    for column in frame.columns[1:]:
        frame[column] = frame[column].map(lambda v: f'{v:.3f}' if math.isfinite(v) else '—')
    return [DisplayTable(KEY,frame)]


def explain(inputs,result):
    r = result.values
    doc = Explanation()
    doc.markdown('**1. 逐差法计算直径平方差**')
    doc.latex(r'd_m=x_{m,\mathrm{左}}-x_{m,\mathrm{右}},\quad\overline{d_m^2-d_n^2}=\frac1N\sum_i(d_{m_i}^2-d_{n_i}^2)')
    if r['count']:
        doc.latex(rf'\overline{{d_m^2-d_n^2}}={r["mean"]:.3f}\,\mathrm{{mm^2}}')
    doc.markdown('**2. 曲率半径**')
    doc.latex(r'\bar R=\frac{\overline{d_m^2-d_n^2}}{4(m-n)\lambda}')
    if math.isfinite(r['radius']):
        doc.latex(rf'\bar R=\frac{{{r["mean"]:.6g}}}{{4\times30\times589.3\times10^{{-6}}}}\approx{latex_number(r["radius"],3,trailing=True)}\,\mathrm{{mm}}')
    else:
        doc.info('补全至少一对有效环级位置并检查平方差后计算曲率半径。')
    doc.markdown('**3. 不确定度与结果表示**')
    doc.latex(r'\Delta_{d_m^2-d_n^2}=\sqrt{\frac{\sum_i[(d_m^2-d_n^2)_i-\overline{d_m^2-d_n^2}]^2}{N-1}}')
    doc.latex(r'\frac{\Delta_R}{R}=\sqrt{\left(\frac{\Delta_\lambda}{\lambda}\right)^2+\frac{\Delta_m^2+\Delta_n^2}{(m-n)^2}+\left(\frac{\Delta_{d_m^2-d_n^2}}{\overline{d_m^2-d_n^2}}\right)^2}')
    if math.isfinite(r['uncertainty']):
        doc.latex(rf'\Delta_{{d_m^2-d_n^2}}={r["std"]:.2f}\,\mathrm{{mm^2}},\quad\frac{{\Delta_R}}{{R}}={r["relative"]:.2f}\%')
        doc.latex(rf'R=({r["radius"]:.2f}\pm{r["uncertainty"]:.2f})\,\mathrm{{mm}}')
    return doc


def get_spec():
    frame = default_tables()[KEY]
    return ExperimentSpec(ID,TITLE,'上册',8,'配对处理牛顿环直径平方差，求透镜曲率半径。',DESCRIPTION,
        (TableSpec(KEY,KEY,frame,tuple(ColumnSpec(c,format='%d' if c=='环的级别' else '%.3f') for c in frame),('环的级别',)),),(),
        compute,explain,format_tables=format_tables)
