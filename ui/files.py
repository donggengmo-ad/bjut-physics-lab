import streamlit as st
from core.files import backup_bytes, csv_bytes, read_backup, read_csv, result_archive
from experiments import get_spec
from ui.state import get_session


@st.dialog('替换当前数据', width='small')
def confirm_replace(experiment_id, action, candidate=None, table_id=None):
    session = get_session(experiment_id)
    spec = get_spec(experiment_id)
    st.write(f'将{action}。当前实验对应的输入会被替换，其他实验保持不变。')
    st.caption('如需保留当前记录，请先取消并导出完整实验。')
    with st.container(horizontal=True):
        if st.button('确认替换', type='primary', icon=':material/check:', key=f'{spec.id}:confirm'):
            if table_id is not None:
                session.import_table(table_id, candidate)
            else:
                session.replace(candidate)
            st.session_state['lab_notice'] = f'已{action}。'
            st.rerun()
        if st.button('取消', key=f'{spec.id}:cancel'):
            st.rerun()


def render_files(spec, session):
    with st.container(horizontal=True):
        with st.popover('导入', icon=':material/upload:'):
            st.caption('CSV 替换一张输入表；JSON 恢复当前实验的完整草稿。')
            uploaded = st.file_uploader('选择 CSV 或完整实验 JSON', type=['csv', 'json'], key=f'{spec.id}:upload', max_upload_size=10)
            table_id = st.selectbox('CSV 对应的输入表', [t.id for t in spec.tables], key=f'{spec.id}:import_table')
            if st.button('检查并导入', disabled=uploaded is None, key=f'{spec.id}:import'):
                try:
                    data = uploaded.getvalue()
                    if uploaded.name.lower().endswith('.json'):
                        candidate = read_backup(spec, data)
                        confirm_replace(spec.id, '恢复完整实验', candidate)
                    else:
                        candidate = read_csv(spec, table_id, data, session.inputs)
                        confirm_replace(spec.id, f'导入「{table_id}」', candidate, table_id)
                except ValueError as error:
                    st.error(str(error))
        with st.popover('导出', icon=':material/download:'):
            st.caption('完整实验包含表格、参数、人工覆盖值和数据来源，可用于恢复。')
            if st.button('准备备份与 CSV', key=f'{spec.id}:prepare_files'):
                session.exports['backup'] = backup_bytes(spec, session.inputs)
                for index, table in enumerate(spec.tables):
                    session.exports[f'input:{index}'] = csv_bytes(session.inputs.tables[table.id])
                if session.result is not None:
                    session.exports['results'] = result_archive(session.result)
                session.prepared_revision = session.inputs.revision
            if session.prepared_revision == session.inputs.revision:
                st.download_button('下载完整实验', session.exports['backup'], file_name=f'{spec.id}.json', mime='application/json', on_click='ignore', key=f'{spec.id}:backup:{session.inputs.revision}', icon=':material/save:')
                for index, table in enumerate(spec.tables):
                    st.download_button(f'输入 CSV · {table.title}', session.exports[f'input:{index}'], file_name=f'{spec.id}_{index+1}_输入.csv', mime='text/csv', on_click='ignore', key=f'{spec.id}:csv:{index}:{session.inputs.revision}')
                if 'results' in session.exports and session.result is not None:
                    st.download_button('下载全部结果 CSV（ZIP）', session.exports['results'], file_name=f'{spec.id}_结果.zip', mime='application/zip', on_click='ignore', key=f'{spec.id}:results:{session.inputs.revision}')
            else:
                st.caption('按当前输入准备文件后下载；编辑数据后需重新准备。')
        if st.button('载入示例', icon=':material/science:', key=f'{spec.id}:example'):
            confirm_replace(spec.id, '载入默认示例', spec.initial_state())
        if st.button('清空', icon=':material/restart_alt:', key=f'{spec.id}:clear'):
            confirm_replace(spec.id, '清空测量值并恢复参数默认值', spec.initial_state(blank=True))
