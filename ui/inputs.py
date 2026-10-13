import math
import pandas as pd
import streamlit as st
from ui.state import editor_key, parameter_key


def render_inputs(spec, session):
    if spec.parameters:
        st.subheader('实验参数')
        with st.container(horizontal=True, vertical_alignment='bottom'):
            for parameter in spec.parameters:
                key = parameter_key(spec.id, parameter.id, session.parameter_generation)
                value = session.inputs.parameters[parameter.id]
                with st.container(width=235):
                    invalid_number = parameter.kind == 'number' and (isinstance(value, (str, bool)) or value is not None and (not math.isfinite(value) or parameter.minimum is not None and value < parameter.minimum or parameter.maximum is not None and value > parameter.maximum))
                    if parameter.kind == 'text' or invalid_number:
                        edited = st.text_input(parameter.label, value='' if value is None else str(value), key=key, help='请修正备份中的无效参数。' if invalid_number else parameter.help or None)
                    else:
                        edited = st.number_input(parameter.label, value=None if value is None else float(value), key=key,
                            min_value=parameter.minimum, max_value=parameter.maximum,
                            step=parameter.step, format=parameter.format,
                            help=parameter.help or None, placeholder='留空时自动计算' if 'mean_' in parameter.id else '填写测量值')
                session.edit_parameter(parameter.id, edited)
    st.subheader('原始数据')
    st.caption('双击单元格编辑，按 Enter 或 Tab 提交后即时更新。固定行标识不可修改。')
    for index, table in enumerate(spec.tables):
        key = editor_key(spec.id, index, session.generations[table.id])
        if key not in st.session_state:
            session.editor_sources[table.id] = session.inputs.tables[table.id].copy(deep=True)
        source = session.editor_sources[table.id]
        config = {}
        for column in table.columns:
            if column.kind == 'number':
                numeric = pd.to_numeric(source[column.name], errors='coerce')
                invalid_text = source[column.name].notna() & (~numeric.map(lambda v: math.isfinite(v)))
                if invalid_text.any():
                    source[column.name] = source[column.name].map(lambda v: None if pd.isna(v) else str(v))
                    config[column.name] = st.column_config.TextColumn(column.label, help='请修正此列中的无效数值。')
                else:
                    source[column.name] = numeric
                    config[column.name] = st.column_config.NumberColumn(column.label, format=column.format,
                        min_value=column.minimum, max_value=column.maximum, help=column.help)
            else:
                source[column.name] = source[column.name].map(lambda v: None if pd.isna(v) else str(v))
                config[column.name] = st.column_config.TextColumn(column.label, help=column.help)
        with st.container(border=True):
            st.markdown(f'**{table.title}**')
            if table.help:
                st.caption(table.help)
            edited = st.data_editor(source, key=key, hide_index=True, column_config=config,
                disabled=list(table.fixed_columns), width='stretch',
                height=min(395, 35 * (len(source) + 1) + 3),
                num_rows='dynamic' if table.variable_rows and not table.fixed_columns else 'fixed')
            session.edit_table(table.id, edited)
            st.caption(f'来源：{session.inputs.sources[table.id]}')
