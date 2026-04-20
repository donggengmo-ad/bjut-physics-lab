import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import sympy as sp
import plotly.express as px
from plotly.graph_objs.layout.scene import xaxis
from scipy.stats import linregress


class Experiment:
    def __init__(self):
        self.name = "实验二：金属弹性模量测量"
        self.description = """
            ##### 数据说明：  
            -  
            ##### 注意事项：  
            - 
        """
        # 数据表
        self.key = ['金属丝直径', 'RLb', '望远镜标尺读数']
        self.d0 = 0
        self.initial_df = {
            '金属丝直径':pd.DataFrame({
                '测量次数': [i + 1 for i in range(6)],
                'di': [0.771, 0.771, 0.769, 0.770, 0.770, 0.771],
            }),
            'RLb':pd.DataFrame({
                '测量量': ['L','dL','R','dR','b','db','m','dm' ],
                '测量值': [402.0, 5, 1030, 20, 40.0, 0.5, 1000, 0.03],
            }),
            '望远镜标尺读数':pd.DataFrame({
                '测量次数':[i + 1 for i in range(10)],
                '砝码质量':[i for i in range(10)],
                'ni':[3.65, 4.15, 4.55, 5.05, 5.45, 5.85, 6.35, 6.85, 7.20, 7.65],
                'ni#':[3.70, 4.15, 4.60, 5.10, 5.55, 6.00, 6.45, 6.90, 7.40, 7.85],
            })
        }
        self.calc_df = {
            '望远镜标尺读数':pd.DataFrame({
                '测量次数': [i + 1 for i in range(10)],
                '平均ni': [0] * 10,
                '逐差值': [0] * 10,
            }),
            '金属丝直径':pd.DataFrame({
                '测量次数': [i + 1 for i in range(6)],
                'di-d0': [0] * 6,
            }),
            'RLb': pd.DataFrame({
                '测量量': ['L', 'dL', 'R', 'dR', 'b', 'db', 'm', 'dm'],
            }),
        }
        self.static_col = {'金属丝直径':['测量次数'], '望远镜标尺读数':['测量次数'], 'RLb':['测量量']}
        self.index = {key:self.static_col[key][0] for key in self.key}
        self.final_df = {
            key:self.initial_df[key].set_index(self.index[key]).join(self.calc_df[key].set_index(self.index[key]))
            for key in self.key
        }

    def set_initial_df(self, initial_df: pd.DataFrame, key: str):
        self.initial_df[key] = initial_df

    def fill_data(self):
        self.d0 = st.slider(label='d0', step=0.001, format='%.3f',
                            min_value=-0.05, max_value=0.05, value=-0.019)
        # 写表格计算逻辑
        key = '望远镜标尺读数'
        df = self.initial_df[key].set_index(self.index[key]).join(self.calc_df[key].set_index(self.index[key]))
        df['平均ni'] = round((df['ni'] + df['ni#']) / 2, 2)
        idxs = df[df['砝码质量'] < 5].index
        df['逐差值'] = [df.loc[idx + 5, '平均ni'] - df.loc[idx, '平均ni'] for idx in idxs] + [0] * 5
        self.final_df[key] = df

        key = '金属丝直径'
        df = self.initial_df[key].set_index(self.index[key]).join(self.calc_df[key].set_index(self.index[key]))
        df['di-d0'] = df['di'] - self.d0
        self.final_df[key] = df

    def calculate(self):
        # 计算
        df_d = self.final_df['金属丝直径']
        df_n = self.final_df['望远镜标尺读数']
        df_rlb = self.final_df['RLb']
        E, d_mean, n_mean = sp.symbols('\\bar{E} \\bar{d} \delta_n')
        F, L, R, b = sp.symbols('F L R b')
        E = 16 * F * R * L / (sp.pi * b * d_mean ** 2 * n_mean)

        E_dict = {F : 9.8,
            L : df_rlb.loc['L', '测量值'] * 1e-3,
            R : df_rlb.loc['R', '测量值'] * 1e-3,
            b : df_rlb.loc['b', '测量值'] * 1e-3,
            d_mean : df_d['di-d0'].mean() * 1e-3,
            n_mean : df_n['逐差值'].mean() / 5 * 2 * 1e-2,
            sp.pi : 3.141}
        E_nums = E.subs(E_dict)
        E_nums = round(E_nums / 1e11, 2)

        st.markdown(f"""
             #### 1.计算弹性模量
             ##### 原始公式
             $$ \\bar d = \\frac{{1}}{{6}} \sum_i^6 d_i$$
             
             $$ \\bar \delta_{{n'_i}} = \\frac{{1}}{{5}} \sum_{{i=1}}^5 \delta_{{n'_i}}$$
             
             $$ \delta_n = \\frac{{1}}{{5}} \\bar \delta_{{n'_i}} $$

             $$ \\bar E = {sp.latex(E)} $$

             ##### 带入数据
             $$ \\bar d = {round(df_d['di-d0'].mean(), 3)} mm$$
             
             $$ \\bar \delta_{{n'_i}} = {round(df_n['逐差值'].mean() * 2, 2)} cm$$
             
             $$ \delta_n = {round(df_n['逐差值'].mean() / 5 * 2, 2)} cm$$
             
             $$ \\bar E = {E_nums}  \\times 10^{{11}} Pa$$

             <br>
        """, unsafe_allow_html=True)

        d = sp.symbols('d', cls=sp.IndexedBase)
        i, six = sp.symbols('i 6')
        Sd = sp.sqrt(sp.summation((d[i] - d_mean)**2, (i, 1, six)) / 5)
        Sd_dict = {
            d:{j + 1: di * 1e-3 for j, di in enumerate(df_d['di-d0'])},
            d_mean:df_d['di-d0'].mean() * 1e-3,
        }
        d_mean_num = df_d['di-d0'].mean()
        Sd_nums = np.sqrt(pd.Series([(di - d_mean_num)**2 for di in df_d['di-d0']]).sum() / 5)
        Sd_nums = round(Sd_nums, 6)

        sd, dyi = sp.symbols('S_d \Delta_{\\text{仪}}')
        dd = sp.sqrt(sd ** 2 + dyi ** 2)
        dd_num = dd.subs({sd:Sd_nums, dyi:0.004})
        dd_num = round(dd_num, 6)

        dn, dnm = sp.symbols('\delta_{n\'_i} \\bar{\delta_{n\'_i}}', cls=sp.IndexedBase)
        five = sp.symbols('5')
        sdel = sp.sqrt(sp.summation((dn - dnm) ** 2, (i, 1, five)) / 4)
        dnm_num = df_n['逐差值'].mean() * 2
        sdel_num = np.sqrt(pd.Series([(dn_num - dnm_num)**2 for dn_num in df_n['逐差值'] if not dn_num == 0]).sum() / 4)
        sdel_num = round(sdel_num, 4)

        sdel_sm = sp.symbols('S_{\delta_{n\'}}')
        ddel = sp.sqrt(sdel_sm ** 2 + dyi ** 2)
        ddel_num = ddel.subs({sdel_sm:sdel_num, dyi:0.03})
        ddel_num = round(ddel_num, 4)

        st.markdown(f"""
            #### 2.计算直接测量量的不确定度
            ##### 原始公式
            $$ S_d = {sp.latex(Sd)} $$
            
            $$ \Delta_d = {sp.latex(dd)} $$
            
            $$ \S_{{\delta{{n'_i}}}} = {sp.latex(sdel)} $$
            
            $$ \Delta_{{\delta{{n'_i}}}} = {sp.latex(ddel)} $$

            ##### 带入数据
            $$ S_d = {Sd_nums} mm$$

            $$ \Delta_d = {dd_num} mm$$
            
            $$ S_{{\delta{{n'_i}}}} = {sdel_num} mm$$
            
            $$ \Delta_{{\delta{{n'_i}}}} = {ddel_num} mm$$
                """, unsafe_allow_html=True)

        dL, dR, db, dm, m = sp.symbols('\Delta_L, \Delta_R, \Delta_b, \Delta_m, m')
        dd, ddn = sp.symbols('\Delta_d, \Delta_{\delta_n}')
        de = sp.sqrt((dL/L)**2 + (dR/R)**2 + (db/b) ** 2 + 4*(dd/d_mean)**2 + (ddn/n_mean)**2 + (dm/m)**2)
        de_dict = {
            L: df_rlb.loc['L', '测量值'] * 1e-3,
            dL: df_rlb.loc['dL', '测量值'] * 1e-3,
            R: df_rlb.loc['R', '测量值'] * 1e-3,
            dR: df_rlb.loc['dR', '测量值'] * 1e-3,
            b: df_rlb.loc['b', '测量值'] * 1e-3,
            db: df_rlb.loc['db', '测量值'] * 1e-3,
            m: df_rlb.loc['m', '测量值'] * 1e-3,
            dm: df_rlb.loc['dm', '测量值'],
            d_mean: df_d['di-d0'].mean() * 1e-3,
            dd:dd_num * 1e-3,
            ddn:ddel_num / 5 * 1e-2,
            n_mean: df_n['逐差值'].mean() / 5 * 2 * 1e-2,
        }
        de_num = round(de.subs(de_dict), 6)

        st.markdown(f"""
                    #### 3.计算间接测量量的不确定度
                    ##### 原始公式
                    $$ \\frac{{\Delta_E}}{{E}} = {sp.latex(de)} $$

                    ##### 带入数据
                    $$ \\frac{{\Delta_E}}{{E}} = {de_num} $$
                    
                        """, unsafe_allow_html=True)

        de_fin = round(E_nums * de_num, 4)
        st.markdown(f"""
                    #### 4.结果表示
                    ##### 原始公式
                    $$ \Delta_E = E \\times \\frac{{\Delta_E}}{{E}} $$
                    
                    $$ E = \\bar E \pm \Delta_E $$

                    ##### 带入数据
                    $$ \Delta_E = {E_nums} \\times 10^{{11}} \\times {de_num} = {de_fin} \\times 10^{{11}} Pa $$
                    
                    $$ E = \left( {E_nums} \pm {de_fin} \\right) \\times 10^{{11}} Pa$$

                        """, unsafe_allow_html=True)

    def plot(self):
        df = self.final_df['望远镜标尺读数'].copy()
        st.subheader('')
        x = df['砝码质量']
        y = df['ni']
        res = linregress(x, y)
        k = res.slope
        b = res.intercept
        y_fit = k * x + b
        fig = px.scatter(x=x, y=y, labels={'x':'砝码质量 (g)', 'y':'ni (cm)'}, title='望远镜读数与砝码质量关系')
        fig.add_trace(px.line(x=x, y=y_fit).data[0])
        eq_text = f'y={k:.3f}x+{b:.3f}'
        fig.add_annotation(
            x=0.5, y=0.95, xref='paper', yref='paper',
            text=eq_text, showarrow=False, font=dict(size=16)
        )
        #fig.update_layout(title='拟合直线', xaxis_title='砝码质量 (g)', yaxis_title='ni (cm)')
        st.plotly_chart(fig)
