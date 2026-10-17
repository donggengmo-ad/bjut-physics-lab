"""按需图表和当前版本静态导出，不持有 Matplotlib Figure。"""
from io import BytesIO
import streamlit as st


def figure_bytes(figure, format):
    from core.fonts import apply_report_fonts, report_style
    buffer = BytesIO()
    with report_style():
        apply_report_fonts(figure)
        figure.savefig(buffer, format=format, dpi=200, facecolor='white', bbox_inches='tight')
    return buffer.getvalue()


def render_chart(spec, session):
    from core.fonts import report_fonts
    fonts = report_fonts()
    font_policy = ('song-times-v1\0' + '\0'.join(fonts.families)).encode()
    if session.exports.get('plot:font-policy') != font_policy:
        # 热更新字体规则后丢弃旧图片，避免相同输入仍下载到上一个字体版本。
        for key in list(session.exports):
            if key.startswith('plot:'):
                del session.exports[key]
        session.exports['plot:font-policy'] = font_policy
    if spec.plot_kind == 'matplotlib':
        if 'plot:preview' not in session.exports:
            figure = spec.build_plot(session.normalized, session.result)
            try:
                session.exports['plot:preview'] = figure_bytes(figure, 'png')
            finally:
                figure.clear()
        st.image(session.exports['plot:preview'], width='stretch')
    else:
        import plotly.io as pio
        if 'plot:json' not in session.exports:
            figure = spec.build_plot(session.normalized, session.result)
            for trace in figure.data:
                trace.x = list(trace.x)
                trace.y = list(trace.y)
            figure.update_layout(font={'size':14},colorway=['#2F81F7','#D55E00','#009E73'],
                                 legend={'orientation':'h','yanchor':'bottom','y':1.02,'xanchor':'left','x':0},
                                 margin={'l':50,'r':20})
            session.exports['plot:json'] = pio.to_json(figure).encode()
        figure = pio.from_json(session.exports['plot:json'].decode())
        st.plotly_chart(figure,width='stretch',theme='streamlit',
                        config={'displaylogo':False,'modeBarButtonsToRemove':['toImage']}, key=f'{spec.id}:plot')
    if spec.plot_caption:
        st.caption(spec.plot_caption)
    if st.button('准备报告图片', key=f'{spec.id}:prepare_plot'):
        if spec.plot_kind == 'matplotlib':
            report = spec.build_plot(session.normalized,session.result)
        else:
            from core.plots import report_from_plotly
            report = report_from_plotly(figure)
        try:
            for format in ('png','svg'):
                session.exports[f'plot:{format}'] = figure_bytes(report,format)
        finally:
            report.clear()
    with st.container(horizontal=True):
        for format,mime in [('png','image/png'),('svg','image/svg+xml')]:
            if f'plot:{format}' in session.exports:
                st.download_button(f'下载 {format.upper()}',session.exports[f'plot:{format}'],
                    file_name=f'{spec.id}.{format}',mime=mime,on_click='ignore',
                    key=f'{spec.id}:plot:{format}:{session.inputs.revision}')
    st.caption('报告图片统一白底，包含当前输入对应的曲线、单位和实验标注。')
    st.caption(fonts.caption)
