"""下册实验五：声速的测量。按手册表 5-1 与数据处理三步计算。"""

import math

import numpy as np
import pandas as pd


T0 = 273.15
ATMOSPHERE = 1.013e5  # 手册公式中的 P，取标准大气压。
ROWS = 10
SPAN = 5  # Δlᵢ = l_{i+5} − lᵢ
INDEX = '序号 i'
L_RESONANCE = 'lᵢ/mm（共振干涉法）'
L_PHASE = 'lᵢ/mm（相位比较法）'
D_RESONANCE = 'Δlᵢ/mm（共振干涉法）'
D_PHASE = 'Δlᵢ/mm（相位比较法）'
RESONANCE = '共振干涉法'
PHASE = '相位比较法'

# 表 5-1 记录数据；两列逐差均值 23.762 mm、23.110 mm 与记录页一致。
INTERFERENCE_DATA = [1.03, 5.80, 10.50, 15.25, 20.03, 24.74, 29.61, 34.35, 38.96, 43.76]
PHASE_DATA = [1.28, 5.89, 10.60, 15.12, 19.65, 24.29, 29.07, 33.46, 38.22, 43.05]


def successive_differences(values):
    """逐差：Δlᵢ = l_{i+5} − lᵢ，只有前 n−5 项。"""
    numbers = pd.to_numeric(pd.Series(values), errors='coerce').to_numpy(dtype=float)
    return numbers[SPAN:] - numbers[:len(numbers) - SPAN]


def mean_and_wavelength(deltas):
    """Δl̄ = (1/n)ΣΔlᵢ，λ = 2(Δl̄/5)；缺值不参与平均，也不当作零。"""
    filled = deltas[np.isfinite(deltas)]
    if filled.size == 0:
        return math.nan, math.nan
    mean = float(filled.mean())
    return mean, 2 * mean / SPAN


def theoretical_speed(temperature, saturated_pressure, humidity,
                      pressure=ATMOSPHERE):
    """v = 331.45√((1+t/T0)(1+0.3192 rPₛ/P))。"""
    return 331.45 * math.sqrt(
        (1 + temperature / T0) * (1 + 0.3192 * humidity * saturated_pressure / pressure)
    )


def relative_error(measured, theoretical):
    if not math.isfinite(measured) or not math.isfinite(theoretical) or theoretical == 0:
        return math.nan
    return abs(measured - theoretical) / theoretical * 100


def fixed(value, digits):
    """按固定小数位显示，保证两种方法的有效位数一致。"""
    return f'{value:.{digits}f}' if value is not None and math.isfinite(value) else '未填写或无法计算'


def error_text(value):
    """相对误差取两位有效数字：1.0013% 写作 1.0%，不能退化成 1%。"""
    if value is None or not math.isfinite(value):
        return '未填写或无法计算'
    if value == 0:
        return '0.0'
    digits = max(0, 2 - math.floor(math.log10(abs(value))) - 1)
    return f'{value:.{digits}f}'


def _cells(values, digits):
    return [f'{value:.{digits}f}' if math.isfinite(value) else '' for value in values]


def _mean_cell(value):
    return f'{value:.3f}' if math.isfinite(value) else ''

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         InputState, ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant

DESCRIPTION = '\n##### 数据说明\n- 表 5-1：序号 $i$、$l_i$（共振干涉法、相位比较法），单位为 mm。\n- $\\Delta l_i = l_{i+5}-l_i$，只对应前五行；表尾给出平均值 $\\overline{\\Delta l}$。\n- 表头环境参数：谐振频率 $f$（kHz）、室温 $t$（℃）、饱和蒸气压 $P_\\mathrm{s}$（$\\times10^5$ Pa）、相对湿度 $r$（%）。\n- 逐差法求波长：$\\overline{\\Delta l}=\\frac{1}{n}\\sum\\limits_{i=1}^{n}\\Delta l_i$，$\\lambda=2\\left(\\frac{\\overline{\\Delta l}}{5}\\right)$。\n- 声速测量值：$v_\\text{测}=\\lambda f$。\n##### 数据处理\n1. 计算声速理论值 $v$：$v=331.45\\sqrt{\\left(1+\\frac{t}{T_0}\\right)\\left(1+0.3192\\frac{rP_\\mathrm{s}}{P}\\right)}$，$T_0=273.15$ K，大气压 $P$ 取 $1.013\\times10^5$ Pa。\n2. 共振干涉法测声速：逐差法求 $\\lambda$，再由 $v_\\text{测}=\\lambda f$ 求声速，并计算相对误差。\n3. 相位比较法测声速：同上。\n4. 相对误差 $E_\\mathrm{r}=\\frac{|v_\\text{测}-v|}{v}\\times100\\%$，误差取两位有效数字。\n'


ID = 'lower_05_sound_speed'
KEY = '表 5-1：测量数据记录'


def default_tables():
    return {KEY: pd.DataFrame({INDEX: list(range(1, ROWS + 1)), L_RESONANCE: INTERFERENCE_DATA, L_PHASE: PHASE_DATA})}


def validate(inputs):
    issues = []
    for column in (L_RESONANCE, L_PHASE):
        values = inputs.tables[KEY][column].to_numpy(dtype=float)
        differences = successive_differences(values)
        for row in np.flatnonzero(np.isfinite(differences) & (differences <= 0)):
            issues.append(ValidationIssue('后一位置应大于对应的前一位置，才能求得正波长。', KEY, int(row + SPAN), column))
    return issues


def compute(inputs):
    table = inputs.tables[KEY]
    frequency, temperature, saturated, humidity = (inputs.parameters[k] for k in ('frequency', 'temperature', 'saturated', 'humidity'))
    columns = {RESONANCE: table[L_RESONANCE].to_numpy(dtype=float), PHASE: table[L_PHASE].to_numpy(dtype=float)}
    deltas = {method: successive_differences(values) for method, values in columns.items()}
    means, wavelengths, measured, errors = {}, {}, {}, {}
    theoretical = theoretical_speed(temperature, saturated * 1e5, humidity / 100)
    notes = []
    for method, differences in deltas.items():
        mean, wave = mean_and_wavelength(differences)
        means[method], wavelengths[method] = mean, wave
        measured[method] = wave * frequency
        errors[method] = relative_error(measured[method], theoretical)
        count = int(np.isfinite(differences).sum())
        if count < 5:
            notes.append(f'{method}：有效逐差记录 {count}/5，平均值仅使用完整的测量对。')
    result_table = pd.DataFrame({INDEX: [*map(str, range(1, ROWS + 1)), '平均值 Δl̄']})
    for column, method in ((L_RESONANCE, RESONANCE), (L_PHASE, PHASE)):
        result_table[column] = [*columns[method], math.nan]
    for column, method in ((D_RESONANCE, RESONANCE), (D_PHASE, PHASE)):
        result_table[column] = [*deltas[method], *[math.nan] * (ROWS - SPAN), means[method]]
    return ResultBundle({KEY: result_table}, dict(deltas=deltas, means=means, wavelengths=wavelengths,
        measured=measured, errors=errors, theoretical=theoretical, frequency=frequency, temperature=temperature,
        saturated=saturated, humidity=humidity), notes,
        (Metric('理论声速', fixed(theoretical, 1), 'm/s'),
         Metric('共振干涉法', fixed(measured[RESONANCE], 1), 'm/s'),
         Metric('相位比较法', fixed(measured[PHASE], 1), 'm/s')))


def format_tables(inputs, result):
    display = result.tables[KEY].copy()
    for column in (L_RESONANCE, L_PHASE):
        display[column] = [*_cells(display[column].iloc[:ROWS], 2), '']
    for column in (D_RESONANCE, D_PHASE):
        display[column] = [*_cells(display[column].iloc[:SPAN], 2), *[''] * SPAN, _mean_cell(display[column].iloc[-1])]
    return [DisplayTable(KEY, display)]


def get_spec():
    frame = default_tables()[KEY]
    return ExperimentSpec(ID, '实验五：声速的测量', '下册', 5,
        '用逐差法处理测量位置，比较两种方法的声速与相对误差。', DESCRIPTION,
        (TableSpec(KEY, KEY, frame, tuple(ColumnSpec(c, minimum=0., format='%.2f' if c != INDEX else '%d') for c in frame), (INDEX,)),),
        (ParameterSpec('frequency', '谐振频率 f / kHz', 37.1, positive=True, minimum=0., format='%.1f'),
         ParameterSpec('temperature', '室温 t / ℃', 27.7, minimum=0., format='%.1f'),
         ParameterSpec('saturated', '饱和蒸气压 Pₛ / ×10⁵ Pa', .0378, minimum=0., step=.0001, format='%.4f'),
         ParameterSpec('humidity', '相对湿度 r / %', 62., minimum=0., maximum=100., step=1., format='%.1f')),
        compute, explain, validate=validate, format_tables=format_tables, discussion=DISCUSSION)

DISCUSSION = '\n**（1）产生驻波的条件是什么？如何产生稳定的驻波？**\n\n两列振幅、频率、振动方向相同而传播方向相反的相干波在同一直线上叠加。$S_1$ 发出的超声波经 $S_2$ 反射后与入射波叠加即成驻波；端面平行且垂直于轴线、频率等于换能器固有频率时驻波稳定。\n\n**（2）是否可以利用此方法测定超声波在其他介质中的传播速度？**\n\n可以。依据是 $v=\\lambda f$，与介质种类无关，只要该介质能传播超声波、能形成驻波或比较相位即可；更换介质需换用声阻抗匹配的换能器并良好耦合。\n\n**（3）为什么要在换能器谐振状态下测定空气中的声速？**\n\n谐振时电声转换效率最高、发射振幅最大、接收信号最强，驻波极大值（或相位差零点）最尖锐、易判断，误差小；且输出频率稳定，读得的 $f$ 更可靠。\n\n**（4）实验中如何使信号源的输出频率等于换能器的固有频率？**\n\n固定两换能器间距，缓慢调节信号源频率，同时观察示波器上接收信号的幅度，波形幅度最大时该频率即为换能器固有频率，可直接读出。\n'

def explain(inputs, result):
    doc = Explanation()
    data_deltas = result.values['deltas']
    data_errors = result.values['errors']
    data_frequency = result.values['frequency']
    data_humidity = result.values['humidity']
    data_means = result.values['means']
    data_measured = result.values['measured']
    data_saturated = result.values['saturated']
    data_temperature = result.values['temperature']
    data_theoretical = result.values['theoretical']
    data_wavelengths = result.values['wavelengths']
    doc.markdown('**（1）计算声速理论值 v**')
    doc.latex(r'v=331.45\sqrt{\left(1+\frac{t}{T_0}\right)\left(1+0.3192\frac{rP_\mathrm{s}}{P}\right)}')
    doc.latex(rf't={data_temperature:g}\,^\circ\mathrm{{C}},\quad T_0={T0:g}\,\mathrm{{K}},\quad '
             rf'r={data_humidity:g}\%,\quad P_\mathrm{{s}}={data_saturated:g}\times10^5\,\mathrm{{Pa}},\quad '
             rf'P={ATMOSPHERE / 1e5:g}\times10^5\,\mathrm{{Pa}}')
    doc.latex(rf'v=331.45\sqrt{{\left(1+\frac{{{data_temperature:g}}}{{{T0:g}}}\right)'
             rf'\left(1+0.3192\times\frac{{{data_humidity / 100:.2f}\times'
             rf'{data_saturated:g}\times10^5}}{{{ATMOSPHERE / 1e5:g}\times10^5}}\right)}}'
             rf'={fixed(data_theoretical, 1)}\,\mathrm{{m/s}}')

    for order, method in ((2, RESONANCE), (3, PHASE)):
        doc.markdown(f'**（{order}）{method}测声速**')
        doc.markdown('① 运用逐差法处理数据，计算波长 λ')
        doc.latex(r'\overline{\Delta l}=\frac{1}{n}\sum_{i=1}^{n}\Delta l_i')
        terms = [value for value in data_deltas[method] if math.isfinite(value)]
        if terms:
            doc.latex(rf'\overline{{\Delta l}}=\frac{{1}}{{{len(terms)}}}'
                     rf'\left({" + ".join(f"{value:.2f}" for value in terms)}\right)'
                     rf'={data_means[method]:.3f}\,\mathrm{{mm}}')
        else:
            doc.markdown('Δl̄：逐差值未填写，暂不能计算。')
        doc.latex(r'\lambda=2\left(\frac{\overline{\Delta l}}{5}\right)')
        if math.isfinite(data_wavelengths[method]):
            doc.latex(rf'\lambda=2\times\frac{{{data_means[method]:.3f}}}{{5}}'
                     rf'={data_wavelengths[method]:.4f}\,\mathrm{{mm}}'
                     rf'={fixed(data_wavelengths[method] / 1000, 7)}\,\mathrm{{m}}')
        else:
            doc.markdown('λ：平均逐差值未填写，暂不能计算。')
        doc.markdown('② 计算声速的测量值 v测')
        doc.latex(r'v_\text{测}=\lambda f')
        if math.isfinite(data_measured[method]):
            doc.latex(rf'v_\text{{测}}={fixed(data_wavelengths[method] / 1000, 7)}\times'
                     rf'{data_frequency:g}\times10^3={fixed(data_measured[method], 1)}\,\mathrm{{m/s}}')
        else:
            doc.markdown('v测：波长未填写，暂不能计算。')
        doc.markdown('③ 计算声速测量值与理论值的相对误差 Eᵣ')
        doc.latex(r'E_\mathrm{r}=\frac{\left|v_\text{测}-v\right|}{v}\times100\%')
        if math.isfinite(data_errors[method]):
            doc.latex(rf'E_\mathrm{{r}}=\frac{{\left|{fixed(data_measured[method], 1)}-'
                     rf'{fixed(data_theoretical, 1)}\right|}}{{{fixed(data_theoretical, 1)}}}\times100\%'
                     rf'={error_text(data_errors[method])}\%')
        else:
            doc.markdown('Er：测量值或理论值未填写，暂不能计算。')

    return doc
