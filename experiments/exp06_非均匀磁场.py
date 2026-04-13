import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import plotly.express as px


class Experiment:
    def __init__(self):
        self.name = "实验六：非均匀磁场测量"
        self.description = """
            ##### 数据说明：  
            - x：距原点距离，单位cm
            - Um：毫伏表读数，单位mV
            - Bm测、Bm计、Er与实验报告一一对应
            ##### 注意事项：  
            - 表格里Er是小数，显示计算时乘以100%了，注意区分
            - Bm测与Bm计的单位是 $10 ^ {{-5}} T$
            - 初始数据是我当时测的，很明显有问题，不要用！！我这节课作业才得6分orz
        """
        # 数据表
        self.initial_df = pd.DataFrame({
            'x':[i for i in range(10)],
            'Um':[66.5, 65.5, 62.7, 58.5, 53.4, 47.8, 37.0, 32.3, 28.1, 24.5],
        })
        self.calc_df = pd.DataFrame({
            'x':[i for i in range(10)],
            'Bm测':[0.0] * 10,
            'Bm计':[0.0] * 10,
            'Er':[0.0] * 10
        })
        self.static_col = ['x']
        self.index = 'x'
        self.final_df = self.initial_df.set_index(self.index).join(self.calc_df.set_index(self.index))

    def set_initial_df(self, initial_df: pd.DataFrame):
        self.initial_df = initial_df

    def fill_data(self):
        # 写表格计算逻辑
        df = self.initial_df.set_index(self.index).join(self.calc_df.set_index(self.index)).reset_index()

        for i, (Um, x) in enumerate(zip(df['Um'], df['x'])):
            BmCe = (Um * 1e-3) * 5.958 * 1e-4 / (6100 * ((11.7 * 1e-3) ** 2)) * 1e5
            BmJi = 12.57 * 1e-7 * 6100 * 0.01 * 1e-3 / (np.sqrt(2) * (0.01 + (x * 1e-2) ** 2) ** (3 / 2)) * 1e5
            Er = abs(BmCe - BmJi) / BmJi * 100

            df.loc[i, 'Bm测'] = round(BmCe, 2)
            df.loc[i, 'Bm计'] = round(BmJi, 2)
            df.loc[i, 'Er'] = round(Er/100, 3)

        self.final_df = df.set_index(self.index)

    def calculate(self):
        # 计算
        samp = self.final_df.reset_index().loc[1].copy() # 只显示一个
        Er = round(samp['Er'] * 100, 1)
        Er = f'{Er:.1f}'

        # 显示
        st.markdown(f"""
             #### 计算Bm测，Bm记录和Er
             ##### 原始公式
             $$ B_{{m_测}} = 5.958 \\times 10^{{-4}} \\cdot \\frac{{U_m}}{{Nd_0^2}} $$

             $$ B_{{m_计}} = \\frac {{\mu_0 N_0 \\bar R^2 I}} {{ \sqrt{{2}} \left(\\bar R^2 + x^2 \\right)^{{\\frac{{3}}{{2}} }} }} $$

             $$ E_r = \\frac{{ |B_{{m_测}} - B_{{m_计}}| }}{{B_{{m_计}}}} \\times 100 \% $$

             ##### 带入数据
             $$ B_{{m_测}} = 5.958 \\times 10^{{-4}} \\times \\frac{{{samp['Um']} \\times 10^{{-3}}}}{{6100 \\times (11.7 \\times 10^{{-3}})^2}} = {samp['Bm测']:.2f} \\times 10^{{-5}} T $$
                
             $$ B_{{m_计}} = \\frac {{12.57 \\times 10^{{-7}} \\times 6100 \\times 0.1^2 \\times 1 \\times 10^{{-3}}}} {{ \sqrt{{2}} \left(0.1^2 + {samp['x']}^2 \\right)^{{\\frac{{3}}{{2}} }} }} = {samp['Bm计']:.2f} \\times 10^{{-5}} T $$
                
             $$ E_r = \\frac{{ |{samp['Bm测']} - {samp['Bm计']}| }}{{{samp['Bm计']}}} \\times 100 \% = {Er} 100 \% $$

            *（老师说写一个就可以，所以这里只显示x=1时的数据啦）*
             <br>
        """, unsafe_allow_html=True)

    def plot(self):
        df = self.final_df.copy().reset_index()
        fig = px.line(df, x='x', y=['Bm测', 'Bm计'], title='Bm-x曲线图', markers=True)

        st.plotly_chart(fig)
