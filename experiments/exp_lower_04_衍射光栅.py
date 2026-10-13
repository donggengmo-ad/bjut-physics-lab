"""下册实验四：衍射光栅及其特性，按表 4-1 和三项数据处理要求。"""

import math
import re

import numpy as np
import pandas as pd

ORDER = '级次 k'
SPECTRAL = '谱线'
WAVE = 'λ / nm'
ANGLES = ('θ左Ⅰ', 'θ左Ⅱ', 'θ右Ⅰ', 'θ右Ⅱ')
PHI_I, PHI_II, PHI = 'φⅠ / °', 'φⅡ / °', 'φ / °'
SPACING = 'dᵢ / nm'
COLORS = ('蓝', '绿', '黄1', '黄2')
WAVELENGTHS = (435.8, 546.1, 577.0, 579.0)


from core.angles import parse_angle, angle_text


def diffraction_angle(left, right):
    """圆周上的最短角距离除以二，避免跨 0° 时误取整圈差值。"""
    if not math.isfinite(left) or not math.isfinite(right):
        return math.nan
    difference = abs(right - left)
    return min(difference, 360 - difference) / 2



def number_text(value, digits=4):
    if value is None or not math.isfinite(value):
        return '—'
    text = f'{value:#.{digits}g}'
    if 'e' in text:
        mantissa, exponent = text.split('e')
        return rf'{mantissa}\times10^{{{int(exponent)}}}'
    return text


def interval_dispersion(phi_a, phi_b, lambda_a, lambda_b, order, spacing):
    """Δφ/Δλ：角差转为 rad，理论值在区间中点角处计算。"""
    result = dict(delta_phi=math.nan, measured=math.nan, theoretical=math.nan, approximate=math.nan)
    if math.isfinite(phi_a) and math.isfinite(phi_b):
        delta_phi = math.radians(phi_b - phi_a)
        result.update(delta_phi=delta_phi, measured=delta_phi / (lambda_b - lambda_a))
        midpoint = math.radians((phi_a + phi_b) / 2)
        if math.isfinite(spacing) and spacing > 0 and math.cos(midpoint) > 1e-12:
            result['theoretical'] = order / (spacing * math.cos(midpoint))
    if math.isfinite(spacing) and spacing > 0:
        result['approximate'] = order / spacing
    return result

from core.models import (ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec,
                         InputState, ResultBundle, Metric, Explanation, DisplayTable, ValidationIssue)
from core.formatting import significant, latex_number

DESCRIPTION = '\n##### 数据说明\n- 表 4-1：记录零级位置及一、二级蓝、绿、黄1、黄2谱线的左右角位置，分别读取游标Ⅰ、Ⅱ。\n- 已知波长依次为 435.8、546.1、577.0、579.0 nm；表头记录照亮光栅的长度 $l$（mm）和光栅编号。\n- 角位置按度、分填写：30.15 表示 30°15′，也可填写 30:15 或 30°15′；30.10 表示 30°10′。\n- 注意测量结果及其不确定度的有效位数。\n'


ID = 'lower_04_diffraction_grating'
KEY = '表 4-1：测量光栅常数'


def default_tables():
    return {KEY: pd.DataFrame({ORDER: [0, *([1] * 4), *([2] * 4)],
        SPECTRAL: ['0级', *COLORS, *COLORS], WAVE: [math.nan, *WAVELENGTHS, *WAVELENGTHS],
        **{column: [None] * 9 for column in ANGLES}})}


def compute(inputs):
    frame = inputs.tables[KEY].copy()
    length_mm = inputs.parameters['length_mm']
    for column in (PHI_I, PHI_II, PHI, SPACING):
        frame[column] = math.nan
    notes = []
    for row in range(1, 9):
        angles = [parse_angle(frame.at[row, column]) for column in ANGLES]
        phi_i, phi_ii = diffraction_angle(angles[0], angles[2]), diffraction_angle(angles[1], angles[3])
        frame.at[row, PHI_I], frame.at[row, PHI_II] = phi_i, phi_ii
        if math.isfinite(phi_i) and math.isfinite(phi_ii):
            phi = (phi_i + phi_ii) / 2
            frame.at[row, PHI] = phi
            if phi > 0:
                frame.at[row, SPACING] = frame.at[row, ORDER] * frame.at[row, WAVE] / math.sin(math.radians(phi))
            else:
                notes.append(f'{int(frame.at[row, ORDER])}级{frame.at[row, SPECTRAL]}：衍射角为零，不能计算光栅常数。')
    spacings = frame[SPACING].dropna()
    spacing_count = len(spacings)
    mean_spacing = float(spacings.mean()) if spacing_count else math.nan
    slit_count = length_mm * 1e6 / mean_spacing if length_mm is not None and math.isfinite(mean_spacing) else math.nan
    records = []
    midpoints = {}
    for order in (1, 2):
        group = frame.loc[frame[ORDER] == order].reset_index(drop=True)
        for interval in range(3):
            first, last = group.iloc[interval], group.iloc[interval + 1]
            midpoints[(order, interval)] = (first[PHI] + last[PHI]) / 2
            interval_result = interval_dispersion(first[PHI], last[PHI], first[WAVE], last[WAVE], order, mean_spacing)
            records.append({ORDER: order, '谱线区间': f'{first[SPECTRAL]}—{last[SPECTRAL]}',
                'Δλ / nm': last[WAVE] - first[WAVE], 'Δφ / rad': interval_result['delta_phi'],
                'ψ实 / (rad/nm)': interval_result['measured'], 'ψ理 / (rad/nm)': interval_result['theoretical'],
                'k/d̄ / (rad/nm)': interval_result['approximate']})
    dispersion = pd.DataFrame(records)
    if spacing_count < 8:
        notes.append(f'已完成 {spacing_count}/8 条非零级谱线；平均光栅常数仅使用已完成记录。')
    if length_mm is None:
        notes.append('未填写照亮长度 l，暂不能计算分辨本领。')
    return ResultBundle({KEY: frame, '角色散率': dispersion},
        dict(input_key=KEY, length_mm=length_mm, grating_number=inputs.parameters['grating_number'],
             mean_spacing=mean_spacing, slit_count=slit_count, spacing_count=spacing_count,
             dispersion=dispersion, midpoints=midpoints, input_issues=notes, resolving_power={k: k*slit_count for k in (1,2)}), notes,
        (Metric('平均光栅常数', significant(mean_spacing, 4, trailing=True), 'nm'),
         Metric('有效谱线', f'{spacing_count}/8'), Metric('照亮缝数 N', significant(slit_count, 4, trailing=True))))


def format_dispersion(result):
    display = result.tables['角色散率'].copy()
    for column in display.columns[2:]:
        display[column] = display[column].map(lambda v: '$' + latex_number(v, 3, trailing=True) + '$' if math.isfinite(v) else '—')
    display['谱线区间'] = display['谱线区间'].map(lambda text: '\u2060'.join(text))
    return display.rename(columns={ORDER: '$k$', '谱线区间': '谱线',
        'Δλ / nm': r'$\Delta\lambda/\mathrm{nm}$', 'Δφ / rad': r'$\Delta\varphi/\mathrm{rad}$',
        'ψ实 / (rad/nm)': r'$\psi_{\mathrm{实}}/(\mathrm{rad/nm})$',
        'ψ理 / (rad/nm)': r'$\psi_{\mathrm{理}}/(\mathrm{rad/nm})$',
        'k/d̄ / (rad/nm)': r'$(k/\bar{d})/(\mathrm{rad/nm})$'})


def format_tables(inputs, result):
    frame = result.tables[KEY]
    display = frame.copy()
    for column in ANGLES:
        display[column] = frame[column].map(lambda value: angle_text(parse_angle(value), latex=False))
    display[WAVE] = frame[WAVE].map(lambda v: f'{v:.1f}' if pd.notna(v) else '—')
    for column in (PHI_I, PHI_II, PHI):
        display[column] = frame[column].map(lambda value: angle_text(value, latex=False))
    display[SPACING] = frame[SPACING].map(lambda v: '$' + latex_number(v, 4, trailing=True) + '$' if math.isfinite(v) else '—')
    dispersion = format_dispersion(result)
    headers = {
        WAVE: r'$\lambda/\mathrm{nm}$',
        ANGLES[0]: r'$\theta_{\text{左},\mathrm{I}}$',
        ANGLES[1]: r'$\theta_{\text{左},\mathrm{II}}$',
        ANGLES[2]: r'$\theta_{\text{右},\mathrm{I}}$',
        ANGLES[3]: r'$\theta_{\text{右},\mathrm{II}}$',
        PHI_I: r'$\varphi_{\mathrm{I}}$', PHI_II: r'$\varphi_{\mathrm{II}}$',
        PHI: r'$\varphi=(\varphi_{\mathrm{I}}+\varphi_{\mathrm{II}})/2$',
        SPACING: r'$d_i/\mathrm{nm}$',
    }
    return [DisplayTable(KEY, display.rename(columns=headers), math=True), DisplayTable('角色散率', dispersion, math=True)]


def get_spec():
    frame = default_tables()[KEY]
    return ExperimentSpec(ID, '实验四：衍射光栅及其特性', '下册', 4,
        '记录双游标角位置，计算光栅常数、角色散率与分辨本领。', DESCRIPTION,
        (TableSpec(KEY, KEY, frame, tuple(ColumnSpec(c, 'angle' if c in ANGLES else 'text' if c == SPECTRAL else 'number',
                    help='度.分，例如 30.15 表示 30°15′；也支持 30:15。' if c in ANGLES else None,
                    format='%.1f' if c==WAVE else None) for c in frame), (ORDER, SPECTRAL, WAVE),
                    optional_cells=tuple((0, c) for c in ANGLES)),),
        (ParameterSpec('length_mm', '照亮光栅的长度 l / mm', None, positive=True, optional=True),
         ParameterSpec('grating_number', '光栅编号', '', kind='text', optional=True)),
        compute, explain, format_tables=format_tables, build_plot=build_plot, plot_kind='matplotlib',
        plot_caption='圆点实线为一级，方点虚线为二级；测量缺失处断开。', discussion=DISCUSSION)

DISCUSSION = '**（1）当狭缝太宽或太窄时，分别会出现什么现象？**\n\n太宽会使谱线变宽、相邻谱线难以分辨；太窄会使光强减弱，谱线暗淡、难以观测。\n\n**（2）比较光栅光谱与棱镜光谱的异同。**\n\n两者都能分光；光栅靠衍射，红光偏转更大且有多级光谱；棱镜靠折射，通常紫光偏转更大。\n\n**（3）怎样利用光栅常数已知的光栅测量光源的波长？**\n\n使光垂直入射光栅，测量已知级次 $k$ 的衍射角 $\\varphi$，由 $\\lambda=d\\sin\\varphi/k$ 求波长。'

def explain(inputs, result):
    doc = Explanation()
    data_dispersion = result.values['dispersion']
    data_final_df = result.tables
    data_input_key = result.values['input_key']
    data_length_mm = result.values['length_mm']
    data_mean_spacing = result.values['mean_spacing']
    data_slit_count = result.values['slit_count']
    data_spacing_count = result.values['spacing_count']
    frame = data_final_df[data_input_key]
    doc.markdown('**1. 计算光栅常数**')
    doc.latex(r'\varphi_{\mathrm{I,II}}=\frac{|\theta_{\text{右},\mathrm{I,II}}-\theta_{\text{左},\mathrm{I,II}}|}{2},\qquad'
             r'\varphi=\frac{\varphi_{\mathrm{I}}+\varphi_{\mathrm{II}}}{2}')
    doc.caption('左右读数跨过 0° 时，角差按圆周上的最短距离计算。')
    doc.latex(r'd_i\sin\varphi_i=k_i\lambda_i,\qquad d_i=\frac{k_i\lambda_i}{\sin\varphi_i},\qquad'
             r'\overline d=\frac{1}{n}\sum_{i=1}^{n}d_i')
    valid = frame.loc[frame[SPACING].notna()]
    for _, row in valid.iterrows():
        doc.markdown(f'{int(row[ORDER])}级 · {row[SPECTRAL]}')
        doc.latex(rf'd_i=\frac{{{int(row[ORDER])}\times{row[WAVE]:.1f}}}{{\sin({angle_text(row[PHI])})}}'
                 rf'\approx{number_text(row[SPACING])}\,\mathrm{{nm}}')
    if data_spacing_count:
        terms = '+'.join(number_text(value, digits=6) for value in valid[SPACING])
        doc.latex(rf'\overline d=\frac{{{terms}}}{{{data_spacing_count}}}\approx{number_text(data_mean_spacing)}\,\mathrm{{nm}}')
        if data_spacing_count < 8:
            doc.caption(f'已完成 {data_spacing_count}/8 条非零级谱线；当前平均值仅使用已完成记录。')
    else:
        doc.markdown('填写一、二级谱线的四个角位置后计算光栅常数；零级不参加平均。')

    doc.markdown('**2. 色散曲线、角色散率和光谱特点**')
    doc.markdown('在同一张图中绘制 k=1、k=2 的 φ–λ 曲线，图见“图表”标签页。')
    doc.latex(r'\psi_{\text{实}}=\frac{\Delta\varphi}{\Delta\lambda},\qquad'
             r'\psi_{\text{理}}=\frac{k}{\overline d\cos\varphi}\approx\frac{k}{\overline d}')
    doc.caption('按曲线上相邻测量点计算 Δφ/Δλ，角差换算为 rad；ψ理取该区间的中点角。')
    doc.table(format_dispersion(result))
    for order in (1, 2):
        group = frame.loc[frame[ORDER] == order].reset_index(drop=True)
        for interval in range(3):
            record = data_dispersion.loc[
                (data_dispersion[ORDER] == order) &
                (data_dispersion['谱线区间'] == f'{COLORS[interval]}—{COLORS[interval + 1]}')
            ].iloc[0]
            if math.isfinite(record['ψ实 / (rad/nm)']):
                first, last = group.iloc[interval], group.iloc[interval + 1]
                doc.markdown(f'{order}级 · {record["谱线区间"]}')
                doc.latex(rf'\psi_{{\text{{实}},{order}}}=\frac{{'
                         rf'({last[PHI]:.6g}-{first[PHI]:.6g})\times\pi/180'
                         rf'}}{{{last[WAVE]:.1f}-{first[WAVE]:.1f}}}'
                         rf'\approx{number_text(record["ψ实 / (rad/nm)"], digits=3)}\,\mathrm{{rad/nm}}')
                if math.isfinite(record['ψ理 / (rad/nm)']):
                    midpoint = result.values['midpoints'][(order, interval)]
                    doc.latex(rf'\psi_{{\text{{理}},{order}}}=\frac{{{order}}}{{'
                             rf'{number_text(data_mean_spacing, digits=6)}\cos({angle_text(midpoint)})'
                             rf'}}\approx{number_text(record["ψ理 / (rad/nm)"], digits=3)}\,\mathrm{{rad/nm}}')
    comparisons = []
    for color in COLORS:
        group = frame.loc[(frame[SPECTRAL] == color) & frame[PHI].notna()]
        if set(group[ORDER]) == {1, 2}:
            first, second = (float(group.loc[group[ORDER] == order, PHI].iloc[0]) for order in (1, 2))
            relation = '大于' if second > first else '小于' if second < first else '等于'
            comparisons.append(f'{color}谱线的二级衍射角{relation}一级')
    if comparisons:
        doc.markdown('实测结果：' + '；'.join(comparisons) + '。')
    doc.markdown('由理论公式可知：同级光谱中，长波长的衍射角更大；级次越高，角色散率越大。'
             '小角度时色散近似均匀，不同级次的光谱可能重叠。')

    doc.markdown('**3. 计算分辨本领**')
    doc.latex(r'R=\frac{\lambda}{\Delta\lambda}=kN,\qquad N=\frac{l}{\overline d}')
    if math.isfinite(data_slit_count):
        doc.latex(rf'l={data_length_mm:g}\,\mathrm{{mm}}={data_length_mm:g}\times10^6\,\mathrm{{nm}}')
        doc.latex(rf'N=\frac{{{data_length_mm:g}\times10^6}}{{{number_text(data_mean_spacing, digits=6)}}}'
                 rf'\approx{number_text(data_slit_count)}')
        for order in (1, 2):
            doc.latex(rf'R_{{k={order}}}={order}\times{number_text(data_slit_count, digits=6)}'
                     rf'\approx{number_text(result.values["resolving_power"][order])}')
    else:
        doc.markdown('填写表头 l 并算出光栅常数后，计算总缝数 N 及一、二级的分辨本领。')
    return doc

def build_plot(inputs, result):
    import matplotlib.font_manager as fm
    import matplotlib as mpl
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    data_final_df = result.tables
    data_input_key = result.values['input_key']
    frame = data_final_df[data_input_key]
    available = {font.name for font in fm.fontManager.ttflist}
    font = next((name for name in ('Noto Sans CJK SC', 'Source Han Sans SC', 'SimHei',
                                  'Microsoft YaHei', 'PingFang SC', 'Heiti SC',
                                  'Arial Unicode MS') if name in available), None)
    with mpl.rc_context({
        'font.family': font or 'DejaVu Sans', 'font.size': 10, 'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'axes.unicode_minus': False, 'pdf.fonttype': 42, 'svg.fonttype': 'none',
    }):
        # Streamlit 在工作线程中执行；直接用 Agg 画布，不创建桌面 GUI 窗口。
        fig = Figure(figsize=(7.2, 4.8), dpi=100, layout='constrained')
        FigureCanvasAgg(fig)
        ax = fig.subplots()
        for order, color, marker, line in [(1, '#0072B2', 'o', '-'), (2, '#D55E00', 's', '--')]:
            group = frame.loc[frame[ORDER] == order]
            # 不跨过缺失值连线，也不由理论值补造测量点。
            ax.plot(group[WAVE], group[PHI], color=color, marker=marker, linestyle=line,
                    linewidth=1.5, markersize=4.5, label=f'k = {order}')
        ax.set_title('衍射光栅的色散曲线' if font else 'Diffraction grating dispersion curves', pad=32)
        ax.set_xlabel(r'波长 $\lambda$ / nm' if font else r'Wavelength $\lambda$ / nm')
        ax.set_ylabel(r'衍射角 $\varphi$ / °' if font else r'Diffraction angle $\varphi$ / °')
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=2, frameon=False)
        ax.grid(alpha=0.25)
        ax.margins(x=0.06, y=0.10)
        ax.spines[['top', 'right']].set_visible(False)
    return fig
