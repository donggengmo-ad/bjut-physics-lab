"""Plotly 测量折线的白底报告导出；重用图中数值、标线与刻度。"""
import re
import base64
import numpy as np
from contextlib import contextmanager


@contextmanager
def report_style():
    import matplotlib as mpl
    from matplotlib import font_manager
    available = {font.name for font in font_manager.fontManager.ttflist}
    font = next((name for name in ('Noto Sans CJK SC','Source Han Sans SC','SimHei',
                                   'Microsoft YaHei','PingFang SC','Heiti SC','Arial Unicode MS')
                 if name in available),'DejaVu Sans')
    with mpl.rc_context({'font.family':font,'font.size':11,'figure.facecolor':'white',
                         'axes.facecolor':'white','text.color':'#1F2328','axes.labelcolor':'#1F2328',
                         'xtick.color':'#1F2328','ytick.color':'#1F2328','axes.unicode_minus':False,
                         'svg.fonttype':'none','pdf.fonttype':42}):
        yield


def plain(text):
    return re.sub('<[^>]+>', '', re.sub(r'<br\s*/?>', '\n', text or ''))


def numeric_values(values):
    # Plotly 6 的 JSON 使用二进制数值数组；不能把 dtype/bdata 键当测量点。
    if isinstance(values, dict) and 'bdata' in values and 'dtype' in values:
        return np.frombuffer(base64.b64decode(values['bdata']), dtype=values['dtype']).tolist()
    return list(values)


def report_from_plotly(plot):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    with report_style():
        figure=Figure(figsize=(9,6),layout='constrained')
        FigureCanvasAgg(figure)
        ax=figure.subplots()
        colors=['#0969DA','#D55E00','#009E73']
        for index,trace in enumerate(plot.data):
            color=trace.line.color or colors[index%len(colors)]
            dash='--' if trace.line.dash in ('dash','dot','dashdot') else '-'
            marker={'diamond':'D','square':'s'}.get(trace.marker.symbol,'o')
            ax.plot(numeric_values(trace.x),numeric_values(trace.y),label=trace.name,color=color,
                    linestyle=dash if 'lines' in (trace.mode or 'lines') else 'None',
                    marker=marker if 'markers' in (trace.mode or '') else None,markersize=4)
        for shape in plot.layout.shapes:
            color=shape.line.color or '#666666'
            if shape.xref and 'domain' in shape.xref:
                ax.axhline(shape.y0,color=color,linestyle='--',linewidth=1)
            else:
                ax.plot([shape.x0,shape.x1],[shape.y0,shape.y1],color=color,linestyle='--',linewidth=1)
        for annotation in plot.layout.annotations:
            if annotation.xref and ('domain' in annotation.xref or annotation.xref=='paper'):
                transform=ax.transAxes if annotation.yref=='paper' else ax.get_yaxis_transform()
                ax.text(annotation.x,annotation.y,plain(annotation.text),transform=transform,
                        ha='right' if annotation.x>=.9 else 'center',fontsize=9)
            elif annotation.xref == 'x' and annotation.yref == 'y':
                # Plotly 的像素偏移向下为正，Matplotlib 的点偏移向上为正。
                color = annotation.font.color or '#1F2328'
                ax.annotate(plain(annotation.text), xy=(annotation.x, annotation.y),
                            xytext=((annotation.ax or 0) * .75, -(annotation.ay or 0) * .75),
                            textcoords='offset points',
                            ha={'left':'left','right':'right'}.get(annotation.xanchor,'center'),
                            va='center', fontsize=9, color=color,
                            arrowprops={'arrowstyle':'->','color':color,'linewidth':1}
                            if annotation.showarrow else None)
        ax.set_title(plain(plot.layout.title.text),pad=18)
        ax.set_xlabel(plain(plot.layout.xaxis.title.text));ax.set_ylabel(plain(plot.layout.yaxis.title.text))
        if plot.layout.xaxis.tickvals:
            ax.set_xticks(list(plot.layout.xaxis.tickvals),[plain(t) for t in plot.layout.xaxis.ticktext],rotation=45,ha='right')
        if plot.layout.yaxis.range:
            ax.set_ylim(*plot.layout.yaxis.range)
        ax.grid(alpha=.2);ax.legend();ax.spines[['top','right']].set_visible(False)
    return figure
