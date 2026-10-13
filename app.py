"""BJUT 物理实验工作台入口：streamlit run app.py。"""
import streamlit as st
from experiments import EXPERIMENTS

st.set_page_config(page_title='BJUT 物理实验工作台', page_icon=':material/science:',
                   layout='wide', initial_sidebar_state='expanded')
st.sidebar.title('物理实验工作台')
st.sidebar.caption('BJUT · 数据处理与实验记录')
pages = {volume: [st.Page(f'app_pages/{entry.id}.py', title=f'{entry.number:02d} · {entry.title}',
                         icon=f':material/{entry.icon}:', url_path=entry.id,
                         default=entry.id == EXPERIMENTS[0].id)
                  for entry in EXPERIMENTS if entry.volume == volume]
         for volume in ('上册','下册')}
page = st.navigation(pages, position='hidden')
with st.sidebar:
    for volume, entries in pages.items():
        st.caption(volume)
        for entry in entries:
            st.page_link(entry, icon=entry.icon)
    st.divider()
    with st.expander('使用说明'):
        st.write('编辑提交后自动计算；结果、推导和图表按需查看。切换实验保留当前会话草稿。')
        st.write('关闭会话或刷新前，请导出完整实验 JSON；下次从“导入”恢复。CSV 用于单张原始表。')
        st.caption('示例用于演示，请按自己的实验记录替换。')
    st.link_button('使用反馈', 'https://wj.qq.com/s2/26323333/b51a/', icon=':material/feedback:')
    st.caption('作者：Alex Dong')
page.run()
