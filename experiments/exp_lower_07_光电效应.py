"""下册实验七：截止电压拟合与光电管伏安特性。"""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.fonts import report_style
from core.formatting import latex_number, significant
from core.models import ColumnSpec, DisplayTable, ExperimentSpec, Explanation, ParameterSpec, ResultBundle, TableSpec

WAVELENGTH = '滤色片透射波长 λ / nm'
FREQUENCY = '频率 ν / (10¹⁴ Hz)'
STOP = '截止电压 U₀ / V'
VOLTAGE = 'Uₐₖ / V'
READING = '电流读数 I'
CURRENT = '电流 I / A'
STOP_TABLE = '表 7-1 U₀–ν 关系'
APERTURES = (4, 2)
# 表 7-2 按照片中的记录顺序展开，两组使用相同的电压点与电流单位。
IV_VOLTAGES = (
    -1.2, -1.0, -.8, -.6, -.4, -.2, 0, .2, .4, .6,
    .8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 4, 6, 8,
    10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
)
IV_READINGS = {
    4: (
        .2, 1.0, 2.0, 2.8, 4.1, 5.3, 6.7, 8.9, 10.7, 12.6,
        14.7, 16.9, 19.4, 21.2, 23.7, 26.2, 28.9, 51.3, 64.7, 77.5,
        85.7, 93.9, 98.5, 106.4, 112.3, 115.3, 122.4, 127.2, 130.1, 134.4, 137.5,
    ),
    2: (
        .2, .4, .7, 1.0, 1.2, 1.5, 2.1, 2.8, 3.2, 3.8,
        4.4, 5.2, 5.7, 6.3, 7.3, 7.7, 8.4, 15.3, 19.3, 23.8,
        26.0, 28.3, 30.3, 31.9, 33.6, 35.3, 36.9, 38.1, 39.4, 40.3, 41.3,
    ),
}
ELECTRON_CHARGE = -1.602e-19
PLANCK_REFERENCE = 6.626e-34
FREQUENCY_UNIT = 1e14


def iv_table(aperture):
    return f'表 7-2 I–Uₐₖ 关系（{aperture} mm）'


@dataclass(frozen=True)
class Fit:
    mean_x: float
    mean_y: float
    sxx: float
    sxy: float
    slope_scaled: float
    intercept: float
    slope: float
    planck: float
    error_pct: float


def fit_stopping_voltage(points):
    if len(points) < 2 or points[FREQUENCY].nunique() < 2:
        return None
    x, y = points[FREQUENCY].to_numpy(), points[STOP].to_numpy()
    mean_x, mean_y = float(x.mean()), float(y.mean())
    dx, dy = x - mean_x, y - mean_y
    sxx, sxy = float(dx @ dx), float(dx @ dy)
    slope_scaled = sxy / sxx
    slope = slope_scaled / FREQUENCY_UNIT
    planck = ELECTRON_CHARGE * slope
    return Fit(mean_x, mean_y, sxx, sxy, slope_scaled, mean_y - slope_scaled * mean_x,
               slope, planck, abs(planck - PLANCK_REFERENCE) / PLANCK_REFERENCE * 100)


def compute(inputs):
    stop = inputs.tables[STOP_TABLE].dropna(subset=[STOP]).copy()
    fit = fit_stopping_voltage(stop)
    results, curves, notes = {}, {}, []
    if fit is None:
        notes.append('至少填写两种不同频率的截止电压，才能拟合斜率。')
    elif fit.slope >= 0:
        notes.append('拟合斜率非负；请核对截止电压是否按带符号的反向电压录入。')
    results['普朗克常数测量结果'] = pd.DataFrame(
        [[fit.slope, fit.planck, fit.error_pct] if fit else [np.nan] * 3],
        columns=['拟合斜率 k / (V/Hz)', '普朗克常数 h / (J·s)', '相对误差 Eᵣ / %'],
    )
    units = {a: inputs.parameters[f'current_unit_{a}'] for a in APERTURES}
    for aperture, unit in units.items():
        frame = inputs.tables[iv_table(aperture)].copy()
        frame[CURRENT] = frame[READING] * unit if unit is not None else np.nan
        if unit is None and frame[READING].notna().any():
            notes.append(f'{aperture} mm 组缺少电流记录单位，暂不能换算。')
        results[iv_table(aperture) + ' · 电流换算'] = frame
        curves[aperture] = frame

    # 只比较两组均有唯一测量值的同一电压，不补点、不跨缺测插值。
    measured = [curves[a].dropna(subset=[VOLTAGE, CURRENT]).drop_duplicates(VOLTAGE, keep=False)
                for a in APERTURES]
    shared = measured[0].merge(measured[1], on=VOLTAGE, suffixes=('_4', '_2'))
    comparison = None
    if not shared.empty:
        row = shared.loc[shared[VOLTAGE].idxmax()]
        comparison = (row[VOLTAGE], row[CURRENT + '_4'], row[CURRENT + '_2'])
    return ResultBundle(tables=results, values={
        'stop': stop, 'fit': fit, 'curves': curves, 'units': units, 'comparison': comparison,
    }, notes=notes)


def scientific_text(value, digits):
    text = significant(value, digits, trailing=True)
    if 'e' not in text:
        return text
    mantissa, exponent = text.split('e')
    superscripts = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')
    return f'{mantissa}×10{str(int(exponent)).translate(superscripts)}'


def format_tables(inputs, result):
    tables = []
    for title, raw in result.tables.items():
        frame = raw.copy()
        for column in frame.columns:
            digits = 3 if column == '相对误差 Eᵣ / %' else 4 if column.startswith(('拟合斜率', '普朗克常数')) else 6
            frame[column] = frame[column].map(lambda v: scientific_text(v, digits))
        tables.append(DisplayTable(title, frame))
    return tables


def explain(inputs, result):
    doc = Explanation()
    doc.markdown('### （1）截止电压与频率')
    doc.markdown('**① 绘制关系图并拟合直线。** 令 $x=\\nu/(10^{14}\\,\\mathrm{Hz})$，'
                 '先拟合 $U_0=ax+b$，再将斜率换算为以 Hz 为横坐标的 $k$。')
    doc.latex(r'a=\frac{\sum_i(x_i-\bar{x})(U_{0,i}-\bar{U}_0)}{\sum_i(x_i-\bar{x})^2},'
              r'\qquad b=\bar{U}_0-a\bar{x},\qquad k=\frac{a}{10^{14}\,\mathrm{Hz}}')
    fit = result.values['fit']
    if fit is None:
        doc.info('至少需要两组不同频率的有效截止电压。')
    else:
        a = latex_number(fit.slope_scaled, 8)
        b = latex_number(fit.intercept, 8)
        k = latex_number(fit.slope, 4, trailing=True)
        doc.markdown(f"使用表 7-1 的 {len(result.values['stop'])} 组有效数据。")
        doc.latex(fr'a\approx\frac{{{latex_number(fit.sxy, 9)}}}{{{latex_number(fit.sxx, 9)}}}'
                  fr'\approx {a}\,\mathrm{{V}}')
        doc.latex(fr'b\approx {latex_number(fit.mean_y, 9)}'
                  fr'-\left({a}\right)\times {latex_number(fit.mean_x, 9)}\approx {b}\,\mathrm{{V}}')
        doc.latex(fr'k\approx\frac{{{a}\,\mathrm{{V}}}}{{10^{{14}}\,\mathrm{{Hz}}}}'
                  fr'\approx {k}\,\mathrm{{V/Hz}}')

    doc.markdown('**② 计算普朗克常数及相对误差。**')
    doc.latex(r'h=ek,\qquad E_r=\frac{|h-h_0|}{h_0}\times100\%')
    doc.latex(r'e=-1.602\times10^{-19}\,\mathrm{C},\qquad h_0=6.626\times10^{-34}\,\mathrm{J\cdot s}')
    if fit is not None:
        h = latex_number(fit.planck, 4, trailing=True)
        err = latex_number(fit.error_pct, 3, trailing=True)
        h_work = latex_number(fit.planck, 9)
        doc.latex(fr'h\approx (-1.602\times10^{{-19}}\,\mathrm{{C}})\times'
                  fr'\left({latex_number(fit.slope, 9)}\,\mathrm{{V/Hz}}\right)'
                  fr'\approx {h}\,\mathrm{{J\cdot s}}')
        doc.latex(fr'E_r\approx\frac{{|\left({h_work}\right)-6.626\times10^{{-34}}|}}'
                  fr'{{6.626\times10^{{-34}}}}\times100\%\approx {err}\%')
        doc.caption('结果展示保留保护位供核算；报告最终取位应结合实际读数精度和不确定度。')

    doc.markdown('### （2）两种光阑的伏安特性')
    doc.markdown('设 $q$ 为每一读数单位对应的电流，单位为 A。')
    doc.latex(r'I=I_{\mathrm{read}}\,q')
    for aperture, frame in result.values['curves'].items():
        unit = result.values['units'][aperture]
        if unit is not None:
            doc.markdown(f'**{aperture} mm 光阑**')
            doc.latex(fr'I=I_{{\mathrm{{read}}}}\times{latex_number(unit, 6)}\,\mathrm{{A}}')
            pairs = frame.dropna(subset=[VOLTAGE, CURRENT])
            if not pairs.empty:
                row = pairs.iloc[0]
                doc.markdown(f'以 $U_{{AK}}={row[VOLTAGE]:g}\\,\\mathrm{{V}}$ 的测量点为例：')
                doc.latex(fr'I\approx {latex_number(row[READING], 6)}\times{latex_number(unit, 6)}'
                          fr'\,\mathrm{{A}}\approx {latex_number(row[CURRENT], 6)}\,\mathrm{{A}}')
    comparison = result.values['comparison']
    if comparison is None:
        doc.caption('两组暂无可直接比较的同电压测量点，可在图中对照各自已测区间。')
    else:
        voltage, i4, i2 = comparison
        doc.markdown(f'在两组均有记录的最高电压 {voltage:g} V 处，4 mm、2 mm 光阑的电流分别为 '
                     f'{scientific_text(i4, 6)} A、{scientific_text(i2, 6)} A。'
                     '是否进入饱和区，应结合曲线末端是否趋于平缓判断。')
    return doc


def build_plot(inputs, result):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    with report_style():
        figure = Figure(figsize=(8, 8), layout='constrained')
        FigureCanvasAgg(figure)
        stop_ax, iv_ax = figure.subplots(2, 1)
        stop = result.values['stop']
        fit = result.values['fit']
        if not stop.empty:
            stop_ax.scatter(stop[FREQUENCY], stop[STOP], label='实测点', zorder=3)
        if fit is not None:
            x = stop[FREQUENCY].to_numpy()
            stop_ax.plot([x.min(), x.max()], fit.slope_scaled * np.array([x.min(), x.max()]) + fit.intercept,
                         '--', color='#D55E00', label='最小二乘拟合')
        stop_ax.set(title='截止电压与频率', xlabel='频率 ν / (10¹⁴ Hz)',
                    ylabel='截止电压 U₀ / V')

        for aperture, marker, line, color in ((4, 'o', '-', '#0072B2'), (2, 's', '--', '#D55E00')):
            frame = result.values['curves'][aperture]
            if frame.dropna(subset=[VOLTAGE, CURRENT]).empty:
                continue
            iv_ax.plot(frame[VOLTAGE], frame[CURRENT], linestyle=line, marker=marker,
                       markersize=4, color=color, label=f'{aperture} mm 光阑')
        iv_ax.set(title='光电管伏安特性（435.8 nm）', xlabel='阳极与阴极间电压 Uₐₖ / V',
                  ylabel='光电流 I / A')
        iv_ax.ticklabel_format(axis='y', style='sci', scilimits=(0, 0), useMathText=True)
        for ax in (stop_ax, iv_ax):
            ax.grid(alpha=.22)
            if ax.has_data():
                ax.legend(loc='best')
            else:
                ax.text(.5, .5, '暂无有效测量点', ha='center', va='center', transform=ax.transAxes)
        return figure


DESCRIPTION = r'''### 实验原理
单色光照射光电阴极时，若光子能量达到阴极逸出功，电子可从阴极逸出。以阳极相对阴极的反向截止电压为 $U_0$，电子电荷为 $e<0$，爱因斯坦光电方程可写为 $eU_0=h\nu-W$。因此 $U_0$ 对 $\nu$ 的拟合斜率为 $h/e$。

### 数据记录
- **表 7-1：** 光阑孔径 4 mm，电流量程 $10^{-13}$ A。按表列波长记录带符号的截止电压。
- **表 7-2：** 使用 435.8 nm 滤色片，保持距离不变，分别记录 4 mm 和 2 mm 光阑下的 $U_{AK}$ 与电流。切换光阑和量程后重新调零；电流读数按实际记录单位换算为 A。
'''

DISCUSSION = r'''**（1）什么是截止频率？**

截止频率是能使光电阴极发生光电发射的最低入射光频率，满足 $\nu_0=W/h$。低于该频率时，单个光子的能量不足以使电子逸出。

**（2）改变光电管的照度对伏安特性曲线有何影响？**

波长不变时，增大照度通常会增大光电流和饱和电流；光电子的最大初动能由频率决定，理想情况下截止电压基本不变。

### 分析与讨论

比较曲线前，应先将两档电流读数换算为同一单位。可对照相同电压下的电流，以及两组曲线是否在正向电压较高时趋于平缓。零点偏移和杂散光会影响小电流读数，尤其是截止附近的判断。
'''


def get_spec():
    stop = pd.DataFrame({
        WAVELENGTH: [365.0, 404.7, 435.8, 546.1, 577.0],
        FREQUENCY: [8.214, 7.407, 6.879, 5.490, 5.196],
        STOP: [-1.783, -1.426, -1.246, -.678, -.560],
    })
    tables = [TableSpec(
        STOP_TABLE, STOP_TABLE, stop,
        (ColumnSpec(WAVELENGTH, format='%.1f'), ColumnSpec(FREQUENCY, format='%.3f'),
         ColumnSpec(STOP, format='%.3f')),
        fixed_columns=(WAVELENGTH, FREQUENCY),
        help='光阑孔径 4 mm；电流量程 10⁻¹³ A。截止电压按仪表带符号读数录入。',
    )]
    for aperture in APERTURES:
        name = iv_table(aperture)
        frame = pd.DataFrame({VOLTAGE: IV_VOLTAGES, READING: IV_READINGS[aperture]}).reindex(range(40))
        tables.append(TableSpec(
            name, name, frame, (ColumnSpec(VOLTAGE), ColumnSpec(READING, format='%.1f')),
            help='按原记录顺序录入，每行一组电压和电流。电流读数以该组所填的记录单位为基准。',
        ))
    parameters = (
        ParameterSpec('distance_stop', '表 7-1 距离 L / mm', 400.0, positive=True, optional=True, step=1.0),
        ParameterSpec('distance_iv', '表 7-2 距离 L / mm', 400.0, positive=True, optional=True, step=1.0),
        ParameterSpec('current_unit_4', '表 7-2 · 4 mm 电流记录单位 / A', 1e-11, positive=True,
                      optional=True, step=1e-12, help='若表头为 I/(10⁻¹¹ A)，单位填 1e-11，表格填原始读数。'),
        ParameterSpec('current_unit_2', '表 7-2 · 2 mm 电流记录单位 / A', 1e-11, positive=True,
                      optional=True, step=1e-12, help='若表头为 I/(10⁻¹¹ A)，单位填 1e-11，表格填原始读数。'),
    )
    return ExperimentSpec(
        'lower_07_photoelectric', '光电效应', '下册', 7,
        '测量截止电压与入射光频率的关系，并比较两种光阑下的光电管伏安特性。',
        DESCRIPTION, tuple(tables), parameters, compute, explain, format_tables=format_tables,
        build_plot=build_plot, plot_kind='matplotlib', discussion=DISCUSSION,
        plot_caption='伏安曲线统一以 A 为电流单位；缺测点不连线。',
    )
