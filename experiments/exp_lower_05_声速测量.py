"""下册实验五：声速的测量。按手册表 5-1 与数据处理三步计算。"""

import hashlib
import math

import numpy as np
import pandas as pd
import streamlit as st


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


class Experiment:
    volume = '下册'
    number = 5
    experiment_id = 'lower_05_sound_speed'

    def __init__(self):
        self.name = '实验五：声速的测量'
        self.description = r"""
##### 数据说明
- 表 5-1：序号 $i$、$l_i$（共振干涉法、相位比较法），单位为 mm。
- $\Delta l_i = l_{i+5}-l_i$，只对应前五行；表尾给出平均值 $\overline{\Delta l}$。
- 表头环境参数：谐振频率 $f$（kHz）、室温 $t$（℃）、饱和蒸气压 $P_\mathrm{s}$（$\times10^5$ Pa）、相对湿度 $r$（%）。
- 逐差法求波长：$\overline{\Delta l}=\frac{1}{n}\sum\limits_{i=1}^{n}\Delta l_i$，$\lambda=2\left(\frac{\overline{\Delta l}}{5}\right)$。
- 声速测量值：$v_\text{测}=\lambda f$。
##### 数据处理
1. 计算声速理论值 $v$：$v=331.45\sqrt{\left(1+\frac{t}{T_0}\right)\left(1+0.3192\frac{rP_\mathrm{s}}{P}\right)}$，$T_0=273.15$ K，大气压 $P$ 取 $1.013\times10^5$ Pa。
2. 共振干涉法测声速：逐差法求 $\lambda$，再由 $v_\text{测}=\lambda f$ 求声速，并计算相对误差。
3. 相位比较法测声速：同上。
4. 相对误差 $E_\mathrm{r}=\frac{|v_\text{测}-v|}{v}\times100\%$，误差取两位有效数字。
"""
        self.frequency = 37.1  # kHz
        self.temperature = 27.7  # ℃
        self.saturated = 0.0378  # ×10^5 Pa
        self.humidity = 62.0  # %
        self.key = '表 5-1：测量数据记录'
        self.initial_df = {self.key: pd.DataFrame({
            INDEX: list(range(1, ROWS + 1)),
            L_RESONANCE: list(INTERFERENCE_DATA),
            L_PHASE: list(PHASE_DATA),
        })}
        self.static_col = {self.key: [INDEX]}
        self.final_df = {}
        self.editor_sources = {}
        self.upload_digests = {}
        self.editor_versions = {self.key: 0}
        self.deltas = {}
        self.means = {}
        self.wavelengths = {}
        self.measured = {}
        self.errors = {}
        self.theoretical = math.nan

    def set_initial_df(self, initial_df, key):
        expected = list(self.initial_df[key].columns)
        if list(initial_df.columns) != expected:
            raise ValueError(f'CSV 列名及顺序必须为：{", ".join(expected)}')
        if len(initial_df) != ROWS:
            raise ValueError(f'表 5-1 必须为 {ROWS} 行测量数据。')
        if list(pd.to_numeric(initial_df[INDEX], errors='raise')) != list(range(1, ROWS + 1)):
            raise ValueError('序号 i 必须依次为 1 至 10。')
        values = initial_df[[L_RESONANCE, L_PHASE]].apply(pd.to_numeric, errors='raise')
        filled = values.to_numpy(dtype=float).ravel()
        filled = filled[np.isfinite(filled)]
        if (filled < 0).any():
            raise ValueError('测量位置必须为非负有限数值。')
        self.initial_df[key] = initial_df.copy()

    def _input_table(self, key):
        prefix = f'{self.experiment_id}_{key}'
        uploaded = st.file_uploader('上传 CSV 文件', type='csv', key=f'{prefix}_upload',
                                    help='列名、单位及格式须与下载的输入表一致。')
        if uploaded is None:
            self.upload_digests.pop(key, None)
        else:
            digest = hashlib.sha256(uploaded.getvalue()).hexdigest()
            if self.upload_digests.get(key) != digest:
                try:
                    imported = pd.read_csv(uploaded).drop(columns='Unnamed: 0', errors='ignore')
                    self.set_initial_df(imported, key)
                    self.editor_sources[key] = self.initial_df[key].copy()
                    self.editor_versions[key] += 1
                    self.upload_digests[key] = digest
                except (ValueError, KeyError, pd.errors.ParserError) as error:
                    st.error(f'CSV 导入失败：{error}')
        editor_key = f'{prefix}_editor_{self.editor_versions[key]}'
        if editor_key not in st.session_state:
            self.editor_sources[key] = self.initial_df[key].copy()
        edited = st.data_editor(self.editor_sources[key], hide_index=True,
                                disabled=self.static_col[key], key=editor_key,
                                column_config={
                                    col: st.column_config.NumberColumn(min_value=0.0)
                                    for col in self.initial_df[key].columns
                                    if col not in self.static_col[key]
                                })
        try:
            self.set_initial_df(edited, key)
        except ValueError as error:
            st.error(str(error))
        st.download_button('下载 CSV 文件', self.initial_df[key].to_csv(index=False),
                           file_name=f'下册_实验五_{key}.csv', mime='text/csv',
                           key=f'{prefix}_download')

    def render_inputs(self):
        st.markdown(f'**{self.key}**')
        self._input_table(self.key)
        left, right = st.columns(2)
        with left:
            self.frequency = st.number_input('谐振频率 f / kHz', min_value=0.0, step=0.1,
                                             value=self.frequency, format='%.1f',
                                             key=f'{self.experiment_id}_frequency')
        with right:
            self.temperature = st.number_input('室温 t / ℃', min_value=0.0, step=0.1,
                                               value=self.temperature, format='%.1f',
                                               key=f'{self.experiment_id}_temperature')
        with left:
            self.saturated = st.number_input('饱和蒸气压 Pₛ / ×10⁵ Pa', min_value=0.0,
                                             step=0.0001, value=self.saturated, format='%.4f',
                                             key=f'{self.experiment_id}_saturated')
        with right:
            self.humidity = st.number_input('相对湿度 r / %', min_value=0.0, max_value=100.0,
                                            step=1.0, value=self.humidity, format='%.1f',
                                            key=f'{self.experiment_id}_humidity')

    def fill_data(self):
        table = self.initial_df[self.key].reset_index(drop=True)
        columns = {
            RESONANCE: pd.to_numeric(table[L_RESONANCE], errors='coerce').to_numpy(dtype=float),
            PHASE: pd.to_numeric(table[L_PHASE], errors='coerce').to_numpy(dtype=float),
        }
        self.deltas = {method: successive_differences(values) for method, values in columns.items()}
        for method, deltas in self.deltas.items():
            mean, wave = mean_and_wavelength(deltas)
            self.means[method] = mean
            self.wavelengths[method] = wave
            self.measured[method] = wave * self.frequency
        self.theoretical = theoretical_speed(self.temperature, self.saturated * 1e5,
                                             self.humidity / 100)
        self.errors = {method: relative_error(measured, self.theoretical)
                       for method, measured in self.measured.items()}

        result = pd.DataFrame({INDEX: [*map(str, range(1, ROWS + 1)), '平均值 Δl̄']})
        for column, method in ((L_RESONANCE, RESONANCE), (L_PHASE, PHASE)):
            result[column] = [*_cells(columns[method], 2), '']
        for column, method in ((D_RESONANCE, RESONANCE), (D_PHASE, PHASE)):
            result[column] = [*_cells(self.deltas[method], 2),
                              *[''] * (ROWS - SPAN), _mean_cell(self.means[method])]
        self.final_df = {self.key: result}

    def calculate(self):
        st.markdown('**（1）计算声速理论值 v**')
        st.latex(r'v=331.45\sqrt{\left(1+\frac{t}{T_0}\right)\left(1+0.3192\frac{rP_\mathrm{s}}{P}\right)}')
        st.latex(rf't={self.temperature:g}\,^\circ\mathrm{{C}},\quad T_0={T0:g}\,\mathrm{{K}},\quad '
                 rf'r={self.humidity:g}\%,\quad P_\mathrm{{s}}={self.saturated:g}\times10^5\,\mathrm{{Pa}},\quad '
                 rf'P={ATMOSPHERE / 1e5:g}\times10^5\,\mathrm{{Pa}}')
        st.latex(rf'v=331.45\sqrt{{\left(1+\frac{{{self.temperature:g}}}{{{T0:g}}}\right)'
                 rf'\left(1+0.3192\times\frac{{{self.humidity / 100:.2f}\times'
                 rf'{self.saturated:g}\times10^5}}{{{ATMOSPHERE / 1e5:g}\times10^5}}\right)}}'
                 rf'={fixed(self.theoretical, 1)}\,\mathrm{{m/s}}')

        for order, method in ((2, RESONANCE), (3, PHASE)):
            st.markdown(f'**（{order}）{method}测声速**')
            st.markdown('① 运用逐差法处理数据，计算波长 λ')
            st.latex(r'\overline{\Delta l}=\frac{1}{n}\sum_{i=1}^{n}\Delta l_i')
            terms = [value for value in self.deltas[method] if math.isfinite(value)]
            if terms:
                st.latex(rf'\overline{{\Delta l}}=\frac{{1}}{{{len(terms)}}}'
                         rf'\left({" + ".join(f"{value:.2f}" for value in terms)}\right)'
                         rf'={self.means[method]:.3f}\,\mathrm{{mm}}')
            else:
                st.write('Δl̄：逐差值未填写，暂不能计算。')
            st.latex(r'\lambda=2\left(\frac{\overline{\Delta l}}{5}\right)')
            if math.isfinite(self.wavelengths[method]):
                st.latex(rf'\lambda=2\times\frac{{{self.means[method]:.3f}}}{{5}}'
                         rf'={self.wavelengths[method]:.4f}\,\mathrm{{mm}}'
                         rf'={fixed(self.wavelengths[method] / 1000, 7)}\,\mathrm{{m}}')
            else:
                st.write('λ：平均逐差值未填写，暂不能计算。')
            st.markdown('② 计算声速的测量值 v测')
            st.latex(r'v_\text{测}=\lambda f')
            if math.isfinite(self.measured[method]):
                st.latex(rf'v_\text{{测}}={fixed(self.wavelengths[method] / 1000, 7)}\times'
                         rf'{self.frequency:g}\times10^3={fixed(self.measured[method], 1)}\,\mathrm{{m/s}}')
            else:
                st.write('v测：波长未填写，暂不能计算。')
            st.markdown('③ 计算声速测量值与理论值的相对误差 Eᵣ')
            st.latex(r'E_\mathrm{r}=\frac{\left|v_\text{测}-v\right|}{v}\times100\%')
            if math.isfinite(self.errors[method]):
                st.latex(rf'E_\mathrm{{r}}=\frac{{\left|{fixed(self.measured[method], 1)}-'
                         rf'{fixed(self.theoretical, 1)}\right|}}{{{fixed(self.theoretical, 1)}}}\times100\%'
                         rf'={error_text(self.errors[method])}\%')
            else:
                st.write('Er：测量值或理论值未填写，暂不能计算。')

        st.divider()
        st.subheader('思考题')
        st.markdown(r"""
**（1）产生驻波的条件是什么？如何产生稳定的驻波？**

两列振幅、频率、振动方向相同而传播方向相反的相干波在同一直线上叠加。$S_1$ 发出的超声波经 $S_2$ 反射后与入射波叠加即成驻波；端面平行且垂直于轴线、频率等于换能器固有频率时驻波稳定。

**（2）是否可以利用此方法测定超声波在其他介质中的传播速度？**

可以。依据是 $v=\lambda f$，与介质种类无关，只要该介质能传播超声波、能形成驻波或比较相位即可；更换介质需换用声阻抗匹配的换能器并良好耦合。

**（3）为什么要在换能器谐振状态下测定空气中的声速？**

谐振时电声转换效率最高、发射振幅最大、接收信号最强，驻波极大值（或相位差零点）最尖锐、易判断，误差小；且输出频率稳定，读得的 $f$ 更可靠。

**（4）实验中如何使信号源的输出频率等于换能器的固有频率？**

固定两换能器间距，缓慢调节信号源频率，同时观察示波器上接收信号的幅度，波形幅度最大时该频率即为换能器固有频率，可直接读出。
""")

    def plot(self):
        """手册本章只要求表 5-1 的数据处理，不要求作图。"""
        st.info('本章节无需绘图：手册只要求逐差法求波长 λ、声速测量值 v测 = λf 和相对误差 Er，'
                '结果见上方「计算结果」表与「数据处理」中的公式推导。')
