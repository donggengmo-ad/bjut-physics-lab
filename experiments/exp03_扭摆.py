"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_03_torsion'
TITLE = '实验三：扭摆法测转动惯量'
DESCRIPTION = '\n            ##### 数据说明：  \n            原表较复杂，拆成了几个分表\n            - 质量表，单位kg\n            - 几何尺寸：测量值和平均值，单位mm\n            - 周期：测量值和平均值，单位s\n            ##### 注意事项：  \n            - 金属载物盘不算理论转动惯量\n            - 结果比较小，都用科学计数表示了，如$1.6e−03 = 1.6^{-3}$\n            - 取 $I_{4\\text{支}} = 2.32 \\times 10^{-5} kg \\cdot m^2$\n        '
DEFAULT_DATA = {'质量表': {'物体': ['金属载物盘', '塑料圆柱', '金属圆筒', '金属细杆'], '质量(kg)': [math.nan, 0.71571, 0.70045, 0.13141]},
 '几何尺寸测量值': {'测量次数': [1, 2, 3],
             '塑料圆柱_D1(mm)': [100.26, 100.26, 100.28],
             '金属圆筒_Do(mm)': [99.94, 100.0, 99.98],
             '金属圆筒_Di(mm)': [93.98, 94.04, 94.0],
             '金属细杆_l(mm)': [610.0, 610.0, 610.0]},
 '周期测量值': {'测量次数': [1, 2, 3],
           '金属载物盘_T0(s)': [0.751, 0.749, 0.751],
           '塑料圆柱_T1(s)': [1.253, 1.254, 1.252],
           '金属圆筒_T2(s)': [1.552, 1.553, 1.55],
           '金属细杆_T4(s)': [2.145, 2.145, 2.145]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

from core.numerics import divide

MASS, GEOMETRY, PERIOD = tuple(DEFAULT_DATA)
I4_SUPPORT = 2.32e-5


def validate(inputs):
    frame = inputs.tables[PERIOD]
    mean = frame.drop(columns='测量次数').mean()
    if pd.notna(mean['塑料圆柱_T1(s)']) and pd.notna(mean['金属载物盘_T0(s)']) and mean['塑料圆柱_T1(s)'] <= mean['金属载物盘_T0(s)']:
        return [ValidationIssue('塑料圆柱的平均周期 T₁ 应大于空载平均周期 T₀。', PERIOD)]
    geometry = inputs.tables[GEOMETRY].mean(numeric_only=True)
    if geometry['金属圆筒_Di(mm)'] >= geometry['金属圆筒_Do(mm)']:
        return [ValidationIssue('金属圆筒的内径应小于外径。', GEOMETRY)]
    return []


def compute(inputs):
    mass = inputs.tables[MASS].set_index('物体')['质量(kg)']
    geometry = inputs.tables[GEOMETRY].drop(columns='测量次数').mean()
    periods = inputs.tables[PERIOD].drop(columns='测量次数').mean()
    d1, do, di, length = geometry.to_numpy(dtype=float) / 1000
    t0, t1, t2, t4 = periods.to_numpy(dtype=float)
    theory = {'塑料圆柱': .125*mass['塑料圆柱']*d1**2,
              '金属圆筒': .125*mass['金属圆筒']*(do**2+di**2),
              '金属细杆': mass['金属细杆']*length**2/12}
    denom = t1**2-t0**2
    # T=2π√(I/K)：统一表格与代入过程，消除原来的 π/π² 不一致。
    k = divide(4*math.pi**2*theory['塑料圆柱'], denom)
    i0 = divide(theory['塑料圆柱']*t0**2, denom)
    measured = {'金属载物盘': i0, '塑料圆柱': k*t1**2/(4*math.pi**2)-i0,
                '金属圆筒': k*t2**2/(4*math.pi**2)-i0,
                '金属细杆': k*t4**2/(4*math.pi**2)-I4_SUPPORT}
    frame = pd.DataFrame({'I理论值(kg*m^2)': pd.Series(theory), 'I实验值(kg*m^2)': pd.Series(measured)})
    frame.index.name = '物体'
    frame['Er(%)'] = abs(frame['I实验值(kg*m^2)']-frame['I理论值(kg*m^2)'])/frame['I理论值(kg*m^2)']*100
    tables = {MASS: inputs.tables[MASS].copy(), GEOMETRY: inputs.tables[GEOMETRY].copy(),
              '几何尺寸平均值': geometry.rename_axis('测量量').to_frame('平均值'),
              PERIOD: inputs.tables[PERIOD].copy(), '周期平均值': periods.rename_axis('测量量').to_frame('平均值'),
              '转动惯量结果': frame}
    return ResultBundle(tables, dict(k=k, i0=i0, theory=theory, measured=measured,
            geometry=geometry, periods=periods, mass=mass),
            summary=(Metric('扭转常数 K', significant(k, 5), 'N·m/rad'), Metric('载物盘转动惯量', significant(i0, 5), 'kg·m²')))


def explain(inputs, result):
    r = result.values
    doc = Explanation()
    doc.markdown('**1. 扭转常数与载物盘转动惯量**')
    doc.latex(r'I_{\mathrm{塑料,理}}=\frac18mD_1^2,\quad K=\frac{4\pi^2I_{\mathrm{塑料,理}}}{T_1^2-T_0^2},\quad I_0=\frac{I_{\mathrm{塑料,理}}T_0^2}{T_1^2-T_0^2}')
    if math.isfinite(r['k']):
        t = r['periods']
        doc.latex(rf'K=\frac{{4\pi^2\times{latex_number(r["theory"]["塑料圆柱"],6)}}}{{{t["塑料圆柱_T1(s)"]:.6f}^2-{t["金属载物盘_T0(s)"]:.6f}^2}}={latex_number(r["k"],6)}')
        doc.latex(rf'I_0={latex_number(r["i0"],6)}\,\mathrm{{kg\cdot m^2}}')
    else:
        doc.info('填写塑料圆柱质量、直径和两组基准周期后计算扭转常数。')
    doc.markdown('**2. 理论值、实验值与相对误差**')
    doc.latex(r'I_{\mathrm{圆筒,理}}=\frac18m(D_o^2+D_i^2),\quad I_{\mathrm{细杆,理}}=\frac1{12}ml^2')
    doc.latex(r'I_{\mathrm{实}}=\frac{KT^2}{4\pi^2}-I_0,\quad E_r=\frac{|I_{\mathrm{实}}-I_{\mathrm{理}}|}{I_{\mathrm{理}}}\times100\%')
    doc.caption('细杆沿用原实验的支架修正 I₄ = 2.32×10⁻⁵ kg·m²；载物盘不计算理论值和相对误差。')
    for name, row in result.tables['转动惯量结果'].iterrows():
        doc.markdown(f'**{name}**')
        if math.isfinite(row['I实验值(kg*m^2)']):
            doc.latex(rf'I_{{\mathrm{{实}}}}={latex_number(row["I实验值(kg*m^2)"],6)}\,\mathrm{{kg\cdot m^2}}')
        if math.isfinite(row['I理论值(kg*m^2)']):
            doc.latex(rf'I_{{\mathrm{{理}}}}={latex_number(row["I理论值(kg*m^2)"],6)}\,\mathrm{{kg\cdot m^2}}')
        if math.isfinite(row['Er(%)']):
            doc.latex(rf'E_r={row["Er(%)"]:.2f}\%')
    return doc


def get_spec():
    tables = default_tables()
    return ExperimentSpec(ID, TITLE, '上册', 3, '整理质量、几何尺寸和周期，比较转动惯量与相对误差。', DESCRIPTION,
        tuple(TableSpec(key,key,frame,tuple(ColumnSpec(c, 'text' if c=='物体' else 'number', positive=c not in ('物体','测量次数')) for c in frame),
              ('物体',) if key==MASS else ('测量次数',), optional_cells=((0,'质量(kg)'),) if key==MASS else ()) for key,frame in tables.items()),
        (), compute, explain, validate=validate)
