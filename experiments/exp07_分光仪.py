import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt

class Experiment:
    def __init__(self):
        self.name = "实验七：分光计的调节和使用"
        self.description = """
            ##### 数据说明：  
            - AB1：游标I 测出的 AB面法线theta角  
            - AB2：游标II 测出的 AB面法线theta角  
            - AC1：游标I 测出的 AC面法线theta角  
            - AC2：游标II 测出的 AC面法线theta角  
            - phi1：AB1 + 360 - AC1  
            - phi2：AB2 - AC2  
            - phi：1/2 * (phi1 + phi2)  
            ##### 注意事项：  
            - 填入浮点数 x.y 表示 x度y分，例如 30.15 表示 30度15分  
            - 注意填入顺序，数值大概是 AB1 < AC2 < AB2 < AC1，可能跟你实际测量结果顺序不一样
            - 初始值是我当时测的，仅供参考，可能不准
        """
        # 数据表
        self.initial_df = pd.DataFrame({
            '测量次数': [i + 1 for i in range(6)],
            'AB1':[56.12, 56.09, 56.10, 56.13, 56.12, 56.13],
            'AB2':[236.06, 236.04, 236.05, 236.08, 236.06, 236.08],
            'AC1':[296.05, 296.07, 296.06, 296.05, 296.09, 296.06],
            'AC2':[116.05, 116.08, 116.08, 116.06, 116.13, 116.08],
        })
        self.calc_df = pd.DataFrame({
            '测量次数': [i + 1 for i in range(6)],
            'phi1': [0] * 6,
            'phi2': [0] * 6,
            'phi': [0] * 6
        })
        self.static_col = ['测量次数']
        self.final_df = self.initial_df.set_index('测量次数').join(self.calc_df.set_index('测量次数'))
        # 其他数值
        self.result = None

    def set_initial_df(self, initial_df: pd.DataFrame):
        self.initial_df = initial_df

    def fill_data(self):
        # 写表格计算逻辑
        df = self.initial_df.set_index('测量次数').join(self.calc_df.set_index('测量次数'))
        df = Experiment.df_deg_to_float(df)

        df['phi1'] = df['AB1'] - df['AC1'] + 360
        df['phi2'] = df['AB2'] - df['AC2']
        df['phi'] = 1 / 2 * (df['phi1'] + df['phi2'])

        df = Experiment.df_float_to_deg(df)

        df['phi'] = round(df['phi'], 2)

        self.final_df = df
        return df

    def calculate(self):
        def to_circ_str(x:float|int)->str:
            return f'{int(x)} ^\circ {int(round((x - int(x))* 100, 0))}' if x >=1 else f'{int(round((x - int(x))* 100, 0))}\''

        # 平均值
        f_df = Experiment.df_deg_to_float(self.final_df)
        m = f_df['phi'].mean()
        m = Experiment.float_to_deg(m)
        m = round(m, 2)
        m_circ = to_circ_str(m)

        m = Experiment.deg_to_float(m)
        A = 180 - m
        A = Experiment.float_to_deg(A)
        A_circ = to_circ_str(A)

        phis = [phi for phi in self.final_df['phi']]
        sums_circ = ' + '.join([f'{to_circ_str(phi)}' for phi in phis])

        st.markdown(f"""
             #### 1.计算 $\\phi$ 角和 A 角
             ##### 原始公式
             $$\\bar\phi = \\frac{{1}}{{n}} \sum_{{i=1}}^{{n}}\phi_i$$
             
             $$A = 180\degree - \phi$$
             
             ##### 代入数据
             $$\\bar\phi = \\frac{{1}}{{6}} ({sums_circ}) = {m_circ}'$$
             
             $$A = 180\degree - {m_circ} = {A_circ}$$
             
             <br>
        """, unsafe_allow_html=True)

        # 不确定度
        s_phi = f_df['phi'].std()
        s_phi = Experiment.float_to_deg(s_phi)
        phi_circ = [to_circ_str(phi) for phi in phis]
        stdsums = ' + '.join([f'({phi}-{m_circ})^2' for phi in phi_circ])
        s_phi_circ = to_circ_str(s_phi)

        s_equip = Experiment.deg_to_float(0.01)
        s_phi = Experiment.deg_to_float(s_phi)

        d_phi = np.sqrt(s_phi ** 2 + s_equip ** 2)
        d_phi = Experiment.float_to_deg(d_phi)
        d_phi_circ = to_circ_str(d_phi)

        st.markdown(f"""
                     #### 2.计算A角不确定度
                     ##### 原始公式
                     $$S_\phi = \sqrt{{\\frac{{1}}{{n-1}} \sum_{{i=1}}^{{n}}(\phi_i-\\bar\phi)^2}}$$

                     $$\Delta_\phi = \sqrt{{S_\phi^2 + \Delta_仪^2}}$$

                     ##### 代入数据
                     $$S_\phi = \sqrt{{\\frac{{1}}{{5}} {stdsums}}}\\\\ = {s_phi_circ}$$

                     $$\Delta_\phi = \sqrt{{({s_phi_circ})^2 + (1')^2}} = {d_phi_circ}$$

                """, unsafe_allow_html=True)

    def plot(self):
        df = self.final_df.copy()
        st.subheader('')
        fig, ax = plt.subplots()

    @staticmethod
    def deg_to_float(x: float):
        x = int(x) + (x - int(x)) * 100 / 60
        # x = np.radians(x)
        return x
    @staticmethod
    def float_to_deg(x: float):
        # x = np.degrees(x)
        x = int(x) + (x - int(x)) * 60 / 100
        return x
    @staticmethod
    def df_deg_to_float(df: pd.DataFrame) -> pd.DataFrame:
        df = df.apply(lambda x: x.astype(int) + (x - x.astype(int)) * 100 / 60)
        # df = df.apply(np.radians)
        return df
    @staticmethod
    def df_float_to_deg(df: pd.DataFrame) -> pd.DataFrame:
        # df = df.apply(np.degrees)
        df = df.apply(lambda x: x.astype(int) + (x - x.astype(int)) * 60 / 100)
        return df
