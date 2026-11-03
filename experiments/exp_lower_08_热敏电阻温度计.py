"""下册实验八：以报告 pp.54–58 的记录和要求为依据。"""
import math
from decimal import Decimal, ROUND_HALF_UP, localcontext
from functools import lru_cache
from io import BytesIO

import numpy as np
import pandas as pd

from core.formatting import significant, latex_number
from core.models import (ColumnSpec, TableSpec, ExperimentSpec, ResultBundle,
                         Metric, Explanation, DisplayTable, ValidationIssue)

ID = 'lower_08_thermistor'
ENV = '自制温度计参数①：环境或仪器参数'
DESIGN = '自制温度计参数②：设计或估算的参数（R₁、R₂保留百位）'
CAL = '校准部分参数'
SCAN = '表 8-1：I_g–T 数据'
NAME, UNIT, VALUE = '物理量', '单位', '记录值'
POINT, TEMP, CURRENT = '测量点', '温度 / ℃', '电流 / μA'
HIGH = 75.0
ENV_ROWS = [('室温 t室', '℃', 24.), ('微安表内阻 Rg', 'Ω', 157.8),
            ('微安表量程下限', 'μA', 0.), ('微安表量程上限', 'μA', 300.),
            ('室温热敏电阻 R室', 'Ω', 5090.), ('75 ℃热敏电阻 R75', 'Ω', 800.)]
DESIGN_ROWS = [('R1', 'Ω', 2900.), ('R2', 'Ω', 2900.),
               ('估算 R3', 'Ω', 5090.), ('估算 E计', 'V', 2.0)]
CAL_ROWS = [('校准 Rs', 'Ω', 5100.), ('校准电源电压 E', 'V', 2.32)]
SAMPLE_CURRENTS = [300.,290.,269.,235.,204.,161.,133.,95.,70.,math.nan,math.nan,43.]

DESCRIPTION = r"""
### 实验八　热敏电阻温度计的设计与标定
原理、关系图、电桥图及设计公式见“计算过程”；表 8-1 的完整温度—电流测量对用于定标。

### 实验目的
利用 NTC 热敏电阻设计并制作“实验室室温～75 ℃”范围的温度测量系统实验电路，完成零点、量程校准和逐点定标。

### 实验内容与步骤
**1. 设计思路与仪器物理量选定**

利用 NTC 热敏电阻阻值随温度升高而减小的特性，以非平衡电桥把阻值变化转换为微安表电流。
室温时调平衡，使电流为 0；75 ℃时调节电源，使微安表满偏。桥臂电阻及电源估算按当前参数计算，实际校准值单独记录。

**2. 实验步骤（不少于 10 步）**

1. 检查仪器，记录电阻箱和电源的调节范围、微安表量程及内阻。
2. 测量室温，待热敏电阻与室温平衡后读取室温阻值。
3. 将热敏电阻放入 75 ℃环境，温度稳定后读取阻值。
4. 根据两端温度的阻值估算 R₁、R₂ 和 R₃，记录选定值并设置电阻箱。
5. 按满偏电流和电桥公式估算所需电源电压。
6. 断电连接电桥，确认各桥臂、微安表和电源接线。
7. 将热敏电阻置于室温，接通低电压电源，调节 R₃ 至微安表指零，记录校准 Rs。
8. 将热敏电阻置于 75 ℃环境，待稳定后缓慢调节 E 至满偏，记录校准电源电压。
9. 从 75 ℃开始降温，建议每降 5 ℃，待温度与示数稳定后同时记录温度和桥路电流，直至接近室温。
10. 用计算机绘制 I_g–T 定标曲线，标出拟合方程。
11. 将热敏电阻置于手心，稳定后记录自制温度计电流与玻璃温度计温度，用定标方程反算温度并计算相对误差。

**3. 注意事项**

- 断电连接和改接电路。
- 阻值及电流读数应待温度稳定，并同时记录温度。
- 调节电源时缓慢操作，不使微安表超过量程。
- 保持热敏电阻与被测物接触良好，并防止自热影响读数。

### 数据与定标方法
表 8-1 预列 75、70……25 ℃的定标温度，可按实际稳定读数修正。
默认样例包含 9 个定标点；30 ℃、25 ℃未测，电流留空。
末行为“手心”，温度栏记录玻璃温度计 T标，电流栏记录自制温度计手心电流；这行用于对比，不参加定标拟合。
采用最小二乘直线 $I_g=a t+b$，其中 $t$ 的单位为 ℃，$I_g$ 的单位为 μA。
实测点偏离直线的情况可在总结分析中讨论。
至少需要两个不同温度的完整测量对；只有两个点时只能确定直线，不能据此检验线性。
手心读数可由同一定标直线反算，必要时延长直线作外推。
相对误差严格按报告给出的摄氏温度表达式计算，T标=0 ℃时该式无定义。
玻璃温度计分度为 1 ℃，温度结果估读到 0.1 ℃；相对误差保留两位有效数字，中间运算保留保护位。

### 总结与分析
本实验利用 NTC 热敏电阻的负温度特性，通过非平衡电桥把温度引起的电阻变化转换为微安表电流变化，
再通过零点校准、满量程校准和逐点定标建立温度与电流的对应关系。
误差主要可能来自 NTC 与玻璃温度计的热惯性、水温分布不均匀、测温位置差异、仪表读数、电源稳定性及接线接触状态。
实际线性偏差和手心测温误差应依据本次完整数据讨论，数据未齐时不预写“精度良好”等实测结论。

### 实验感悟与体会（p.59，写作参考）
热敏电阻完成了温度到电阻的转换，电桥设计则需要兼顾灵敏度、线性和量程；零点校准、满偏校准与定标各有作用，不能互相替代。
设计、标定和修正贯穿着对误差的识别与控制，这种“传感—转换—校准”的方法也可用于其他传感测量。
以上仅作参考；本人实际遇到的问题、学到的方法及拟应用的场景，应结合真实操作补充。
"""

DISCUSSION = r"""
**（1）非平衡电桥有哪些应用，请详细说明。**

应用包括：①热敏电阻测温；②应变片测力与电子称重；③压阻式压力检测；④电阻式位移检测；⑤光敏电阻光强检测；⑥热导式气体成分检测。

**光敏电阻光强检测：** 将光敏电阻接入一个桥臂，在参考光照下调平衡。光照变化使光敏电阻阻值改变，电桥将其转换为电压或电流输出；
用已知光强或照度计对输出进行标定后，可检测光照变化，并将输出信号用于自动照明或遮挡报警。

**应变片称重：** 将应变片粘贴在弹性元件上，受力产生形变，使应变片电阻发生微小变化。
将其接入电桥后，电阻变化转换为差动电信号，经放大、采集并用已知载荷标定即可换算质量；合理配置多个应变片还可减小共同温度变化的影响。

**（2）列举几种其他类型的温度计，并说明其工作原理。**

- 液体玻璃温度计：利用液体热胀冷缩引起液柱长度变化测温。
- 铂电阻温度计：利用金属电阻随温度变化的规律测温。
- 热电偶温度计：利用两种导体构成回路时，测量端与参考端的温差产生热电势测温。
- 红外温度计：测量物体热辐射并结合发射率换算温度，可进行非接触测量。
"""


def records(inputs, key):
    return inputs.tables[key].set_index(NAME)[VALUE].to_numpy(dtype=float)


def round_hundreds(value):
    if not math.isfinite(value):
        return math.nan
    decimal = Decimal(str(value))
    with localcontext() as context:
        context.prec = max(28,decimal.adjusted()+4)
        return float(decimal.quantize(Decimal('1E2'), rounding=ROUND_HALF_UP))


def calibration_rows(frame):
    return frame.loc[frame[POINT].astype(str) != '手心'] if POINT in frame else frame


def bridge_current(r1, r2, rt, rs, rg, voltage):
    """正方向为 R2/Rs 中点经微安表流向 R1/Rt 中点；返回 A。"""
    if not all(math.isfinite(v) for v in (r1, r2, rt, rs, rg, voltage)):
        return math.nan
    denominator = rg * (r1 + rt) * (r2 + rs) + r1 * rt * (r2 + rs) + r2 * rs * (r1 + rt)
    return (r1 * rs - r2 * rt) * voltage / denominator if denominator > 0 else math.nan


def fit_calibration(frame):
    valid = calibration_rows(frame).dropna(subset=[TEMP, CURRENT])
    fit = dict(n=len(valid), slope=math.nan, intercept=math.nan, error=None,
               temperature_range=None, current_range=None, curve_x=(), curve_y=())
    if len(valid) < 2 or valid[TEMP].nunique() < 2:
        fit['error'] = '至少需要两个不同温度的完整测量对，当前不能确定定标方程。'
        return fit
    x, y = valid[TEMP].to_numpy(dtype=float), valid[CURRENT].to_numpy(dtype=float)
    with np.errstate(over='ignore', invalid='ignore', divide='ignore'):
        x0, y0 = float(np.mean(x)), float(np.mean(y))
        sxy, sxx = float(np.dot(x-x0,y-y0)), float(np.dot(x-x0,x-x0))
        slope = sxy / sxx if sxx > 0 else math.nan
        intercept = y0 - slope*x0
    if not all(math.isfinite(v) for v in (slope, intercept, sxx, sxy, x0, y0)):
        fit['error'] = '当前数值尺度无法稳定拟合，请核对记录。'
        return fit
    xx = np.linspace(float(x.min()), float(x.max()), 200)
    fit.update(slope=slope, intercept=intercept, x_mean=x0, y_mean=y0,
               sum_x=float(x.sum()), sum_y=float(y.sum()),
               sxx=sxx, sxy=sxy,
               temperature_range=(float(x.min()), float(x.max())),
               current_range=(float(y.min()), float(y.max())), curve_x=xx, curve_y=slope*xx+intercept)
    return fit


def validate(inputs):
    issues = []
    for key, positive_rows, nonnegative_rows, temperature_rows in [
        (ENV, (1, 3, 4, 5), (2,), (0,)), (DESIGN, (0, 1, 2, 3), (), ()),
        (CAL, (0, 1), (), ()),
    ]:
        values = records(inputs, key)
        for row in positive_rows:
            if math.isfinite(values[row]) and values[row] <= 0:
                issues.append(ValidationIssue('电阻、电源电压及量程上限须大于 0。', key, row, VALUE))
        for row in nonnegative_rows:
            if math.isfinite(values[row]) and values[row] < 0:
                issues.append(ValidationIssue('量程下限不能小于 0。', key, row, VALUE))
        for row in temperature_rows:
            if math.isfinite(values[row]) and values[row] <= -273.15:
                issues.append(ValidationIssue('温度须高于绝对零度。', key, row, VALUE))
    env = records(inputs, ENV)
    if math.isfinite(env[2]) and math.isfinite(env[3]) and env[2] >= env[3]:
        issues.append(ValidationIssue('量程下限须小于上限。', ENV, 2, VALUE))
    scan = inputs.tables[SCAN]
    for row in scan.index[scan[TEMP].notna() & (scan[TEMP] <= -273.15)]:
        issues.append(ValidationIssue('温度须高于绝对零度。', SCAN, int(row), TEMP))
    return issues


def compute(inputs):
    room, rg, low, high, rroom, r75 = records(inputs, ENV)
    r1, r2, r3, e_record = records(inputs, DESIGN)
    rs, e_cal = records(inputs, CAL)
    t_standard, palm_current = inputs.tables[SCAN].iloc[-1][[TEMP,CURRENT]].to_numpy(dtype=float)
    notes = []
    r_mean = (rroom + r75) / 2
    r_selected = round_hundreds(r_mean)
    if math.isfinite(r_selected) and r_selected <= 0:
        notes.append('桥臂平均值按百位取整后不足 100 Ω，不能将 0 Ω 作为桥臂，请另选正阻值并记录。')
        r_selected = math.nan
    unit_current = bridge_current(r1, r2, r75, r3, rg, 1.)
    e_required = high * 1e-6 / unit_current if math.isfinite(unit_current) and unit_current > 0 and math.isfinite(high) else math.nan
    balance_rs = r2 * rroom / r1 if math.isfinite(r1) and r1 > 0 else math.nan
    fit = fit_calibration(inputs.tables[SCAN])
    if fit['error']:
        notes.append(fit['error'])
    elif fit['n'] == 2:
        notes.append('定标仅有两个有效点，可确定直线但尚不能检验线性。')
    if math.isfinite(fit['slope']) and fit['slope'] < 0:
        notes.append('定标斜率为负，请核对电流方向、记录及接线。')
    if math.isfinite(rroom) and math.isfinite(r75) and rroom <= r75:
        notes.append('室温与 75 ℃的阻值未体现 NTC 阻值随升温减小的关系，请核对。')
    if math.isfinite(room) and room >= HIGH:
        notes.append('室温不低于 75 ℃，请核对实验温区。')
    for key, currents in [(SCAN, inputs.tables[SCAN][CURRENT])]:
        if math.isfinite(low) and math.isfinite(high) and ((currents < low) | (currents > high)).any():
            notes.append(f'{key}：存在超出记录量程的电流，请核对。')
    missing_pairs = calibration_rows(inputs.tables[SCAN])[[TEMP, CURRENT]].notna().sum(axis=1).eq(1).sum()
    if missing_pairs:
        notes.append(f'{missing_pairs} 个测量点只填写了温度或电流，未参与拟合。')
    palm_temperature, relative_error = math.nan, math.nan
    palm_extrapolated = False
    palm_error = None
    if not math.isfinite(palm_current):
        palm_error = '手心电流未填写，暂不能由定标曲线换算温度。'
    elif fit['error']:
        palm_error = '定标方程尚不可用，暂不能换算手心温度。'
    elif fit['slope'] == 0:
        palm_error = '定标直线斜率为 0，电流不能唯一反算温度。'
    else:
        candidate = (palm_current - fit['intercept']) / fit['slope']
        lower, upper = fit['temperature_range']
        tolerance = 1e-9 * max(1., abs(lower), abs(upper))
        if not math.isfinite(candidate):
            palm_error = '当前记录不能得到有限的反算温度，请核对数值。'
        else:
            palm_temperature = candidate
            palm_extrapolated = (not lower-tolerance <= candidate <= upper+tolerance
                                 or not fit['current_range'][0] <= palm_current <= fit['current_range'][1])
            if palm_extrapolated:
                fit['curve_x'] = np.linspace(min(lower,candidate),max(upper,candidate),200)
                fit['curve_y'] = fit['slope']*fit['curve_x']+fit['intercept']
    if math.isfinite(palm_temperature) and math.isfinite(t_standard) and t_standard > 0:
        relative_error = abs(palm_temperature-t_standard) / t_standard * 100
    if math.isfinite(t_standard) and t_standard <= 0:
        notes.append('T标≤0 ℃，本实验给定的相对误差表达式不适用，请核对。')
    if math.isfinite(e_required) and math.isfinite(e_record):
        notes.append(f'当前桥臂参数的满偏电压估算为 {e_required:.3g} V；实验使用零点和满偏校准后的 Rs、E。')
    design_table = pd.DataFrame({'计算项': ['桥臂平均值 (R室+R75)/2', 'R₁=R₂建议选取（保留百位）', '室温平衡所需 Rs', '75 ℃满偏所需电压'],
                                 '计算值': [r_mean, r_selected, balance_rs, e_required], '单位': ['Ω', 'Ω', 'Ω', 'V']})
    fit_table = pd.DataFrame({'参数': ['a', 'b'], '数值': [fit['slope'], fit['intercept']], '单位': ['μA/℃', 'μA']})
    palm_table = pd.DataFrame({'校准 Rs / Ω': [rs], '校准 E / V': [e_cal],
                              'T标 / ℃': [t_standard], '手心电流 / μA': [palm_current],
                              'T计 / ℃': [palm_temperature], '相对误差 Er / %': [relative_error],
                              '取值方式': ['线性外推' if palm_extrapolated else '范围内反算' if math.isfinite(palm_temperature) else '—']})
    values = dict(room=room, rg=rg, low=low, high=high, rroom=rroom, r75=r75, r1=r1, r2=r2, r3=r3,
                  e_record=e_record, rs=rs, e_cal=e_cal, r_mean=r_mean, r_selected=r_selected, balance_rs=balance_rs,
                  e_required=e_required, fit=fit, palm_temperature=palm_temperature,
                  relative_error=relative_error, t_standard=t_standard, palm_current=palm_current, palm_error=palm_error,
                  palm_extrapolated=palm_extrapolated)
    return ResultBundle({SCAN: inputs.tables[SCAN].copy(), '设计计算与选定': design_table,
                         '定标直线参数': fit_table, '手心温度与相对误差': palm_table}, values, notes,
                        (Metric('桥臂建议值（保留百位）', number(r_selected), 'Ω'),
                         Metric('满偏电源估算（两位）', number(e_required, 2, trailing=True), 'V'),
                         Metric('手心温度 T计（外推）' if palm_extrapolated else '手心温度 T计', f'{palm_temperature:.1f}' if math.isfinite(palm_temperature) else '—', '℃'),
                         Metric('相对误差 Er', number(relative_error, 2, trailing=True), '%')))


def number(value, digits=6, *, trailing=False):
    text = significant(value, digits, trailing=trailing)
    if 'e' in text:
        mantissa, exponent = text.split('e')
        return mantissa + '×10' + str(int(exponent)).translate(str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹'))
    return text


def format_tables(inputs, result):
    tables = []
    for title, frame in result.tables.items():
        display = frame.copy()
        for column in display:
            if column == POINT:
                continue
            if pd.api.types.is_numeric_dtype(display[column]):
                if column == 'T计 / ℃':
                    display[column] = display[column].map(lambda v:f'{v:.1f}' if math.isfinite(v) else '—')
                elif column == '相对误差 Er / %':
                    display[column] = display[column].map(lambda v:number(v,2,trailing=True))
                else:
                    display[column] = display[column].map(number)
        tables.append(DisplayTable(title, display))
    return tables


def explain(inputs, result):
    r = result.values
    doc = Explanation()
    doc.markdown('**一、实验原理**')
    doc.markdown('**1. NTC 热敏电阻及其物理量**：升温使载流子浓度增大，电阻减小。下图为阻温关系示意。')
    doc.latex(r'R(T)=R(T_0)\exp\!\left[B\left(\frac1T-\frac1{T_0}\right)\right],\qquad T=t+273.15\ \mathrm K')
    doc.latex(r'\ln R=\frac BT+\left(\ln R_0-\frac B{T_0}\right),\quad B=\frac{\ln R(T_1)-\ln R(T_2)}{1/T_1-1/T_2}')
    doc.markdown('B 是表征热敏电阻阻温特性的材料常数，单位 K；ln R–1/T 直线的斜率为 B。')
    doc.latex(r'\alpha_T=\frac1R\frac{\mathrm dR}{\mathrm dT}=-\frac B{T^2}<0')
    doc.markdown('αT 表示温度每变化 1 K 时电阻的相对变化率，单位 K⁻¹；B>0 时为负温度系数，绝对值随绝对温度升高而减小。')
    from core.fonts import report_fonts
    ntc, bridge = principle_diagrams(tuple(report_fonts().families))
    doc.image(ntc)
    doc.markdown('**2. 非平衡电桥测量原理**：上支路为 R₁、RT，下支路为 R₂、Rs；微安表跨接两支路中点。取微安表电流从下中点 B 流向上中点 A 为正。')
    doc.image(bridge)
    doc.latex(r'\frac{V_A-E}{R_1}+\frac{V_A}{R_T}+\frac{V_A-V_B}{R_g}=0,\qquad\frac{V_B-E}{R_2}+\frac{V_B}{R_s}+\frac{V_B-V_A}{R_g}=0')
    doc.latex(r'I_g=\frac{V_B-V_A}{R_g}=\frac{E(R_1R_s-R_2R_T)}{R_g(R_1+R_T)(R_2+R_s)+R_1R_T(R_2+R_s)+R_2R_s(R_1+R_T)}')
    doc.latex(r'I_g=0\iff R_1R_s=R_2R_T\iff\frac{R_1}{R_2}=\frac{R_T}{R_s}')
    doc.markdown('按室温平衡后，升温使 RT 减小，电流从 B 流向 A；降温时正向电流减小，低于平衡温度后可能反向。此方向以图示正方向为准。')
    doc.markdown('**二、设计选定与计算**')
    doc.latex(r'R_1=R_2\approx R=\frac{R_{\rm 室}+R_{75}}2,\qquad R_s=\frac{R_2}{R_1}R_{\rm 室}')
    if math.isfinite(r['r_mean']) and math.isfinite(r['r_selected']):
        doc.latex(rf'R=\frac{{{r["rroom"]:g}+{r["r75"]:g}}}2={r["r_mean"]:.6g}\ \Omega\ \longrightarrow\ R_1=R_2={r["r_selected"]:g}\ \Omega\quad\text{{（保留百位）}}')
    else:
        doc.info('室温与 75 ℃阻值齐全、且百位取整能选出正阻值时，显示桥臂建议值。')
    doc.markdown('据平均值选择桥臂电阻，并记录实际设置的 R₁、R₂。')
    if math.isfinite(r['balance_rs']):
        doc.latex(rf'R_{{s,\rm 平衡}}=\frac{{{r["r2"]:g}}}{{{r["r1"]:g}}}\times {r["rroom"]:g}\approx {r["balance_rs"]:.6g}\ \Omega')
    doc.latex(r'E_{\rm 满偏}=I_{g\max}\frac{R_g(R_1+R_{75})(R_2+R_3)+R_1R_{75}(R_2+R_3)+R_2R_3(R_1+R_{75})}{R_1R_3-R_2R_{75}}')
    if math.isfinite(r['e_required']):
        doc.latex(rf'I_{{g\max}}={r["high"]:g}\ \mu\mathrm A={r["high"]:g}\times10^{{-6}}\ \mathrm A')
        a,b,c,d,g = (r[k] for k in ('r1','r2','r75','r3','rg'))
        doc.latex(rf'E_{{\rm 满偏}}={r["high"]:g}\times10^{{-6}}\frac{{{g:g}({a:g}+{c:g})({b:g}+{d:g})+{a:g}\times{c:g}({b:g}+{d:g})+{b:g}\times{d:g}({a:g}+{c:g})}}{{{a:g}\times{d:g}-{b:g}\times{c:g}}}\approx {latex_number(r["e_required"],2,trailing=True)}\ \mathrm V')
    else:
        doc.info('补全量程、内阻与设计桥臂值，并使升温对应正向电流后，才能估算满偏电压。')
    doc.caption('R₁、R₂按百位四舍五入；电源估算展示两位有效数字，代入保留保护位。校准 Rs、E 应分别记录零点、满偏校准后的实测值。')
    doc.markdown('**三、数据处理（1）：定标曲线与拟合方程**')
    doc.latex(r'I_g=a t+b,\quad a=\frac{\sum_i(t_i-\bar t)(I_i-\bar I)}{\sum_i(t_i-\bar t)^2},\quad b=\bar I-a\bar t')
    fit = r['fit']
    if fit['error']:
        doc.info(fit['error'])
    else:
        doc.caption(f'仅使用 {fit["n"]} 个完整测量对；温度使用 ℃，电流使用 μA。系数显示 6 位有效数字，计算不使用舍入后的系数。')
        doc.latex(rf'\bar t=\frac{{{fit["sum_x"]:.8g}}}{{{fit["n"]}}}={fit["x_mean"]:.8g},\quad\bar I=\frac{{{fit["sum_y"]:.8g}}}{{{fit["n"]}}}={fit["y_mean"]:.8g}\ \mu\mathrm A')
        doc.latex(rf'a=\frac{{{fit["sxy"]:.8g}}}{{{fit["sxx"]:.8g}}}\approx{fit["slope"]:.6g}\ \mu\mathrm A/\!^\circ\mathrm C,\quad b={fit["y_mean"]:.8g}-({fit["slope"]:.8g})\times {fit["x_mean"]:.8g}\approx{fit["intercept"]:.6g}\ \mu\mathrm A')
        doc.latex(rf'I_g\approx({fit["slope"]:.6g})t+({fit["intercept"]:.6g})\quad[I_g:\mu\mathrm A,\ t:^\circ\mathrm C]')
    doc.markdown('**四、数据处理（2）：手心温度与相对误差**')
    doc.latex(r't_{\rm 计}=\frac{I_{\rm 手心}-b}{a},\qquad E_r=\frac{|t_{\rm 计}-t_{\rm 标}|}{t_{\rm 标}}\times100\%')
    if r['palm_error']:
        doc.info(r['palm_error'])
    else:
        doc.latex(rf't_{{\rm 计}}=\frac{{{r["palm_current"]:g}-({fit["intercept"]:.8g})}}{{{fit["slope"]:.8g}}}\approx{r["palm_temperature"]:.1f}\ ^\circ\mathrm C')
    if math.isfinite(r['relative_error']):
        doc.latex(rf'E_r=\frac{{|{r["palm_temperature"]:.8g}-{r["t_standard"]:g}|}}{{{r["t_standard"]:g}}}\times100\%\approx {latex_number(r["relative_error"],2,trailing=True)}\%')
    else:
        doc.info('定标、手心电流和正的玻璃温度计温度齐全后计算相对误差。')
    doc.caption('玻璃温度计分度 1 ℃，温度结果估读到 0.1 ℃；相对误差保留两位有效数字。误差使用未舍入温度计算，CSV 保留复算精度。')
    return doc


@lru_cache(maxsize=2)
def principle_diagrams(font_families):
    """只缓存与用户数据无关的原理示意 SVG；用字形路径保证跨环境显示。"""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.patches import Rectangle, Circle
    from core.fonts import report_style
    images = []
    with report_style():
        figure = Figure(figsize=(5.8,2.8),layout='constrained');FigureCanvasAgg(figure)
        ax = figure.subplots()
        x = np.linspace(.12,1,200)
        ax.plot(x,np.exp(.4/x-3),color='#0969DA')
        ax.set(xlabel='绝对温度 T / K',ylabel='热敏电阻 R / Ω',title='NTC 阻温关系示意（无数值刻度）')
        ax.set_xticks([]);ax.set_yticks([]);ax.spines[['top','right']].set_visible(False)
        buffer=BytesIO();figure.savefig(buffer,format='svg',bbox_inches='tight');images.append(buffer.getvalue().decode());figure.clear()
        figure = Figure(figsize=(5.8,3.3),layout='constrained');FigureCanvasAgg(figure)
        ax = figure.subplots();ax.set(xlim=(-.8,4.8),ylim=(-1.2,3));ax.axis('off')
        def wire(x,y):ax.plot(x,y,color='#1F2328',linewidth=1.5)
        wire([0,0,4,4],[0,2,2,0]);wire([0,4],[0,0]);wire([0,0,1.8], [0,-.8,-.8]);wire([2.2,4,4],[-.8,-.8,0])
        wire([1.8,1.8],[-1,-.6]);wire([2.2,2.2],[-.95,-.65]);ax.text(2,-1.15,'E',ha='center')
        for x,y,label in [(.8,2,'R₁'),(3.2,2,'RT'),(.8,0,'R₂'),(3.2,0,'Rs')]:
            ax.add_patch(Rectangle((x-.35,y-.15),.7,.3,facecolor='white',edgecolor='#1F2328',zorder=3))
            ax.text(x,y+.28,label,ha='center')
        wire([2,2],[0,2]);ax.add_patch(Circle((2,1),.24,facecolor='white',edgecolor='#1F2328',zorder=4))
        ax.add_patch(Rectangle((1.9,1.35),.2,.4,facecolor='white',edgecolor='#1F2328',zorder=4))
        ax.text(1.75,1.55,'Rg',ha='right',va='center')
        ax.text(2,1,'G',ha='center',va='center',zorder=5);ax.text(2.12,2.1,'A');ax.text(2.12,-.25,'B')
        ax.annotate('Ig > 0',xy=(2.65,1.55),xytext=(2.65,.5),arrowprops={'arrowstyle':'->'},ha='center')
        ax.text(-.3,1,'+E',ha='center');ax.text(4.3,1,'0',ha='center');ax.set_title('非平衡电桥连接与正电流方向')
        buffer=BytesIO();figure.savefig(buffer,format='svg',bbox_inches='tight');images.append(buffer.getvalue().decode());figure.clear()
    return tuple(images)


def build_plot(inputs, result):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from core.fonts import report_style
    fit = result.values['fit']
    with report_style():
        figure=Figure(figsize=(8,5.4),layout='constrained');FigureCanvasAgg(figure)
        ax=figure.subplots()
        valid=calibration_rows(inputs.tables[SCAN]).dropna(subset=[TEMP,CURRENT])
        ax.scatter(valid[TEMP],valid[CURRENT],s=35,color='#0969DA',label='实测定标点',zorder=3)
        if not fit['error']:
            ax.plot(fit['curve_x'],fit['curve_y'],color='#D55E00',linestyle='--',label='最小二乘直线')
            if result.values['palm_extrapolated']:
                ax.scatter([result.values['palm_temperature']],[result.values['palm_current']],color='#6F42C1',marker='x',s=60,label='手心换算',zorder=4)
            ax.text(.03,.97,f'Ig = ({fit["slope"]:.6g}) t + ({fit["intercept"]:.6g})\nIg: μA; t: ℃',transform=ax.transAxes,va='top',bbox={'facecolor':'white','edgecolor':'none','alpha':.85})
        else:
            ax.text(.03,.97,fit['error'],transform=ax.transAxes,va='top',wrap=True)
        ax.set(xlabel='温度 t / ℃',ylabel='桥路电流 Ig / μA',title='热敏电阻温度计的定标曲线')
        ax.legend(loc='lower right');ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False);ax.margins(.08)
    return figure


def get_spec():
    def parameter_table(key, rows):
        frame=pd.DataFrame(rows,columns=[NAME,UNIT,VALUE])
        return TableSpec(key,key,frame,(ColumnSpec(NAME,'text'),ColumnSpec(UNIT,'text'),ColumnSpec(VALUE)),(NAME,UNIT))
    scan=pd.DataFrame({POINT:[*map(str,range(1,12)),'手心'],TEMP:[*np.arange(75.,24.,-5.),32.],CURRENT:SAMPLE_CURRENTS})
    return ExperimentSpec(ID,'热敏电阻温度计的设计与标定','下册',8,
        '记录设计与校准参数，用实测电流—温度数据定标，并换算手心温度和相对误差。',
        DESCRIPTION,(parameter_table(ENV,ENV_ROWS),parameter_table(DESIGN,DESIGN_ROWS),parameter_table(CAL,CAL_ROWS),
                     TableSpec(SCAN,SCAN,scan,(ColumnSpec(POINT,'text'),ColumnSpec(TEMP),ColumnSpec(CURRENT)),(POINT,),
                               help='30 ℃、25 ℃未测，电流留空。末行“手心”的温度栏为玻璃温度计 T标，该行不参与拟合。')),
        (),compute,explain,validate=validate,format_tables=format_tables,build_plot=build_plot,plot_kind='matplotlib',
        plot_caption='完整定标数据对用于最小二乘直线拟合；手心点用于温度换算。',discussion=DISCUSSION)
