import streamlit as st
from core.formatting import default_tables
from core.validation import measurement_counts
from experiments import get_spec
from ui.content import render_document, render_tables
from ui.files import render_files
from ui.inputs import render_inputs
from ui.state import get_session


def render_experiment(experiment_id):
    spec = get_spec(experiment_id)
    session = get_session(experiment_id)
    definitions = st.session_state.setdefault('lab_compute_definitions', {})
    if definitions.get(experiment_id) is not spec.compute:
        # 热更新计算定义后重算已有草稿，避免旧结果表结构进入新的展示函数。
        session.evaluated_revision = -1
        definitions[experiment_id] = spec.compute
    st.caption(f'{spec.volume} / 实验 {spec.number:02d}')
    st.title(spec.title)
    st.write(spec.introduction)
    status = st.empty()
    toolbar = st.container()
    render_inputs(spec, session)
    session.evaluate(spec)
    status.caption(f'{session.source_label} · {session.status} · 草稿保留于当前会话')
    with toolbar:
        render_files(spec, session)
    if 'lab_notice' in st.session_state:
        st.toast(st.session_state.pop('lab_notice'), icon=':material/check_circle:')
    st.subheader('计算结果')
    for issue in session.issues[:20]:
        (st.error if issue.severity == 'error' else st.warning)(str(issue))
    if len(session.issues) > 20:
        st.caption(f'另有 {len(session.issues) - 20} 处问题；修正上列问题后继续检查。')
    if session.result is not None:
        present, total = measurement_counts(spec, session.normalized)
        st.caption(f'已填写 {present} / {total} 个测量值 · {session.status}')
        if session.status == '未填写':
            st.info('填写原始测量值后显示可用结果。空白项不会用示例或理论值补齐。', icon=':material/edit_note:')
        for note in session.result.notes:
            st.caption(note)
        if session.result.summary:
            with st.container(horizontal=True):
                for metric in session.result.summary[:4]:
                    with st.container(width=260):
                        st.metric(metric.label, f'{metric.value} {metric.unit}'.strip())
    names = ['结果表格', '计算过程']
    if spec.build_plot is not None:
        names.append('图表')
    names.append('实验说明')
    tabs = st.tabs(names, default=session.active_view, key=f'{spec.id}:view', on_change='rerun')
    for name, tab in zip(names, tabs):
        if not tab.open:
            continue
        session.active_view = name
        with tab:
            if name == '实验说明':
                st.markdown(spec.description)
                if spec.discussion:
                    st.markdown('**思考题**')
                    st.markdown(spec.discussion)
            elif session.result is None:
                st.info('修正当前输入后，此处会显示对应的新结果。')
            elif name == '结果表格':
                tables = (spec.format_tables(session.normalized, session.result) if spec.format_tables
                          else default_tables(session.normalized, session.result))
                render_tables(tables)
            elif name == '计算过程':
                render_document(spec.explain(session.normalized, session.result))
            elif name == '图表':
                from ui.charts import render_chart
                render_chart(spec, session)
