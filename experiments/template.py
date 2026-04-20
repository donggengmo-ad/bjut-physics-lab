import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt


class Experiment:
    def __init__(self):
        self.name = "实验X：XXX"
        self.description = """
            ##### 数据说明：  
            -  
            ##### 注意事项：  
            - 
        """
        # 数据表
        self.key = 'key'
        self.initial_df = {
            self.key:pd.DataFrame({
                '测量次数': [i + 1 for i in range(6)],
                'XX': [],
            })
        }
        self.calc_df = pd.DataFrame({
            '测量次数': [i + 1 for i in range(6)],
            'XX':[]
        })
        self.static_col = {self.key:['测量次数']}
        self.index = self.static_col[0]
        self.final_df = {self.key:self.initial_df[self.key].set_index(self.index).join(self.calc_df.set_index(self.index))}

    def set_initial_df(self, initial_df: pd.DataFrame, key: str):
        self.initial_df[key] = initial_df

    def fill_data(self):
        # 写表格计算逻辑
        df = self.initial_df[self.key].set_index(self.index).join(self.calc_df.set_index(self.index))

        self.final_df[self.key] = df

    def calculate(self):
        # 计算

        # 显示
        st.markdown(f"""
             #### 1.计算
             ##### 原始公式
             $$ $$

             $$ $$

             ##### 带入数据
             $$ $$

             $$ $$

             <br>
        """, unsafe_allow_html=True)

        st.markdown(f"""
            #### 2.计算
            ##### 原始公式
            $$ $$

            $$ $$

            ##### 带入数据
            $$ $$

            $$ $$
                """, unsafe_allow_html=True)

    def plot(self):
        df = self.final_df[self.key].copy()
        st.subheader('')
        fig, ax = plt.subplots()


