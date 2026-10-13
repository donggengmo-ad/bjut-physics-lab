"""下册实验六：密立根油滴实验。"""

import math
from decimal import Decimal

import numpy as np
import pandas as pd


MEASUREMENT = '测量量'
DROPS = ('油滴一', '油滴二', '油滴三')
TIME_ROWS = tuple(f't_g{subscript} / s' for subscript in '₁₂₃₄₅')
STANDARD_E = 1.602e-19

# 实验参数（书中 20 ℃ 条件）
RHO = 981.0          # kg / m^3
G = 9.8017           # m / s^2
ETA = 1.83e-5        # kg / (m·s)
B = 8.23e-3          # Pa·m
P = 101_324.7        # Pa
L = 1.5e-3           # m
D = 5e-3             # m

CHARGE_COEFFICIENT = 18 * math.pi / math.sqrt(2 * RHO * G) * (ETA * L) ** 1.5 * D
CORRECTION_COEFFICIENT = B / P * math.sqrt(2 * RHO * G / (9 * ETA * L))


def calculate_drop(voltage, times):
    """按书中公式计算一个油滴；没有完整必要数据时返回空结果。"""
    numeric_times = pd.to_numeric(pd.Series(times), errors='raise').dropna().to_numpy(dtype=float)
    if len(numeric_times) and (not np.isfinite(numeric_times).all() or (numeric_times <= 0).any()):
        raise ValueError('下落时间必须为正的有限数值。')
    if pd.notna(voltage):
        voltage = float(voltage)
        if not math.isfinite(voltage) or voltage <= 0:
            raise ValueError('平衡电压必须为正的有限数值。')

    result = dict(mean_time=math.nan, radius=math.nan, charge=math.nan,
                  n_calculated=math.nan, n_integer=math.nan,
                  measured_e=math.nan, relative_error=math.nan)
    if not len(numeric_times):
        return result

    mean_time = float(numeric_times.mean())
    result['mean_time'] = mean_time
    result['radius'] = math.sqrt(9 * ETA * L / (2 * RHO * G * mean_time))
    if pd.isna(voltage):
        return result

    charge = CHARGE_COEFFICIENT / (
        (mean_time * (1 + CORRECTION_COEFFICIENT * math.sqrt(mean_time))) ** 1.5
        * voltage
    )
    n_calculated = charge / STANDARD_E
    n_integer = math.floor(n_calculated + 0.5)
    result.update(charge=charge, n_calculated=n_calculated, n_integer=n_integer)
    if n_integer > 0:
        measured_e = charge / n_integer
        result['measured_e'] = measured_e
        result['relative_error'] = abs(measured_e - STANDARD_E) / STANDARD_E * 100
    return result


def display_number(value, digits=3):
    # # 保留有效末尾零，例如 1.00，而不是 1。
    return f'{value:#.{digits}g}' if math.isfinite(value) else '未填写或无法计算'


def latex_number(value, digits=3):
    """把数值的科学计数法转换为可渲染的 LaTeX。"""
    text = display_number(value, digits)
    if 'e' in text:
        mantissa, exponent = text.split('e')
        return rf'{mantissa}\times10^{{{int(exponent)}}}'
    return text


def time_decimal_places(times):
    """按已有记录中最粗的小数精度显示平均值，不推定仪器分辨率。"""
    places = [max(0, -Decimal(str(value)).as_tuple().exponent)
              for value in times if pd.notna(value) and math.isfinite(float(value))]
    return min(places) if places else 0

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         InputState, ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant

DESCRIPTION = '\n##### 数据说明\n- 表 6-1 记录三个油滴各自的平衡电压 $U_i$，以及每个油滴 5 次通过 $l=1.5\\,\\mathrm{mm}$ 距离的下落时间 $t_{g_i}$。\n- 实验参数：$\\rho=981\\,\\mathrm{kg/m^3}$，$g=9.8017\\,\\mathrm{m/s^2}$，$\\eta=1.83\\times10^{-5}\\,\\mathrm{kg/(m\\cdot s)}$，$b=8.23\\times10^{-3}\\,\\mathrm{Pa\\cdot m}$，$p=101324.7\\,\\mathrm{Pa}$，$d=5\\,\\mathrm{mm}$。\n- “倒过来验证”采用公认电子电荷 $e_{\\text{标}}=1.602\\times10^{-19}\\,\\mathrm C$。\n- 注意测量结果及其不确定度的有效位数。\n'


ID = 'lower_06_millikan_oil_drop'
KEY = '表 6-1：密立根油滴法的实验数据记录'


def default_tables():
    return {KEY: pd.DataFrame({MEASUREMENT: ['U / V', *TIME_ROWS],
        '油滴一': [102, 30.9, 29.4, 29.47, 29.09, 28.73],
        '油滴二': [290, 11.18, 11.19, 11.03, 11.28, 11.05],
        '油滴三': [160, 11.71, 11.69, 11.93, 11.72, 11.75]})}


def compute(inputs):
    source = inputs.tables[KEY].set_index(MEASUREMENT)
    results, automatic_means, rows = {}, {}, []
    average_row = {MEASUREMENT: '平均下降时间 / s'}
    overrides = {drop: inputs.parameters[f'mean_{drop}'] for drop in DROPS}
    notes = []
    for drop in DROPS:
        voltage, times = source.loc['U / V', drop], source.loc[list(TIME_ROWS), drop]
        automatic = calculate_drop(voltage, times)
        automatic_means[drop] = automatic['mean_time']
        result = calculate_drop(voltage, [overrides[drop]]) if overrides[drop] is not None else automatic
        results[drop] = result
        average_row[drop] = result['mean_time']
        count = int(times.notna().sum())
        if count < 5 and overrides[drop] is None:
            notes.append(f'{drop}：有效下落时间 {count}/5 次。')
        if not math.isfinite(result['charge']):
            notes.append(f'{drop}：缺少电压或下落时间，电荷量暂不可用。')
        elif result['n_integer'] == 0:
            notes.append(f'{drop}：电荷倍数取整为 0，无法倒推电子电荷量。')
        rows.append({'油滴': drop[-1], 'Uᵢ / V': voltage, '平均 t̄gᵢ / s': result['mean_time'],
            'qᵢ / C': result['charge'], 'n计算ᵢ = qᵢ/e标': result['n_calculated'],
            'n整数ᵢ': result['n_integer'], 'e测ᵢ = qᵢ/n整数ᵢ / C': result['measured_e']})
    tables = {KEY: pd.concat([inputs.tables[KEY], pd.DataFrame([average_row])], ignore_index=True),
              '表 6-2：“倒过来验证”电荷量数据': pd.DataFrame(rows)}
    return ResultBundle(tables, dict(input_key=KEY, results=results, automatic_means=automatic_means, average_overrides=overrides), notes,
        tuple(Metric(f'{drop} · 电荷量', significant(results[drop]['charge'], 3, trailing=True), 'C') for drop in DROPS))


def time_text(inputs, drop, value, automatic=False):
    source = inputs.tables[KEY].set_index(MEASUREMENT)
    override = inputs.parameters[f'mean_{drop}']
    times = [override] if override is not None and not automatic else source.loc[list(TIME_ROWS), drop]
    return f'{value:.{time_decimal_places(times)}f}' if math.isfinite(value) else '—'


def get_spec():
    frame = default_tables()[KEY]
    return ExperimentSpec(ID, '实验六：密立根油滴实验', '下册', 6,
        '由下落时间与平衡电压计算油滴电荷，完成电荷量的倒向验证。', DESCRIPTION,
        (TableSpec(KEY, KEY, frame, tuple(ColumnSpec(c, 'text' if c==MEASUREMENT else 'number', positive=c!=MEASUREMENT) for c in frame), (MEASUREMENT,)),),
        tuple(ParameterSpec(f'mean_{drop}', f'{drop}平均下降时间 / s', None, positive=True, optional=True,
              help='留空时使用原始测量的平均值；填写后以此值计算。') for drop in DROPS),
        compute, explain, format_tables=format_tables, discussion=DISCUSSION)

DISCUSSION = '**（1）若平行极板不水平，对测量结果有何影响？**\n\n电场偏离竖直方向，油滴发生横向漂移，难以静止，导致平衡电压测量产生系统误差。\n\n**（2）如何选择合适的油滴进行测量？**\n\n选择清晰明亮、大小适中、下降缓慢稳定且能在适中电压下平衡的油滴，避免布朗运动明显的油滴。\n\n**（3）实验时怎样才能保证油滴做匀速运动？**\n\n撤去电场后，待油滴达到终端速度再计时，并避免气流和振动干扰。\n\n**（4）为什么在实验过程中会出现油滴漂移现象？**\n\n主要由空气对流、布朗运动及极板倾斜产生的水平电场分量引起。\n\n**分析与讨论**\n\n可以从实验结果、实验背景、实验原理、实验仪器、实验方法和实验应用等方面分析。'

def explain(inputs, result):
    doc = Explanation()
    data_automatic_means = result.values['automatic_means']
    data_average_overrides = result.values['average_overrides']
    data_initial_df = inputs.tables
    data_input_key = result.values['input_key']
    data_results = result.values['results']
    doc.markdown('**1. 计算三个油滴下落时间的平均值**')
    doc.latex(r'\overline{t}_{g_i}=\frac{1}{n}\sum_{j=1}^{n}t_{g_{ij}}')
    source = data_initial_df[data_input_key].set_index(MEASUREMENT)
    for index, drop in enumerate(DROPS, 1):
        values = pd.to_numeric(
            source.loc[list(TIME_ROWS), drop], errors='coerce'
        ).dropna().tolist()
        override = data_average_overrides.get(drop)
        if override is not None:
            doc.latex(rf'\overline{{t}}_{{g_{index}}}={time_text(inputs, drop, float(override))}\,\mathrm{{s}}\quad\text{{（直接修改值）}}')
            if values:
                doc.caption(f'{drop}由 5 次下落时间自动计算的平均值为 {time_text(inputs, drop, data_automatic_means[drop], automatic=True)} s。')
        elif values:
            terms = '+'.join(str(value) for value in values)
            doc.latex(rf'\overline{{t}}_{{g_{index}}}=\frac{{{terms}}}{{{len(values)}}}\approx{time_text(inputs, drop, data_results[drop]["mean_time"])}\,\mathrm{{s}}')
        else:
            doc.markdown(f'{drop}：下落时间未填写。')

    doc.markdown('**2. 计算三个油滴的电荷量**')
    doc.caption('代入过程保留保护位，等式末端与结果表按有效位数显示。')
    doc.latex(r'a_i=\sqrt{\frac{9\eta l}{2\rho g\overline{t}_{g_i}}}')
    doc.latex(r'q_i=\frac{18\pi}{\sqrt{2\rho g}}\left[\frac{\eta l}{\overline{t}_{g_i}\left(1+\frac{b}{pa_i}\right)}\right]^{\frac{3}{2}}\frac{d}{U_i}')
    doc.markdown('代入本实验参数后：')
    doc.latex(r'q_i=\frac{9.27\times10^{-15}}{\left[\overline{t}_{g_i}\left(1+0.0226\sqrt{\overline{t}_{g_i}}\right)\right]^{3/2}U_i}')
    for index, drop in enumerate(DROPS, 1):
        result = data_results[drop]
        voltage = source.loc['U / V', drop]
        if math.isfinite(result['charge']):
            # 代入过程保留保护位，结果表及等式末端按有效位数显示。
            t = f'{result["mean_time"]:g}'
            doc.latex(rf'a_{index}=\sqrt{{\frac{{9\times1.83\times10^{{-5}}\times1.5\times10^{{-3}}}}{{2\times981\times9.8017\times{t}}}}}\approx{latex_number(result["radius"])}\,\mathrm{{m}}')
            doc.latex(rf'q_{index}=\frac{{9.27\times10^{{-15}}}}{{\left[{t}\left(1+0.0226\sqrt{{{t}}}\right)\right]^{{3/2}}\times{float(voltage):g}}}\approx{latex_number(result["charge"])}\,\mathrm{{C}}')
        elif math.isfinite(result['mean_time']):
            doc.markdown(f'{drop}：平均下落时间为 {time_text(inputs, drop, result["mean_time"])} s，平衡电压未填写，暂不能计算电荷量。')
        else:
            doc.markdown(f'{drop}：暂不能计算电荷量。')

    doc.markdown('**3. 用“倒过来验证”的方法处理电荷量数据（结果见表 6-2）**')
    doc.latex(r'n_{\text{计算},i}=\frac{q_i}{e_{\text{标}}},\qquad e_{\text{测},i}=\frac{q_i}{n_{\text{整数},i}}')
    for index, drop in enumerate(DROPS, 1):
        result = data_results[drop]
        if math.isfinite(result['measured_e']):
            doc.latex(rf'n_{{\text{{计算}},{index}}}=\frac{{{latex_number(result["charge"], digits=6)}}}{{1.602\times10^{{-19}}}}\approx{latex_number(result["n_calculated"])}\approx {int(result["n_integer"])}')
            doc.latex(rf'e_{{\text{{测}},{index}}}=\frac{{{latex_number(result["charge"], digits=6)}}}{{{int(result["n_integer"])}}}\approx{latex_number(result["measured_e"])}\,\mathrm{{C}}')
        else:
            doc.markdown(f'{drop}：电荷量未算出，暂不能进行“倒过来验证”。')

    doc.markdown('**4. 计算实验值与公认值的相对误差**')
    doc.latex(r'E_r=\frac{\left|e_{\text{测}}-e_{\text{标}}\right|}{e_{\text{标}}}\times100\%')
    for index, drop in enumerate(DROPS, 1):
        result = data_results[drop]
        if math.isfinite(result['relative_error']):
            doc.latex(rf'E_{{r,{index}}}=\frac{{\left|{latex_number(result["measured_e"], digits=6)}-1.602\times10^{{-19}}\right|}}{{1.602\times10^{{-19}}}}\times100\%\approx{latex_number(result["relative_error"], digits=2)}\%')
        else:
            doc.markdown(f'{drop}：暂不能计算相对误差。')
    return doc

def format_tables(inputs, result):
    tables = []
    """小表格使用原生 Markdown 表格渲染表头和单元格公式。"""
    headers = {
        'Uᵢ / V': r'$U_i/\mathrm{V}$',
        '平均 t̄gᵢ / s': r'$\overline{t}_{g_i}/\mathrm{s}$',
        'qᵢ / C': r'$q_i/\mathrm{C}$',
        'n计算ᵢ = qᵢ/e标': r'$n_{\text{计算},i}=q_i/e_{\text{标}}$',
        'n整数ᵢ': r'$n_{\text{整数},i}$',
        'e测ᵢ = qᵢ/n整数ᵢ / C': r'$e_{\text{测},i}=q_i/n_{\text{整数},i}$，$\mathrm{C}$',
    }
    row_labels = {
        'U / V': r'$U/\mathrm{V}$',
        **{label: rf'$t_{{g_{index}}}/\mathrm{{s}}$'
           for index, label in enumerate(TIME_ROWS, 1)},
        '平均下降时间 / s': r'平均下降时间 $\overline{t}_g/\mathrm{s}$',
    }
    for index, (name, frame) in enumerate(result.tables.items(), 1):
        display = frame.copy()
        for column in frame.columns:
            if pd.api.types.is_numeric_dtype(frame[column]):
                cells = []
                for row, value in enumerate(frame[column]):
                    if pd.isna(value):
                        cells.append('—')
                        continue
                    if MEASUREMENT in frame:
                        label = frame.iloc[row][MEASUREMENT]
                        if label == '平均下降时间 / s':
                            text = time_text(inputs, column, value)
                        elif label == 'U / V':
                            text = f'{value:g}'
                        else:
                            text = str(value)
                    elif column == '平均 t̄gᵢ / s':
                        text = time_text(inputs, DROPS[row], value)
                    elif column == 'Uᵢ / V':
                        text = f'{value:g}'
                    elif column == 'n整数ᵢ':
                        text = str(int(value))
                    else:
                        text = latex_number(value)
                    cells.append(f'${text}$')
                display[column] = cells
        if MEASUREMENT in display:
            display[MEASUREMENT] = display[MEASUREMENT].replace(row_labels)
        tables.append(DisplayTable(name, display.rename(columns=headers), math=True))

    return tables
