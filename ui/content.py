import streamlit as st


def render_document(document):
    for block in document.blocks:
        if block.kind == 'table':
            st.table(block.body, hide_index=True)
        elif block.kind == 'latex':
            st.latex(block.body)
        elif block.kind == 'markdown':
            st.markdown(block.body)
        elif block.kind == 'caption':
            st.caption(block.body)
        elif block.kind == 'info':
            st.info(block.body, icon=':material/info:')
        elif block.kind == 'warning':
            st.warning(block.body, icon=':material/warning:')


def render_tables(tables):
    for table in tables:
        st.markdown(f'**{table.title}**')
        if table.math:
            st.table(table.frame, hide_index=True)
        else:
            st.dataframe(table.frame, hide_index=True, width='stretch')
