import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt


class Experiment:
    def __init__(self):
        self.name = "实验九：弗兰克-赫兹实验"
        self.description = """
            ##### 数据说明：
            - $V_{G2K}$：加速电压，单位 V
            - $I_p$：板极电流，单位 $\\times 10$ nA
            - 电压参数：$V_f = 3.75$ V，$V_p = 6.96$ V，$V_{G1} = 1.87$ V
            ##### 注意事项：
            - 程序自动识别 $I_p$ 的极大值（波峰）
            - 用逐差法处理前偶数个波峰对应的 $V_{G2K}$，求出第一激发电位 $V_g$
            - $V_{G理} = 11.55$ V
        """
        self.key = "数据表"
        self.initial_df = {
            self.key: pd.DataFrame({
                "V_G2K(V)": [
                    6, 8, 10, 12, 12.6, 14, 16, 18, 20, 22, 24,
                    26, 28, 30, 32, 33.2, 34, 36, 38, 39.4, 40, 42,
                    44, 44.5, 46, 48, 50, 51.3, 52, 54, 56, 58, 60,
                    62, 62.7, 64, 66, 68, 69.2, 70, 72, 74, 75.6, 76,
                    78, 80, 81.2, 82, 84, 86, 88, 90, 92, 94, 96, 97.5,
                ],
                "Ip(×10nA)": [
                    0.05, 0.42, 2.30, 4.70, 6.47, 8.70, 10.23, 10.90, 9.70, 7.03, 11.51,
                    19.5, 23.9, 19.0, 10.1, 6.8, 9.2, 20.7, 30.0, 32.2, 31.5, 19.9,
                    7, 6.6, 14.2, 28, 38.8, 40.3, 32.2, 22.4, 8.7, 18, 34,
                    46, 47, 45, 30, 15.6, 15, 23.4, 38.9, 50.9, 54.4, 53.6,
                    43.4, 27.3, 26, 28.4, 41.5, 56.2, 62.9, 58.7, 47, 41.7, 48.5, 57.6,
                ],
            })
        }
        self.static_col = {self.key: []}
        self.final_df = {}

    def set_initial_df(self, initial_df: pd.DataFrame, key: str):
        self.initial_df[key] = initial_df

    def fill_data(self):
        df = self.initial_df[self.key].copy()
        df["V_G2K(V)"] = pd.to_numeric(df["V_G2K(V)"], errors="coerce")
        df["Ip(×10nA)"] = pd.to_numeric(df["Ip(×10nA)"], errors="coerce")
        df = df.sort_values("V_G2K(V)").reset_index(drop=True)
        self.final_df[self.key] = df

    @staticmethod
    def _find_peaks(V, I):
        """识别 Ip-V_G2K 曲线中的局部极大值（波峰），含末点边界处理"""
        peaks_V = []
        peaks_I = []
        for i in range(1, len(I) - 1):
            if I[i] > I[i - 1] and I[i] > I[i + 1]:
                peaks_V.append(V[i])
                peaks_I.append(I[i])
        # 末点：若高于前一个点，也视为波峰
        if len(I) >= 2 and I[-1] > I[-2]:
            peaks_V.append(V[-1])
            peaks_I.append(I[-1])
        return np.array(peaks_V), np.array(peaks_I)

    def calculate(self):
        if self.key not in self.final_df or self.final_df[self.key].empty:
            self.fill_data()

        df = self.final_df[self.key]
        V = df["V_G2K(V)"].values
        I = df["Ip(×10nA)"].values

        peaks_V, peaks_I = self._find_peaks(V, I)

        # 取前偶数个波峰
        n_peaks = len(peaks_V)
        if n_peaks % 2 != 0:
            n_peaks -= 1
        peaks_V = peaks_V[:n_peaks]
        peaks_I = peaks_I[:n_peaks]
        n = n_peaks // 2

        # 逐差法求 V_g
        first_half = peaks_V[:n]
        second_half = peaks_V[n:]
        diffs = second_half - first_half
        sum_diffs = np.sum(diffs)
        V_g = sum_diffs / (n * n)

        # 理论值与相对误差
        V_G_theory = 11.55
        E_r = abs(V_g - V_G_theory) / V_G_theory * 100
        peaks_str = ""
        for i in range(n_peaks):
            peaks_str += f"\n | {i+1} | {peaks_V[i]:.1f} | {peaks_I[i]:.1f} |"

        st.markdown(f"""
            #### 1. 波峰识别结果
从 $I_p-V_{{G2K}}$ 曲线中共识别出 **{n_peaks}** 个波峰（取偶数个用于逐差法）：

| 序号 | $V_{{G2K}}$ (V) | $I_p$ (×10 nA) |
|------|----------------|---------------|{peaks_str}""")



        st.markdown(f"""
            <br>

            #### 2. 逐差法求第一激发电位 $V_g$

            ##### 原始公式
            $$ V_g = \\frac{{1}}{{n \\times n \\Delta x}} \\sum_{{i=1}}^{{n}} (y_{{n+i}} - y_i) $$

            其中 $n = {n}$，$\\Delta x = 1$。

            ##### 代入数据

            前半波峰：$V_{{G2K}} = [{', '.join(f'{v:.1f}' for v in first_half)}]$ V

            后半波峰：$V_{{G2K}} = [{', '.join(f'{v:.1f}' for v in second_half)}]$ V

            $$ \\sum_{{i=1}}^{{{n}}} (y_{{n+i}} - y_i) = {" + ".join(f"({second_half[i]:.1f} - {first_half[i]:.1f})" for i in range(n)) + f" = {sum_diffs:.1f}"} $$

        """, unsafe_allow_html=True)

        st.markdown(f"""
            $$ V_g = \\frac{{{sum_diffs:.1f}}}{{{n} \\times {n} \\times 1}} = {V_g:.2f} \\;\\text{{V}} $$

            <br>

            #### 3. 相对误差

            ##### 原始公式
            $$ E_r = \\frac{{|V_g - V_{{G理}}|}}{{V_{{G理}}}} \\times 100\\% $$

            ##### 代入数据
            $$ E_r = \\frac{{|{V_g:.2f} - {V_G_theory}|}}{{{V_G_theory}}} \\times 100\\% = {E_r:.1f}\\% $$
        """, unsafe_allow_html=True)

    def plot(self):
        if self.key not in self.final_df or self.final_df[self.key].empty:
            self.fill_data()

        df = self.final_df[self.key]
        V = df["V_G2K(V)"].values
        I = df["Ip(×10nA)"].values
        peaks_V, peaks_I = self._find_peaks(V, I)

        # 取前偶数个波峰用于标注
        n_peaks = len(peaks_V)
        if n_peaks % 2 != 0:
            n_peaks -= 1

        # 构建表格数据
        table_data = [[f"{i+1}", f"{peaks_V[i]:.1f}", f"{peaks_I[i]:.1f}"]
                      for i in range(n_peaks)]
        columns = ["", "$V_{G2K}$ (V)", "Ip (×10 nA)"]

        # 创建上下布局：上图下表
        fig = plt.figure(figsize=(10, 7))
        gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.35)

        # 上图：曲线
        ax_curve = fig.add_subplot(gs[0])
        ax_curve.plot(V, I, 'b-', linewidth=1.2, label='$I_p$-$V_{G2K}$')
        ax_curve.scatter(V, I, s=20, c='blue', zorder=3)
        ax_curve.scatter(peaks_V[:n_peaks], peaks_I[:n_peaks], s=50, c='red',
                         zorder=5, label=f'peaks ({n_peaks})')

        for i in range(n_peaks):
            ax_curve.annotate(
                f'{peaks_V[i]:.1f}V',
                (peaks_V[i], peaks_I[i]),
                textcoords="offset points",
                xytext=(0, 10),
                ha='center',
                fontsize=8,
                color='red',
            )

        ax_curve.set_xlabel('$V_{G2K}$ (V)', fontsize=12)
        ax_curve.set_ylabel('$I_p$ (×10 nA)', fontsize=12)
        ax_curve.set_title('$I_p$-$V_{G2K}$', fontsize=14)
        ax_curve.legend()
        ax_curve.grid(True, alpha=0.3)

        # 下图：波峰统计表
        ax_table = fig.add_subplot(gs[1])
        ax_table.axis("off")
        tbl = ax_table.table(
            cellText=table_data,
            colLabels=columns,
            cellLoc="center",
            loc="center",
            colWidths=[0.12, 0.2, 0.2],
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(10)
        tbl.scale(1, 1.5)

        # 表头样式
        for j in range(3):
            tbl[0, j].set_facecolor("#40466e")
            tbl[0, j].set_text_props(color="white", weight="bold")

        # 奇偶行交替背景色
        for i in range(n_peaks):
            for j in range(3):
                color = "#f0f0f0" if i % 2 == 0 else "white"
                tbl[i + 1, j].set_facecolor(color)

        st.pyplot(fig)
