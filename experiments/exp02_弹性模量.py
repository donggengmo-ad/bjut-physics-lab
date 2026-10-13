"""实验定义、纯计算及展示内容；无 Streamlit 状态。"""

import math
import numpy as np
import pandas as pd

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

ID = 'upper_02_elasticity'
TITLE = '实验二：金属弹性模量测量'
DESCRIPTION = '\n            ##### 数据说明：  \n            - di - d0：金属丝直径，单位mm\n            - d0：螺旋测微器零度值，单位mm\n            - R、L、b：单位mm\n            - m：单个砝码质量，单位g（dm是百分比）\n            - ni、ni#：望远镜标尺读数，单位cm\n            ##### 注意事项：  \n            - 逐差值是$$n_{i+5} - n_i$$，仅前五行有\n            - 最近比较忙，没有做代入数据的具体过程，只把结果写出来了（投降\n        '
DEFAULT_DATA = {'金属丝直径': {'测量次数': [1, 2, 3, 4, 5, 6], 'di': [0.771, 0.771, 0.769, 0.77, 0.77, 0.771]},
 'RLb': {'测量量': ['L', 'dL', 'R', 'dR', 'b', 'db', 'm', 'dm'],
         '测量值': [402.0, 5.0, 1030.0, 20.0, 40.0, 0.5, 1000.0, 0.03]},
 '望远镜标尺读数': {'测量次数': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
             '砝码质量': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
             'ni': [3.65, 4.15, 4.55, 5.05, 5.45, 5.85, 6.35, 6.85, 7.2, 7.65],
             'ni#': [3.7, 4.15, 4.6, 5.1, 5.55, 6.0, 6.45, 6.9, 7.4, 7.85]}}


def default_tables():
    return {key: pd.DataFrame(values) for key, values in DEFAULT_DATA.items()}

from core.numerics import finite_mean, sample_std, divide

WIRE, GEOMETRY, READINGS = tuple(DEFAULT_DATA)


def validate(inputs):
    issues = []
    geometry = inputs.tables[GEOMETRY].set_index('测量量')['测量值']
    for row, (label, value) in enumerate(geometry.items()):
        if pd.notna(value) and (value < 0 or label in ('L', 'R', 'b', 'm') and value == 0):
            issues.append(ValidationIssue('长度和质量应为正数，不确定度应非负。', GEOMETRY, row, '测量值'))
    corrected = inputs.tables[WIRE]['di'] - inputs.parameters['d0']
    for row in corrected.index[corrected.notna() & (corrected <= 0)]:
        issues.append(ValidationIssue('扣除零点后的直径应大于 0。', WIRE, int(row), 'di'))
    readings = inputs.tables[READINGS]
    avg = (readings['ni'] + readings['ni#']) / 2
    difference = avg.iloc[5:].to_numpy() - avg.iloc[:5].to_numpy()
    if math.isfinite(finite_mean(difference)) and finite_mean(difference) <= 0:
        issues.append(ValidationIssue('平均逐差值应大于 0，请检查标尺读数顺序。', READINGS))
    return issues


def compute(inputs):
    wire = inputs.tables[WIRE].copy()
    wire['di-d0'] = wire['di'] - inputs.parameters['d0']
    readings = inputs.tables[READINGS].copy()
    readings['平均ni'] = (readings['ni'] + readings['ni#']) / 2
    differences = readings['平均ni'].iloc[5:].to_numpy() - readings['平均ni'].iloc[:5].to_numpy()
    readings['逐差值'] = [*differences, *[math.nan] * 5]
    geometry = inputs.tables[GEOMETRY].copy()
    g = geometry.set_index('测量量')['测量值']
    d_mean = finite_mean(wire['di-d0'])
    difference_mean = finite_mean(differences)
    delta_n = difference_mean / 5
    force = g['m'] / 1000 * 9.8
    # 保留原计算的 π 近似；本轮只统一数据流，不进行模型常量校订。
    elastic = divide(16 * force * (g['R'] * 1e-3) * (g['L'] * 1e-3),
                     3.141 * (g['b'] * 1e-3) * (d_mean * 1e-3) ** 2 * delta_n * 1e-2)
    sd = sample_std(wire['di-d0'])
    dd = math.sqrt(sd**2 + .004**2)
    sn = sample_std(differences)
    dn = math.sqrt(sn**2 + .03**2)
    relative = math.sqrt(divide(g['dL'], g['L'])**2 + divide(g['dR'], g['R'])**2
                         + divide(g['db'], g['b'])**2 + 4 * divide(dd, d_mean)**2
                         + divide(dn / 5, delta_n)**2 + divide(g['dm'], g['m'] * 1e-3)**2)
    error = elastic * relative
    valid_pairs = int(np.isfinite(differences).sum())
    notes = [] if valid_pairs == 5 else [f'有效逐差记录 {valid_pairs}/5；只使用完整的前后测量对。']
    from scipy.stats import linregress
    valid = readings['砝码质量'].notna() & readings['ni'].notna()
    fit = linregress(readings.loc[valid, '砝码质量'], readings.loc[valid, 'ni']) if valid.sum() >= 2 and readings.loc[valid, '砝码质量'].nunique() >= 2 else None
    fit_parameters = (fit.slope, fit.intercept) if fit is not None else None
    values = dict(fit=fit_parameters, d_mean=d_mean, difference_mean=difference_mean, delta_n=delta_n,
                  force=force, elastic=elastic, sd=sd, dd=dd, sn=sn, dn=dn, relative=relative, error=error)
    return ResultBundle({WIRE: wire, GEOMETRY: geometry, READINGS: readings}, values, notes,
                        (Metric('弹性模量 E', significant(elastic / 1e11, 3), '×10¹¹ Pa'),
                         Metric('不确定度 ΔE', significant(error / 1e11, 3), '×10¹¹ Pa'),
                         Metric('有效逐差记录', f'{valid_pairs}/5')))


def explain(inputs, result):
    r = result.values
    g = inputs.tables[GEOMETRY].set_index('测量量')['测量值']
    doc = Explanation()
    doc.markdown('**1. 平均值与弹性模量**')
    doc.latex(r'\bar d=\frac1n\sum_i(d_i-d_0),\quad\overline{\Delta n}=\frac1N\sum_i(n_{i+5}-n_i),\quad\delta_n=\frac{\overline{\Delta n}}5')
    doc.latex(r'\bar E=\frac{16FRL}{\pi b\bar d^2\delta_n}')
    doc.caption('毫米、厘米和克在计算时换算为 SI 单位；表格显示精度不用于后续计算。')
    if math.isfinite(r['elastic']):
        doc.latex(rf'\bar d={r["d_mean"]:.3f}\,\mathrm{{mm}},\quad\overline{{\Delta n}}={r["difference_mean"]:.2f}\,\mathrm{{cm}},\quad\delta_n={r["delta_n"]:.3f}\,\mathrm{{cm}}')
        doc.latex(rf'F={g["m"]:g}\times10^{{-3}}\times9.8={r["force"]:g}\,\mathrm{{N}}')
        doc.latex(rf'\bar E=\frac{{16\times{r["force"]:g}\times({g["R"]:g}\times10^{{-3}})\times({g["L"]:g}\times10^{{-3}})}}{{3.141\times({g["b"]:g}\times10^{{-3}})\times({r["d_mean"]:.6g}\times10^{{-3}})^2\times({r["delta_n"]:.6g}\times10^{{-2}})}}\approx{r["elastic"]/1e11:.2f}\times10^{{11}}\,\mathrm{{Pa}}')
    else:
        doc.info('补全长度、质量、直径及至少一对标尺读数后计算弹性模量。')
    doc.markdown('**2. 直接测量量的不确定度**')
    doc.latex(r'S_d=\sqrt{\frac{\sum_i(d_i-\bar d)^2}{n-1}},\quad\Delta_d=\sqrt{S_d^2+\Delta_{\mathrm{仪},d}^2}')
    doc.latex(r'S_{\Delta n}=\sqrt{\frac{\sum_i(\Delta n_i-\overline{\Delta n})^2}{N-1}},\quad\Delta_{\Delta n}=\sqrt{S_{\Delta n}^2+\Delta_{\mathrm{仪},n}^2}')
    if math.isfinite(r['sd']):
        doc.latex(rf'S_d={r["sd"]:.6f}\,\mathrm{{mm}},\quad\Delta_d={r["dd"]:.6f}\,\mathrm{{mm}}')
    if math.isfinite(r['sn']):
        doc.latex(rf'S_{{\Delta n}}={r["sn"]:.4f}\,\mathrm{{cm}},\quad\Delta_{{\Delta n}}={r["dn"]:.4f}\,\mathrm{{cm}}')
    doc.markdown('**3. 间接测量量的不确定度与结果**')
    doc.latex(r'\frac{\Delta_E}{E}=\sqrt{\left(\frac{\Delta_L}{L}\right)^2+\left(\frac{\Delta_R}{R}\right)^2+\left(\frac{\Delta_b}{b}\right)^2+4\left(\frac{\Delta_d}{\bar d}\right)^2+\left(\frac{\Delta_{\delta_n}}{\delta_n}\right)^2+\left(\frac{\Delta_m}{m}\right)^2}')
    if math.isfinite(r['error']):
        doc.latex(rf'\frac{{\Delta_E}}{{E}}={r["relative"]:.6f},\quad\Delta_E={r["error"]/1e11:.4f}\times10^{{11}}\,\mathrm{{Pa}}')
        doc.latex(rf'E=({r["elastic"]/1e11:.2f}\pm{r["error"]/1e11:.4f})\times10^{{11}}\,\mathrm{{Pa}}')
    else:
        doc.info('不确定度需要至少两次有效直径测量、两组有效逐差值及完整仪器参数。')
    return doc


def build_plot(inputs, result):
    import plotly.graph_objects as go
    frame = result.tables[READINGS]
    x, y = frame['砝码质量'], frame['ni']
    fig = go.Figure(go.Scatter(x=x, y=y, mode='markers', name='测量值'))
    if result.values['fit'] is not None:
        slope, intercept = result.values['fit']
        fig.add_scatter(x=x, y=slope*x+intercept, mode='lines', name='线性拟合')
        fig.add_annotation(x=.5, y=.95, xref='paper', yref='paper',
                           text=f'y={slope:.3f}x+{intercept:.3f}', showarrow=False)
    fig.update_layout(title='望远镜读数与砝码质量关系', xaxis_title='砝码质量 / kg', yaxis_title='ni / cm')
    return fig


def format_tables(inputs, result):
    tables = []
    for title, frame in result.tables.items():
        display = frame.copy()
        for column in display:
            if pd.api.types.is_numeric_dtype(display[column]):
                digits = 3 if title == WIRE and column != '测量次数' else 2 if title == READINGS and column != '测量次数' else None
                display[column] = display[column].map(lambda value: '—' if pd.isna(value) else f'{value:.{digits}f}' if digits else f'{value:g}')
        tables.append(DisplayTable(title, display))
    return tables


def get_spec():
    tables = default_tables()
    static = {WIRE: ('测量次数',), GEOMETRY: ('测量量',), READINGS: ('测量次数',)}
    return ExperimentSpec(ID, TITLE, '上册', 2, '整理直径与标尺读数，计算弹性模量及不确定度。', DESCRIPTION,
        tuple(TableSpec(key, key, frame, tuple(ColumnSpec(c, 'text' if c=='测量量' else 'number',
              format='%.3f' if key==WIRE and c=='di' else None) for c in frame), static[key]) for key,frame in tables.items()),
        (ParameterSpec('d0', '螺旋测微器零点 d₀ / mm', -.019, minimum=-.05, maximum=.05, step=.001, format='%.3f'),),
        compute, explain, validate=validate, format_tables=format_tables, build_plot=build_plot)
