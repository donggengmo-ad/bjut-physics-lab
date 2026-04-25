import pandas as pd
import numpy as np
import streamlit as st


class Experiment:
    def __init__(self):
        self.name = "实验三：扭摆法测转动惯量"
        self.description = """
            ##### 数据说明：  
            原表较复杂，拆成了几个分表
            - 质量表，单位kg
            - 几何尺寸：测量值和平均值，单位mm
            - 周期：测量值和平均值，单位s
            ##### 注意事项：  
            - 金属载物盘不算理论转动惯量
            - 结果比较小，都用科学计数表示了，如$1.6e−03 = 1.6^{-3}$
            - 取 $I_{4\\text{支}} = 2.32 \\times 10^{-5} kg \cdot m^2$
        """

        self.key = ["质量表", "几何尺寸测量值", "周期测量值"]
        self.initial_df = {
            "质量表": pd.DataFrame(
                {
                    "物体": ["金属载物盘", "塑料圆柱", "金属圆筒", "金属细杆"],
                    "质量(kg)": [np.nan, 0.71571, 0.70045, 0.13141],
                }
            ),
            "几何尺寸测量值": pd.DataFrame(
                {
                    "测量次数": [1, 2, 3],
                    "塑料圆柱_D1(mm)": [100.26, 100.26, 100.28],
                    "金属圆筒_Do(mm)": [99.94, 100.00, 99.98],
                    "金属圆筒_Di(mm)": [93.98, 94.04, 94.00],
                    "金属细杆_l(mm)": [610.0, 610.0, 610.0],
                }
            ),
            "周期测量值": pd.DataFrame(
                {
                    "测量次数": [1, 2, 3],
                    "金属载物盘_T0(s)": [0.751, 0.749, 0.751],
                    "塑料圆柱_T1(s)": [1.253, 1.254, 1.252],
                    "金属圆筒_T2(s)": [1.552, 1.553, 1.550],
                    "金属细杆_T4(s)": [2.145, 2.145, 2.145],
                }
            ),
        }

        self.static_col = {
            "质量表": ["物体"],
            "几何尺寸测量值": ["测量次数"],
            "周期测量值": ["测量次数"],
        }
        self.index = {k: self.static_col[k][0] for k in self.key}

        # 常量：细杆支架转动惯量
        self.I4_support = 2.32e-5
        self.final_df = {}

    def set_initial_df(self, initial_df: pd.DataFrame, key: str):
        self.initial_df[key] = initial_df

    @staticmethod
    def _to_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
        out = df.copy()
        for col in cols:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        return out

    def fill_data(self):
        mass_key = "质量表"
        geom_key = "几何尺寸测量值"
        period_key = "周期测量值"

        df_mass = self.initial_df[mass_key].copy()
        df_mass = self._to_numeric(df_mass, ["质量(kg)"])

        df_geom_meas = self.initial_df[geom_key].copy()
        geom_cols = [c for c in df_geom_meas.columns if c != "测量次数"]
        df_geom_meas = self._to_numeric(df_geom_meas, geom_cols)

        df_period_meas = self.initial_df[period_key].copy()
        period_cols = [c for c in df_period_meas.columns if c != "测量次数"]
        df_period_meas = self._to_numeric(df_period_meas, period_cols)

        mass_s = df_mass.set_index("物体")["质量(kg)"]
        geom_mean = pd.DataFrame(df_geom_meas[geom_cols].mean(axis=0), columns=["平均值"])
        period_mean = pd.DataFrame(df_period_meas[period_cols].mean(axis=0), columns=["平均值"])

        geo_m = geom_mean["平均值"] / 1000.0
        period_m = period_mean["平均值"]

        I_theory = pd.Series(
            {
                "塑料圆柱": 0.125 * mass_s["塑料圆柱"] * geo_m["塑料圆柱_D1(mm)"] ** 2,
                "金属圆筒": 0.125
                * mass_s["金属圆筒"]
                * (geo_m["金属圆筒_Do(mm)"] ** 2 + geo_m["金属圆筒_Di(mm)"] ** 2),
                "金属细杆": (1.0 / 12.0) * mass_s["金属细杆"] * geo_m["金属细杆_l(mm)"] ** 2,
            }
        )

        denom = period_m["塑料圆柱_T1(s)"] ** 2 - period_m["金属载物盘_T0(s)"] ** 2
        K = 4 * np.pi * I_theory["塑料圆柱"] / denom
        I0 = I_theory["塑料圆柱"] * period_m["金属载物盘_T0(s)"] ** 2 / denom

        I_exp = pd.Series(
            {
                "金属载物盘": I0,
                "塑料圆柱": K * period_m["塑料圆柱_T1(s)"] ** 2 / (4 * np.pi) - I0,
                "金属圆筒": K * period_m["金属圆筒_T2(s)"] ** 2 / (4 * np.pi) - I0,
                "金属细杆": K * period_m["金属细杆_T4(s)"] ** 2 / (4 * np.pi) - self.I4_support,
            }
        )

        df_I = pd.DataFrame({"I理论值(kg*m^2)": I_theory, "I实验值(kg*m^2)": I_exp})
        df_I["Er(%)"] = (
            np.abs(df_I["I实验值(kg*m^2)"] - df_I["I理论值(kg*m^2)"])
            / df_I["I理论值(kg*m^2)"]
            * 100
        ).round(2)

        self.final_df = {
            mass_key: df_mass.set_index("物体"),
            geom_key: df_geom_meas.set_index("测量次数"),
            "几何尺寸平均值": geom_mean,
            period_key: df_period_meas.set_index("测量次数"),
            "周期平均值": period_mean,
            "转动惯量结果": df_I,
        }

    def calculate(self):
        if "转动惯量结果" not in self.final_df:
            self.fill_data()

        df_mass = self.final_df["质量表"]
        df_geom_mean = self.final_df["几何尺寸平均值"]
        df_period_mean = self.final_df["周期平均值"]
        df_I = self.final_df["转动惯量结果"]

        m = df_mass["质量(kg)"]
        d1 = df_geom_mean.loc["塑料圆柱_D1(mm)", "平均值"] * 1e-3
        do = df_geom_mean.loc["金属圆筒_Do(mm)", "平均值"] * 1e-3
        di = df_geom_mean.loc["金属圆筒_Di(mm)", "平均值"] * 1e-3
        l = df_geom_mean.loc["金属细杆_l(mm)", "平均值"] * 1e-3

        t0 = df_period_mean.loc["金属载物盘_T0(s)", "平均值"]
        t1 = df_period_mean.loc["塑料圆柱_T1(s)", "平均值"]
        t2 = df_period_mean.loc["金属圆筒_T2(s)", "平均值"]
        t4 = df_period_mean.loc["金属细杆_T4(s)", "平均值"]

        i_the_plastic = 0.125 * m["塑料圆柱"] * d1 ** 2
        i_the_cylinder = 0.125 * m["金属圆筒"] * (do ** 2 + di ** 2)
        i_the_rod = (1.0 / 12.0) * m["金属细杆"] * l ** 2

        denom = t1 ** 2 - t0 ** 2
        k = 4 * np.pi * i_the_plastic / denom
        i0 = i_the_plastic * t0 ** 2 / denom

        i_exp_plate = i0
        i_exp_plastic = k * t1 ** 2 / (4 * np.pi) - i0
        i_exp_cylinder = k * t2 ** 2 / (4 * np.pi) - i0
        i_exp_rod = k * t4 ** 2 / (4 * np.pi) - self.I4_support

        er_plastic = abs(i_exp_plastic - i_the_plastic) / i_the_plastic * 100
        er_cylinder = abs(i_exp_cylinder - i_the_cylinder) / i_the_cylinder * 100
        er_rod = abs(i_exp_rod - i_the_rod) / i_the_rod * 100

        st.markdown(f"""
            #### 1. 扭转常数与载物盘转动惯量
            ##### 原始公式
            $$ I_{{\\text{{塑料,理}}}} = \\frac{{1}}{{8}}mD_1^2 $$
            
            $$ K = \\frac{{4\\pi I_{{\\text{{塑料,理}}}}}}{{T_1^2 - T_0^2}} $$
            
            $$ I_0 = I_{{\\text{{塑料,理}}}} \\cdot \\frac{{T_0^2}}{{T_1^2 - T_0^2}} $$

            ##### 带入数据
            $$ I_{{\\text{{塑料,理}}}} = \\frac{{1}}{{8}} \\times {m['塑料圆柱']:.5f} \\times ({d1:.5f})^2 = {i_the_plastic:.6e}\\;kg\\cdot m^2 $$
            
            $$ K = \\frac{{4\\pi \\times {i_the_plastic:.6e}}}{{({t1:.6f})^2 - ({t0:.6f})^2}} = {k:.6e} $$
            
            $$ I_0 = {i_the_plastic:.6e} \\times \\frac{{({t0:.6f})^2}}{{({t1:.6f})^2 - ({t0:.6f})^2}} = {i0:.6e}\\;kg\\cdot m^2 $$
        """, unsafe_allow_html=True)

        st.markdown(f"""
            #### 2. 四样测量物转动惯量（理论值、实验值、相对误差）
            ##### 原始公式
            $$ I_{{\\text{{圆柱,理}}}} = \\frac{{1}}{{8}}m(D_o^2 + D_i^2),\\quad I_{{\\text{{细杆,理}}}} = \\frac{{1}}{{12}}ml^2 $$
            
            $$ I_{{\\text{{实验}}}} = \\frac{{K T^2}}{{4\\pi}} - I_0 \\; (\\text{{细杆用支架修正}}\\;I_{{4}}) $$
            
            $$ E_r = \\frac{{|I_{{\\text{{实验}}}} - I_{{\\text{{理论}}}}|}}{{I_{{\\text{{理论}}}}}} \\times 100\\% $$

            ##### 塑料圆柱
            $$ I_{{\\text{{理}}}} = \\frac{{1}}{{8}} \\times {m['塑料圆柱']:.5f} \\times ({d1:.5f})^2 = {i_the_plastic:.6e} $$
            
            $$ I_{{\\text{{实}}}} = \\frac{{{k:.6e} \\times ({t1:.6f})^2}}{{4\\pi}} - {i0:.6e} = {i_exp_plastic:.6e} $$
            
            $$ E_r = \\frac{{|{i_exp_plastic:.6e} - {i_the_plastic:.6e}|}}{{{i_the_plastic:.6e}}} \\times 100\\% = {er_plastic:.2f}\\% $$

            ##### 金属圆筒
            $$ I_{{\\text{{理}}}} = \\frac{{1}}{{8}} \\times {m['金属圆筒']:.5f} \\times [({do:.5f})^2 + ({di:.5f})^2] = {i_the_cylinder:.6e} $$
            
            $$ I_{{\\text{{实}}}} = \\frac{{{k:.6e} \\times ({t2:.6f})^2}}{{4\\pi}} - {i0:.6e} = {i_exp_cylinder:.6e} $$
            
            $$ E_r = \\frac{{|{i_exp_cylinder:.6e} - {i_the_cylinder:.6e}|}}{{{i_the_cylinder:.6e}}} \\times 100\\% = {er_cylinder:.2f}\\% $$

            ##### 金属细杆
            $$ I_{{\\text{{理}}}} = \\frac{{1}}{{12}} \\times {m['金属细杆']:.5f} \\times ({l:.5f})^2 = {i_the_rod:.6e} $$
            
            $$ I_{{\\text{{实}}}} = \\frac{{{k:.6e} \\times ({t4:.6f})^2}}{{4\\pi}} - {self.I4_support:.6e} = {i_exp_rod:.6e} $$
            
            $$ E_r = \\frac{{|{i_exp_rod:.6e} - {i_the_rod:.6e}|}}{{{i_the_rod:.6e}}} \\times 100\\% = {er_rod:.2f}\\% $$

            ##### 金属载物盘
            $$ I_{{\\text{{实}}}} = I_0 = {i_exp_plate:.6e} \\;kg\\cdot m^2 $$
            
            $$ I_{{\\text{{理}}}}\\;\\text{{与}}\\;E_r\\;\\text{{本实验不计}} $$
        """, unsafe_allow_html=True)

