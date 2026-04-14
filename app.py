import pandas as pd
import streamlit as st
from st_aggrid import aggrid_utils

from experiments import get_experiments
from st_aggrid import AgGrid, GridOptionsBuilder

# 页面配置
st.set_page_config(
    page_title = 'bjut物理实验数据处理平台',
    layout = 'wide',
    initial_sidebar_state = 'expanded'
)
st.markdown("""
<style>
    .main-header{
        font-size: 36px;
        font-weight: bold;
        color: #333;
        text-align: center;
        margin-bottom: 20px;
    }
    .selection-header{
        font-size: 26px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <div id="idy_floatdiv" 
            style="position:fixed;
                    display:flex;
                    right:0;
                    bottom:15%;
                    width:40px;
                    border-top-left-radius:6px;
                    border-bottom-left-radius:6px;
                    height:120px;
                    background:#2cd9e6;
                    line-height: 24px;
                    writing-mode:vertical-rl;
                    align-items:center;
                    justify-content:center;
                    font-family:PingFangSC-Regular;
                    font-size:20px;">
        <a href="https://wj.qq.com/s2/26323333/b51a/" 
            target="blank" 
            style="color:#ffffff;
            text-decoration:none;">
            留言
        </a>
    </div>
""", unsafe_allow_html=True)

# 侧边栏
st.sidebar.title('实验章节')
# 抽屉版
# selected_experiment = st.sidebar.selectbox('选择章节', experiments.keys())
# exp = experiments[selected_experiment]
# 目录版
with st.sidebar:
    experiments = get_experiments()
    exp_list = list(experiments.keys())
    if 'select_exp' not in st.session_state:
        st.session_state.select_exp = exp_list[0]
    for name in exp_list:
        if st.button(name):
            st.session_state.select_exp = name
            st.rerun()
selected_exp = st.session_state.select_exp
exp = experiments[selected_exp]

# 主界面
st.markdown(f"""
    <div class="main-header">{exp.name}</div>
""", unsafe_allow_html=True)
st.markdown(exp.description)

# 原始数据表
st.divider()
st.markdown(f"""
    <div class="selection-header">原始数据输入</div>
""", unsafe_allow_html=True)
st.info('双击表格单元格编辑数据')

upload_file = st.file_uploader(
    label="上传csv文件",
    type="csv",
    help="列名必须一致，且第一列必须是测量次数，数值格式必须是x.y表示x度y分",
    key='upload_initial_df'
)

if upload_file is not None:
    try:
        imported_df = pd.read_csv(upload_file)
        exp.initial_df = imported_df.drop(columns='Unnamed: 0')
    except Exception as e:
        st.error(f"出错了：{str(e)}")

gb = GridOptionsBuilder.from_dataframe(exp.initial_df)
gb.configure_default_column(editable=True, resizable=True,
                            sortable=True, filter = False,
                            cellStyle = {'textAlign': 'center'})
for col in exp.static_col:
    gb.configure_column(col, editable=False, cellStyle = {'textAlign': 'center', 'backgroundColor': '#f0f0f0'})
gb.configure_grid_options(domLayout='autoHeight')
grid_options = gb.build()
grid_response = AgGrid(
    exp.initial_df,
    gridOptions=grid_options,
    theme='streamlit',
    update_mode='VALUE_CHANGED',
)
exp.set_initial_df(grid_response['data'].copy())

csv = exp.initial_df.to_csv()
st.download_button(
    label='下载csv文件',
    data=csv,
    file_name=f'{exp.name}.csv',
    mime='text/csv',
    key='download_initial_df'
)

# 计算结果表
st.divider()
st.markdown(f"""
    <div class="selection-header">计算结果</div>
""", unsafe_allow_html=True)
try:
    exp.fill_data()
    st.dataframe(exp.final_df)

except Exception as e:
    st.error(f'出错了：{str(e)}')
    st.warning('请检查数据填写是否正确')

st.info('从表格右上角工具栏下载')


# 数据处理
st.divider()
st.subheader('数据处理')
try:
    exp.calculate()
except Exception as e:
    st.error(f'出错了：{str(e)}')
    st.warning('请检查数据填写是否正确')

# 画图
st.divider()
st.subheader('绘图')
try:
    exp.plot()
    st.info('从图片右上角工具栏下载')
except Exception as e:
    st.warning('本章节无需绘图')

# 页脚
st.sidebar.markdown("""
    <div style="text-align: center; color:#666;">
        <p>作者：Alex Dong</p>
    </div>
""", unsafe_allow_html=True)

# cd /Users/alexdong/Programme/bjut-physics-lab
# streamlit run app.py
