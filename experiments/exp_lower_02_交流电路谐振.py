"""下册实验二；表 2-1 至表 2-4 及书本要求的数据处理。"""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go


FREQUENCIES = [*range(1400, 2200, 100), *range(2200, 2310, 10), *range(2400, 3401, 100)]
VOLTAGES = {
    100: [0.065, 0.079, 0.095, 0.122, 0.148, 0.208, 0.277, 0.442,
          0.731, 0.757, 0.774, 0.798, 0.803, 0.802, 0.799, 0.779,
          0.762, 0.732, 0.700, 0.439, 0.299, 0.226, 0.181, 0.151,
          0.130, 0.113, 0.101, 0.091, 0.083, 0.076],
    500: [0.330, 0.385, 0.445, 0.525, 0.608, 0.703, 0.812, 0.894,
          0.950, 0.951, 0.961, 0.952, 1.097, 0.952, 0.951, 0.949,
          0.948, 0.945, 0.947, 0.901, 0.826, 0.745, 0.671, 0.605,
          0.550, 0.504, 0.463, 0.427, 0.401, 0.373],
}
FREQ = 'f / Hz'
UR = 'U_R / mV'
CURRENT = 'I / mA'
R_COL = 'R / Ω'
UL = 'U_L / V'
UC = 'U_C / V'


def scan_table(frame, resistance):
    """mV / Ω = mA；保留空白电压，不以零替代。"""
    result = frame[[FREQ, UR]].apply(pd.to_numeric, errors='raise').copy()
    if (not np.isfinite(result[FREQ]).all() or (result[FREQ] <= 0).any()
            or result[FREQ].duplicated().any()):
        raise ValueError('频率必须为互不重复的正数。')
    voltage = result[UR].dropna()
    if not np.isfinite(voltage).all() or (voltage < 0).any():
        raise ValueError('电压必须为非负有限数值。')
    result[CURRENT] = result[UR] / resistance
    return result.sort_values(FREQ).reset_index(drop=True)


def analyze_curve(table):
    """取测量峰值，并计算图中测量点连线与半功率水平线的交点。"""
    table = table.reset_index(drop=True)
    valid = table.dropna(subset=[FREQ, CURRENT])
    result = dict(f0=math.nan, imax=math.nan, level=math.nan,
                  f1=math.nan, f2=math.nan, bandwidth=math.nan,
                  cutoff_error=None)
    if valid.empty:
        result['cutoff_error'] = '没有有效测量数据，无法确定截止频率。'
        return result
    imax = float(valid[CURRENT].max())
    level = imax / math.sqrt(2)
    result.update(imax=imax, level=level)
    peaks = valid.index[valid[CURRENT] == imax]
    if len(peaks) != 1:
        result['cutoff_error'] = '最大电流对应多个测量频率，无法唯一确定谐振峰。'
        return result
    peak = int(peaks[0])
    result['f0'] = float(table.loc[peak, FREQ])
    if peak in (0, len(table) - 1) or imax <= 0:
        result['cutoff_error'] = '测量数据未覆盖谐振峰两侧，无法确定通频带宽。'
        return result
    frequencies = table[FREQ].to_numpy(dtype=float)
    currents = table[CURRENT].to_numpy(dtype=float)
    missing = []
    for field, indices in [('f1', range(peak)), ('f2', range(peak, len(table) - 1))]:
        crossings = set()
        plateau = False
        for i in indices:
            ia, ib = currents[i:i + 2]
            if not math.isfinite(ia) or not math.isfinite(ib):
                continue
            if ia == ib:
                plateau |= ia == level
            elif min(ia, ib) <= level <= max(ia, ib):
                fa, fb = frequencies[i:i + 2]
                crossings.add(float(fa + (level - ia) * (fb - fa) / (ib - ia)))
        if len(crossings) == 1 and not plateau:
            result[field] = crossings.pop()
        else:
            missing.append(field)
    if missing:
        result['cutoff_error'] = f'{"、".join(missing)}：测量点连线与截止电流水平线没有唯一交点。'
    if math.isfinite(result['f1']) and math.isfinite(result['f2']):
        result['bandwidth'] = abs(result['f2'] - result['f1'])
    return result


def quality_factors(resistance, coil_resistance, ul, uc, source_voltage, inductance,
                    theoretical_f0, curve):
    return (
        2 * math.pi * theoretical_f0 * inductance / (resistance + coil_resistance),
        ul / source_voltage,
        uc / source_voltage,
        curve['f0'] / curve['bandwidth'] if curve['bandwidth'] > 0 else math.nan,
    )


def fmt(value):
    return f'{value:.4g}' if value is not None and math.isfinite(value) else '未填写或无法计算'

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         InputState, ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant

DESCRIPTION = '\n##### 数据说明\n- 电源输出电压 $U=1\\,\\mathrm V$；电感 $L=0.1\\,\\mathrm H$；电容 $C=0.05\\,\\mu\\mathrm F$。\n- 原始数据已由 kHz、V 转为书本表格的 Hz、mV；电流按 $I=U_R/R$ 计算，单位 mA。\n- 实测谐振频率直接取各组测量电压 $U_R$ 最大值所在的测量频率。\n- 程序计算测量点连线与 $I_{\\max}/\\sqrt2$ 水平线的交点频率 $f_1、f_2$，在图上以垂直虚线及横轴数值标出，并计算 $\\Delta f=|f_2-f_1|$。\n- 谐振频率附近测量步长为 10 Hz，数据点要丰富。\n- 表 2-3 的电压为谐振状态下的测量值；$R_L$ 为电感不接入电路时测得的电感电阻。\n- 绘图须标出图名、坐标轴对应的物理量及单位，原始数据点要清晰；注意测量结果及其不确定度的有效位数。\n'


ID = 'lower_02_resonance'
SCAN_KEYS = {r: f'表 2-{i}：R={r} Ω 时的电压、电流数据表' for i, r in enumerate((100, 500), 1)}
VOLTAGE_KEY = '表 2-3：谐振状态下的电压分布'


def default_tables():
    tables = {SCAN_KEYS[r]: pd.DataFrame({FREQ: FREQUENCIES, UR: np.array(VOLTAGES[r]) * 1000}) for r in (100, 500)}
    tables[VOLTAGE_KEY] = pd.DataFrame({R_COL: [100, 500], UL: [12., 2.715], UC: [12.05, 2.718]})
    return tables


def validate(inputs):
    issues = []
    for key in SCAN_KEYS.values():
        frequencies = inputs.tables[key][FREQ]
        for row in frequencies.index[frequencies.isna() | (frequencies <= 0) | frequencies.duplicated()]:
            issues.append(ValidationIssue('频率必须为互不重复的正数。', key, int(row), FREQ))
    return issues


def compute(inputs):
    rl = inputs.parameters['rl']
    theoretical_f0 = 1 / (2 * math.pi * math.sqrt(0.1 * 0.05e-6))
    curves, q, measured_f0, tables = {}, {}, {}, {}
    voltage = inputs.tables[VOLTAGE_KEY].set_index(R_COL)
    notes = []
    for resistance, key in SCAN_KEYS.items():
        table = scan_table(inputs.tables[key], resistance)
        tables[key] = table
        curve = curves[resistance] = analyze_curve(table)
        measured_f0[resistance] = curve['f0']
        q[resistance] = quality_factors(resistance, rl, float(voltage.loc[resistance, UL]),
                                        float(voltage.loc[resistance, UC]), 1., .1, theoretical_f0, curve)
        if curve['cutoff_error']:
            notes.append(f'R={resistance} Ω：{curve["cutoff_error"]}')
    table3 = inputs.tables[VOLTAGE_KEY].copy()
    table3['R_L / Ω（共用）'] = rl
    tables['表 2-3：谐振状态下的电压分布和不接电路时的电感电阻'] = table3
    tables['表 2-4：品质因数 Q 的理论值、实验值及画图计算值对比'] = pd.DataFrame({
        '类别': ['理论值', '实验值', '实验值', '画图计算值'],
        'Q': ['Q₁ = ω₀L/(R+R_L)', 'Q₂ = U_L/U', 'Q₃ = U_C/U', 'Q₄ = f₀/Δf'],
        'R=100 Ω': q[100], 'R=500 Ω': q[500],
    })
    return ResultBundle(tables, dict(scan_keys=SCAN_KEYS, voltage_key=VOLTAGE_KEY, rl=rl,
        curves=curves, q=q, measured_f0=measured_f0, theoretical_f0=theoretical_f0), notes,
        tuple(Metric(f'R={r} Ω · {label}', significant(curves[r][field]), unit)
              for r in (100, 500) for label, field, unit in [('谐振频率', 'f0', 'Hz'), ('通频带宽', 'bandwidth', 'Hz')]))


def get_spec():
    tables = default_tables()
    return ExperimentSpec(ID, '实验二：交流电路的谐振现象', '下册', 2,
        '记录电压与频率，比较谐振曲线、通频带宽和品质因数。', DESCRIPTION,
        tuple(TableSpec(key, key, frame, tuple(ColumnSpec(c, minimum=0., positive=c==FREQ) for c in frame),
                         (FREQ,) if key in SCAN_KEYS.values() else (R_COL,), variable_rows=key in SCAN_KEYS.values(),
                         help='电源 U=1 V · 电感 L=0.1 H · 电容 C=0.05 μF') for key, frame in tables.items()),
        (ParameterSpec('rl', '电感电阻 R_L / Ω', 18.8, minimum=0., format='%.1f', help='电感不接入电路时测得'),),
        compute, explain, validate=validate, build_plot=build_plot, discussion=DISCUSSION,
        plot_caption='截止频率由测量点连线与 Imax/√2 的交点自动确定；缺测处不连接。')

DISCUSSION = '**思考题**\n\n将 RLC 串联电路中的 R 从 100 Ω 调整为 500 Ω，而其他条件不变，电路的谐振特性会有什么变化？为什么？\n\n\n**回答：** 在串联 RLC 电路模型中，保持电源电压、电感、电容及电感电阻不变，\n将 $R$ 从 $100\\,\\Omega$ 增大到 $500\\,\\Omega$，理论谐振频率不变，\n峰值电流减小，谐振曲线变低、变宽，通频带宽增大，品质因数减小，选频能力减弱。\n\n谐振时感抗与容抗相等，$\\omega_0L=1/(\\omega_0C)$，因此\n$$f_0=\\frac{1}{2\\pi\\sqrt{LC}}$$\n只由 $L、C$ 决定，与 $R$ 无关。谐振时电路总阻抗为 $R+R_L$，因此\n$$I_{\\max}=\\frac{U}{R+R_L}$$\n随 $R$ 增大而减小；谐振时电感、电容上的电压放大作用也减弱。\n\n电阻增大使电路阻尼增强。由\n$$\nQ=\\frac{\\omega_0L}{R+R_L},\\qquad \\Delta f=\\frac{f_0}{Q}=\\frac{R+R_L}{2\\pi L}\n$$\n可知，$R$ 增大时 $Q$ 减小、$\\Delta f$ 增大，所以谐振峰变宽，选频能力减弱。\n'

def explain(inputs, result):
    doc = Explanation()
    data_curves = result.values['curves']
    data_final_df = result.tables
    data_initial_df = inputs.tables
    data_measured_f0 = result.values['measured_f0']
    data_q = result.values['q']
    data_rl = result.values['rl']
    data_scan_keys = result.values['scan_keys']
    data_theoretical_f0 = result.values['theoretical_f0']
    data_voltage_key = result.values['voltage_key']
    doc.markdown('**1. 数据整理、绘制谐振曲线与计算通频带宽**')
    doc.latex(r'I=\frac{U_R}{R},\qquad I(\mathrm{mA})=\frac{U_R(\mathrm{mV})}{R(\Omega)}')
    doc.caption('截止频率由程序计算图中测量点连线与 Imax/√2 水平线的交点；测量点之间按图中的直线段取值（线性插值）。')
    for resistance, key in data_scan_keys.items():
        doc.markdown(f'**R={resistance} Ω**')
        row = data_final_df[key].dropna(subset=[UR]).head(1)
        if not row.empty:
            row = row.iloc[0]
            doc.latex(rf'I_{{f={row[FREQ]:g}\,\mathrm{{Hz}}}}=\frac{{{row[UR]:g}}}{{{resistance}}}={row[CURRENT]:g}\,\mathrm{{mA}}')
        curve = data_curves[resistance]
        if math.isfinite(curve['level']):
            doc.latex(rf'I_{{\max}}={curve["imax"]:.4g}\,\mathrm{{mA}},\quad I_{{\mathrm{{截止}}}}=\frac{{{curve["imax"]:.4g}}}{{\sqrt2}}={curve["level"]:.4g}\,\mathrm{{mA}}')
        if curve['cutoff_error']:
            doc.warning(f'R={resistance} Ω：{curve["cutoff_error"]}')
        for label, field in [('1', 'f1'), ('2', 'f2')]:
            if math.isfinite(curve[field]):
                doc.latex(rf'f_{label}={curve[field]:.2f}\,\mathrm{{Hz}}\quad\text{{（测量点连线交点）}}')
            else:
                doc.markdown(f'R={resistance} Ω：暂不能确定 f{label}。')
        if math.isfinite(curve['bandwidth']):
            doc.latex(rf'\Delta f=|f_2-f_1|=|{curve["f2"]:g}-{curve["f1"]:g}|={curve["bandwidth"]:g}\,\mathrm{{Hz}}')
        else:
            doc.markdown('Δf：两侧截止频率无法确定，暂不能计算。')

    doc.markdown('**2. 计算理论谐振频率，并与实验值比较**')
    doc.latex(r'C=0.05\,\mu\mathrm F=0.05\times10^{-6}\,\mathrm F')
    doc.latex(rf'f_{{0,\mathrm{{理论}}}}=\frac{{1}}{{2\pi\sqrt{{LC}}}}=\frac{{1}}{{2\pi\sqrt{{0.1\times0.05\times10^{{-6}}}}}}={data_theoretical_f0:.2f}\,\mathrm{{Hz}}')
    for resistance, measured in data_measured_f0.items():
        if not math.isfinite(measured):
            doc.markdown(f'R={resistance} Ω：无法唯一确定测量电压最大值对应频率，暂不能与理论值比较。')
        else:
            relation = '高于' if measured > data_theoretical_f0 else '低于' if measured < data_theoretical_f0 else '等于'
            doc.markdown(f'R={resistance} Ω：实测谐振频率 {measured:g} Hz，{relation}理论值 {data_theoretical_f0:.2f} Hz。')

    doc.markdown('**3. 品质因数的计算与比较（结果见表 2-4）**')
    doc.caption('Q₁ 中 ω₀=2πf₀，采用理论谐振频率；Q₄ 中 f₀ 采用实测谐振频率，即该组测量电压最大值对应频率。')
    voltage = data_initial_df[data_voltage_key].set_index(R_COL)
    for resistance in (100, 500):
        curve, q = data_curves[resistance], data_q[resistance]
        doc.markdown(f'**R={resistance} Ω**')
        doc.latex(rf'Q_1=\frac{{\omega_0L}}{{R+R_L}}=\frac{{2\pi\times{data_theoretical_f0:.6g}\times0.1}}{{{resistance}+{data_rl:g}}}={q[0]:.4g}')
        for i, col, symbol in [(1, UL, 'L'), (2, UC, 'C')]:
            value = float(voltage.loc[resistance, col])
            if math.isfinite(value):
                doc.latex(rf'Q_{i+1}=\frac{{U_{symbol}}}{{U}}=\frac{{{value:g}}}{{1}}={q[i]:.4g}')
            else:
                doc.markdown(f'Q{i+1}：谐振电压未填写。')
        if math.isfinite(q[3]):
            doc.latex(rf'Q_4=\frac{{f_0}}{{\Delta f}}=\frac{{{curve["f0"]:g}}}{{{curve["bandwidth"]:.6g}}}={q[3]:.4g}')
            for i in (1, 2):
                if math.isfinite(q[i]):
                    relation = '大于' if q[i] > q[3] else '小于' if q[i] < q[3] else '等于'
                    doc.markdown(f'实验值 Q{i+1}={fmt(q[i])}，{relation}画图计算值 Q4={fmt(q[3])}。')
        else:
            doc.markdown('Q4：实测谐振频率或带宽无法确定，暂不能计算和比较。')
    return doc

def build_plot(inputs, result):
    data_curves = result.values['curves']
    data_final_df = result.tables
    data_scan_keys = result.values['scan_keys']
    fig = go.Figure()
    cutoff_ticks = set()
    for resistance, color in [(100, '#2F81F7'), (500, '#D55E00')]:
        table = data_final_df[data_scan_keys[resistance]]
        curve = data_curves[resistance]
        fig.add_trace(go.Scatter(x=table[FREQ], y=table[CURRENT], mode='lines+markers',
                                 name=f'R={resistance} Ω', line={'color': color, 'dash': 'solid' if resistance == 100 else 'dash'}, marker={'symbol': 'circle' if resistance == 100 else 'diamond'},
                                 connectgaps=False))
        if not math.isfinite(curve['level']):
            continue
        fig.add_hline(y=curve['level'], line_dash='dash', line_color=color,
                      annotation_text=f'{resistance} Ω：Imax/√2={curve["level"]:.4g} mA',
                      annotation_position='top right' if resistance == 100 else 'bottom right')
        for field in ('f1', 'f2'):
            if math.isfinite(curve[field]):
                fig.add_shape(type='line', x0=curve[field], x1=curve[field], y0=0,
                              y1=curve['level'], line={'color': color, 'dash': 'dash', 'width': 2})
                fig.add_annotation(
                    x=curve[field], y=curve['level'], xref='x', yref='y',
                    text=f'R={resistance} Ω<br>{"f₁" if field == "f1" else "f₂"}={curve[field]:.2f} Hz',
                    showarrow=True, arrowhead=2, arrowcolor=color,
                    ax=-45 if field == 'f1' else 45,
                    ay=-65 if resistance == 100 else -85,
                    xanchor='right' if field == 'f1' else 'left',
                    font={'color': color, 'size': 13}, align='center')
                cutoff_ticks.add(curve[field])
    minimum = min(frame[FREQ].min() for key, frame in data_final_df.items() if key in data_scan_keys.values())
    maximum = max(frame[FREQ].max() for key, frame in data_final_df.items() if key in data_scan_keys.values())
    # 避免常规刻度挤占截止频率标注的位置。
    regular_ticks = [float(tick) for tick in np.linspace(minimum, maximum, 6)
                     if all(abs(tick - cutoff) >= (maximum - minimum) / 20 for cutoff in cutoff_ticks)]
    ticks = sorted(set(regular_ticks) | cutoff_ticks)
    labels = [f'<b>{tick:.2f}</b>' if tick in cutoff_ticks else f'{tick:g}' for tick in ticks]
    fig.update_layout(title='RLC 串联电路的谐振曲线（I-f 曲线）',
                      xaxis_title='频率 f / Hz', yaxis_title='电流 I / mA',
                      legend_title='电阻 R', height=650,
                      margin={'b': 120})
    fig.update_xaxes(tickmode='array', tickvals=ticks, ticktext=labels, tickangle=-45,
                     tickfont={'size': 14}, ticks='outside', ticklen=8,
                     showline=True, linewidth=2)
    ymax = max((curve['imax'] for curve in data_curves.values()
                if math.isfinite(curve['imax'])), default=0)
    fig.update_yaxes(range=[0, max(ymax * 1.12, 1)], showline=True, linewidth=2)
    return fig
