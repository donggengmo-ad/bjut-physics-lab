import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt


class Experiment:
    def __init__(self):
        self.name = "实验八：牛顿环测透镜曲率半径"
        self.description = """
            ##### 数据说明：  
            - 报告册上m 对应 50 > 环的级别 > 45
            - 报告册上n 对应20 > 环的级别 > 15
            - 左、右：环的位置
            - d：50 > 环的级别 > 45 时表示dm；20 > 环的级别 > 15 时表示dn
            - dm2-dn2：$$ dm^2 - dn^2 $$ ，只在m范围内有意义
            ##### 注意事项：  
            - 初始值是我当时测的，仅供参考，可能不准
        """
        # 数据表
        self.initial_df = pd.DataFrame({
            '环的级别':[50, 49, 48, 47, 46, 45, 20, 19, 18, 17, 16, 15],
            '左':[30.659, 30.600, 30.549, 30.496, 30.435, 30.372, 28.691, 28.610, 28.522, 28.438, 28.345, 28.252],
            '右':[19.375, 19.430, 19.482, 19.545, 19.590, 19.658, 21.339, 21.417, 21.502, 21.580, 21.681, 21.767],
        })
        self.calc_df = pd.DataFrame({
            '环的级别':[50, 49, 48, 47, 46, 45, 20, 19, 18, 17, 16, 15],
            'd':[0] * 12,
            'dm2-dn2':[0] * 12
        })
        self.static_col = ['环的级别']
        self.final_df = self.initial_df.set_index('环的级别').join(self.calc_df.set_index('环的级别'))

    def set_initial_df(self, initial_df: pd.DataFrame):
        self.initial_df = initial_df

    def fill_data(self):
        # 写表格计算逻辑
        df = self.initial_df.set_index('环的级别').join(self.calc_df.set_index('环的级别')).reset_index()

        df['d'] = df['左'] - df['右']

        dm2 = [df[df['环的级别'] == lev]['d'].to_numpy() ** 2 for lev in df['环的级别'] if lev >= 30]
        dn2 = [df[df['环的级别'] == lev - 30]['d'].to_numpy() ** 2 for lev in df['环的级别'] if lev >= 30]
        d_list = [float((dm2[i] - dn2[i]).squeeze()) for i in range(len(dm2))]
        df['dm2-dn2'] = d_list + [0] * 6

        df = df.apply(lambda x: round(x, 3))

        self.final_df = df

    def calculate(self):
        # 平均值
        df = self.final_df.copy()
        d_series = df[df['dm2-dn2'] != 0]
        d_mean = round(d_series.mean()[-1], 3)

        st.markdown(f"""
             #### 1.逐差法求$d_m^2-d_n^2$
             
             略
             *（我们老师没要求写过程，所以我就不写了，哈哈，不过表格里面有结果）*
             
             $$\overline{{d_m^2 - d_n^2}} = {d_mean} mm^2$$

             <br>
        """, unsafe_allow_html=True)

        # 曲率半径
        R = round(d_mean / (120 * 589.3 * 1e-6), 2)
        tempR = R
        dig = 0
        while tempR >= 10:
            tempR = round(tempR / 10, 2)
            dig += 1
        scR = f'{round(R / 10**dig, 2)} × 10^{dig}'

        st.markdown(f"""
            #### 2.计算平凸透镜曲率半径平均值
            ##### 原始公式
            $$ \\bar R = \\frac{{\overline{{d_m^2 - d_n^2}}}}{{4(m-n) \lambda}} $$

            ##### 代入数据
            $$ \\bar R = \\frac{{{d_mean}}}{{4 \\times 30 \\times 589.3 \\times 10^{{-6}}}} = {R} mm = {scR} mm$$
            
            *（这里老师建议我们写成科学计数法，保留三位有效数字，所以我多写了一步）*
            
            <br>
                """, unsafe_allow_html=True)

        # 不确定度
        dm = [df[df['环的级别'] == lev]['d'].to_numpy().item() for lev in df['环的级别'] if lev >= 30]
        dn = [df[df['环的级别'] == lev - 30]['d'].to_numpy().item() for lev in df['环的级别'] if lev >= 30]

        dm2_dn2 = df[df['dm2-dn2'] != 0]['dm2-dn2'].to_numpy()
        d_dm2_dn2 = [(dm2_dn2[i] - d_mean)**2 for i in range(len(dm))]

        d_dm2_dn2 = pd.Series(d_dm2_dn2).sum() / 5
        d_dm2_dn2 = np.sqrt(d_dm2_dn2)
        d_dm2_dn2 = round(d_dm2_dn2, 2)

        stdsums = ' + '.join([f'\left[({dm[i]}^2 - {dn[i]}^2) - {d_mean} \\right]^2' for i in range(len(dm))])
        dr_r = (0.2/589.3)**2 + (1/30)**2 * 0.02 + (d_dm2_dn2 / d_mean)**2
        dr_r = np.sqrt(dr_r) * 100
        dr_r = round(dr_r, 2)

        d_r = R * dr_r / 100
        d_r = round(d_r, 2)

        st.markdown(f"""
            #### 3.不确定度的估算
            ##### 原始公式
            $$ \Delta_{{(d_m^2-d_n^2)}} = \sqrt{{\\frac{{1}}{{n-1}} \sum_{{i=1}}^{{n}} [(d_m^2-d_n^2)_i - (\overline{{d_m^2 - d_n^2}})]^2}} $$
            
            $$ \\frac{{\Delta_R}}{{R}} = \sqrt{{ \left (\\frac{{\Delta_\lambda}}{{\lambda}} \\right)^2 + (\\frac{{1}}{{m-n}})^2(\Delta_m^2+\Delta_n^2) + \left[\\frac{{\Delta_{{(d_m^2-d_n^2)}} }}{{ \overline{{d_m^2-d_n^2}} }} \\right]^2 }} $$
            
            $$ \Delta_R = \\bar R \cdot \\frac{{\Delta_R}}{{R}} $$
            
            $$ R = \\bar R \pm \Delta_R $$
            
            ##### 代入数据
            $$ \Delta_{{(d_m^2-d_n^2)}} = \sqrt{{ \\frac{{1}}{{5}} \left( {stdsums} \\right) }} \\\\= {d_dm2_dn2} mm^2 $$
            
            $$ \\frac{{\Delta_R}}{{R}} = \sqrt{{ \left (\\frac{{0.2}}{{589.3}} \\right)^2 + (\\frac{{1}}{{30}})^2(0.1^2+0.1^2) + \left(\\frac{{ {d_dm2_dn2} }}{{ {d_mean} }} \\right)^2 }} \\\\= {dr_r} \% $$
            
            $$ \Delta_R = {R} \\times {dr_r} \% =  {d_r} mm $$
            
            $$ R = {scR} \pm {d_r} mm $$
        """, unsafe_allow_html=True)




