"""太阳能电池：记录点计算，不用插值制造测量值。"""
import numpy as np
import pandas as pd
from core.models import ColumnSpec, TableSpec, ParameterSpec, ExperimentSpec, ResultBundle, Explanation, DisplayTable
from core.fonts import report_style

KINDS = ('单晶硅', '多晶硅', '非晶硅')
DARK, LIGHT, OUTPUT = '表9-1 暗伏安特性', '表9-2 光强关系', '表9-3 输出特性'
U, E, L = '电压 / V', '照度 / lx', '距离 / cm'
def voltage(k): return f'{k}实际电压 / V'
def current(k): return f'{k}电流 / mA'
def voc(k): return f'{k}开路电压 / V'
def isc(k): return f'{k}短路电流 / mA'

def table(name, fixed, values, columns):
    frame = pd.DataFrame({fixed: values})
    for c in columns: frame[c] = np.nan
    return TableSpec(name, name, frame, tuple(ColumnSpec(c) for c in frame), fixed_columns=(fixed,))

def compute(inputs):
    light = inputs.tables[LIGHT].copy()
    light['光强 / (W/m²)'] = light[E] / 25.8
    out = inputs.tables[OUTPUT].copy()
    rows = []
    intensity = inputs.parameters.get('intensity')
    area = inputs.parameters.get('area')
    for k in KINDS:
        p = out[voltage(k)] * out[current(k)]
        out[f'{k}功率 / mW'] = p
        valid = p.notna() & (out[current(k)] >= 0)
        maximum = float(p[valid].max()) if valid.any() else np.nan
        peaks = out.loc[valid & np.isclose(p, maximum, rtol=1e-12, atol=0), voltage(k)].tolist()
        oc, sc = inputs.parameters.get(f'voc_{k}'), inputs.parameters.get(f'isc_{k}')
        ff = maximum / (oc * sc) if oc and sc and oc > 0 and sc > 0 else np.nan
        pin = intensity * area / 1000 if intensity and area and intensity > 0 and area > 0 else np.nan
        efficiency = maximum / pin * 100 if pin > 0 else np.nan
        rows.append([k, maximum, '、'.join(f'{x:g}' for x in peaks), oc, sc, ff, pin, efficiency])
    summary = pd.DataFrame(rows, columns=['电池', '采样最大功率 / mW', '最大功率点电压 / V', '开路电压 / V', '短路电流 / mA', '填充因子', '入射功率 / mW', '转换效率 / %'])
    return ResultBundle(tables={DARK: inputs.tables[DARK].copy(), LIGHT: light, OUTPUT: out, '特性参数': summary}, revision=inputs.revision,
        notes=['最大功率取已测点中的最大值；并列最大值全部保留。填充因子使用与输出测量相同光照条件下的开路电压和短路电流。'])

def explain(inputs, result):
    d = Explanation()
    d.image(principle_diagram())
    d.markdown('### 1. 暗伏安特性\n比较三种电池正向电流增长与反向电流大小。测量数据不足时不判定性能优劣。')
    d.markdown('### 2. 光强换算')
    d.latex(r'G=E/25.8\quad [G]=\mathrm{W/m^2}')
    for _, row in result.tables[LIGHT].iterrows():
        if pd.notna(row[E]): d.latex(fr'G_{{{row[L]:g}\mathrm{{cm}}}}={row[E]:g}/25.8\approx {row["光强 / (W/m²)"]:.0f}\ \mathrm{{W/m^2}}')
    d.markdown('开路电压通常随光强增加而缓慢增大，短路电流通常近似随光强线性增加；以实测曲线判断各电池的差异。')
    d.markdown('### 3. 输出功率、填充因子和转换效率')
    d.latex(r'P(\mathrm{mW})=U(\mathrm V)I(\mathrm{mA}),\quad FF=\frac{P_{max}}{V_{oc}I_{sc}},\quad P_{in}(\mathrm{mW})=G S(\mathrm{mm^2})/1000,\quad \eta=\frac{P_{max}}{P_{in}}\times100\%')
    for _, row in result.tables[OUTPUT].iterrows():
        for k in KINDS:
            if pd.notna(row[current(k)]) and pd.notna(row[voltage(k)]):
                d.markdown(f'{k}：{row[voltage(k)]:g} V × {row[current(k)]:g} mA ≈ {row[f"{k}功率 / mW"]:.1f} mW。')
    for _, r in result.tables['特性参数'].iterrows():
        d.markdown(f'**{r["电池"]}**')
        maximum = r['采样最大功率 / mW']
        if pd.isna(maximum):
            d.caption('没有完整的输出电压、电流测量对，暂不能确定最大功率点。')
            continue
        d.markdown('① 比较各有效测量点的输出功率，选取最大值（并列点全部列出）。')
        d.latex(r'P_{max}=\max_i(U_i I_i)')
        k = r['电池']
        output = result.tables[OUTPUT]
        peak_rows = output[np.isclose(output[f'{k}功率 / mW'], maximum, rtol=1e-12, atol=0)]
        for _, point in peak_rows.iterrows():
            d.markdown(f'最大功率点：实际电压 **{point[voltage(k)]:g} V**，电流 **{point[current(k)]:g} mA**。')
            d.latex(fr'P_{{max}}={point[voltage(k)]:g}\times {point[current(k)]:g}\approx {maximum:.1f}\ \mathrm{{mW}}')
        d.markdown('② 计算填充因子。')
        if pd.isna(r['填充因子']):
            oc, sc = r['开路电压 / V'], r['短路电流 / mA']
            oc_text = f'{oc:g}' if pd.notna(oc) and oc > 0 else 'V_{oc}'
            sc_text = f'{sc:g}' if pd.notna(sc) and sc > 0 else 'I_{sc}'
            d.latex(fr'FF=\frac{{P_{{max}}}}{{V_{{oc}}I_{{sc}}}}=\frac{{{maximum:.6g}}}{{{oc_text}\times {sc_text}}}')
            missing = []
            if pd.isna(oc) or oc <= 0: missing.append('同光照开路电压')
            if pd.isna(sc) or sc <= 0: missing.append('同光照短路电流')
            d.info('待录入' + '、'.join(missing) + '后计算填充因子。')
        if pd.notna(r['填充因子']): d.latex(fr'FF=\frac{{{r["采样最大功率 / mW"]:.6g}}}{{{r["开路电压 / V"]:g}\times {r["短路电流 / mA"]:g}}}={r["填充因子"]:.6g}')
        d.markdown('③ 计算能量转换效率。')
        d.latex(r'P_{in}=GS,\qquad S(\mathrm{m^2})=S(\mathrm{mm^2})\times10^{-6},\qquad \eta=\frac{P_{max}}{P_{in}}\times100\%')
        intensity, area = inputs.parameters.get('intensity'), inputs.parameters.get('area')
        g_text = f'{intensity:.6g}' if pd.notna(intensity) and intensity > 0 else 'G'
        area_text = f'{area:g}' if pd.notna(area) and area > 0 else 'S'
        d.latex(fr'P_{{in}}={g_text}\times {area_text}\times10^{{-6}}\ \mathrm{{W}}={g_text}\times {area_text}/1000\ \mathrm{{mW}}')
        if pd.isna(r['转换效率 / %']):
            d.latex(fr'\eta=\frac{{{maximum:.6g}}}{{{g_text}\times {area_text}/1000}}\times100\%')
            missing = []
            if pd.isna(intensity) or intensity <= 0: missing.append('输出测量光强')
            if pd.isna(area) or area <= 0: missing.append('电池受光面积')
            d.info('待录入' + '、'.join(missing) + '后计算转换效率。')
        if pd.notna(r['转换效率 / %']): d.latex(fr'\eta=\frac{{{r["采样最大功率 / mW"]:.6g}}}{{{r["入射功率 / mW"]:.6g}}}\times100\%={r["转换效率 / %"]:.6g}\%')
    d.caption('输出功率保留一位小数，光强保留整数；中间代入保留保护位，计算及 CSV 导出使用未舍入值。')
    return d

def format_tables(inputs, result):
    tables = []
    for name, source in result.tables.items():
        frame = source.copy(deep=True)
        for column in frame.columns:
            if column == '光强 / (W/m²)':
                frame[column] = frame[column].map(lambda v: '—' if pd.isna(v) else f'{v:.0f}')
            elif column.endswith('功率 / mW') and column != '入射功率 / mW':
                frame[column] = frame[column].map(lambda v: '—' if pd.isna(v) else f'{v:.1f}')
        tables.append(DisplayTable(name, frame))
    return tables


def build_plot(inputs, result):
    from matplotlib import pyplot as plt
    with report_style():
        fig, axes = plt.subplots(3, 2, figsize=(11, 13), layout='constrained')
        panels = [(DARK,U,current,'暗伏安特性','电流 / mA'),(LIGHT,'光强 / (W/m²)',voc,'开路电压与光强','开路电压 / V'),(LIGHT,'光强 / (W/m²)',isc,'短路电流与光强','短路电流 / mA'),(OUTPUT,U,current,'输出伏安特性','电流 / mA'),(OUTPUT,U,lambda k:f'{k}功率 / mW','输出功率','功率 / mW')]
        for ax,(name,x,col,title,y) in zip(axes.flat,panels):
            frame=result.tables[name]
            for k,color,mark,line in zip(KINDS,('#0072B2','#D55E00','#009E73'),('o','s','^'),('-','--',':')):
                xcol = voltage(k) if name == OUTPUT else x
                if not (frame[xcol].notna() & frame[col(k)].notna()).any():
                    continue
                ax.plot(frame[xcol],frame[col(k)],color=color,marker=mark,linestyle=line,label=k)
            ax.set(title=title,xlabel=x,ylabel=y); ax.grid(alpha=.2)
            if ax.lines: ax.legend()
            else: ax.text(.5,.5,'暂无有效测量点',ha='center',transform=ax.transAxes)
        axes.flat[-1].axis('off')
        return fig

DESCRIPTION = '''### 实验目的与仪器
学习光生伏特效应，测量单晶硅、多晶硅、非晶硅电池的暗伏安特性、开路电压、短路电流和输出特性。使用太阳能电池实验装置、电池组、电阻、光源及导线。
### 实验原理
P 型与 N 型半导体接触后，多数载流子扩散形成空间电荷区和由 N 区指向 P 区的内建电场。光照产生电子—空穴对，内建电场分离载流子，接入负载后输出电能。
开路电压为输出电流为零时的端电压；短路电流为端电压为零时的电流。输出功率为电压与电流的乘积，填充因子为最大功率与开路电压、短路电流乘积的比值。
### 实验内容与步骤
1. 遮光测暗伏安特性：电源经限流电阻和电流表接电池，电压表并联电池。从零电压开始测正向与反向电流，依表 9-1 记录三种电池。
2. 光源稳定后调整距离，测照度；用电压表测开路电压，用电流表测短路电流，填写表 9-2。
3. 固定距离和光强，电阻箱作为负载，电流表串联、电压表并联电池；改变负载记录表 9-3，计算功率。
4. 同一光照条件测开路电压、短路电流，计算填充因子；以电池受光面积和光强计算入射功率及转换效率。
### 注意事项
暗特性测量须遮光；改变接线前将电源调零并断电。光源工作时避免触碰发热部件，保持光照、位置及接触状态稳定，按装置规定接地。
'''


DISCUSSION = """**（1）讨论太阳能电池的暗伏安特性与一般二极管的伏安特性有何异同。**

相同点：两者均具有整流特性，正向电流随电压迅速增大，反向未击穿时电流较小。

不同点：太阳能电池通常结面积较大，且可能由多个单元串联组成，因此暗电流大小和端电压与普通单个二极管有所不同。
"""

def get_spec():
    tables=(table(DARK,U,list(range(-7,1))+[round(.3*i,1) for i in range(1,14)],[current(k) for k in KINDS]),
            table(LIGHT,L,list(range(15,51,5)),[E]+[c for k in KINDS for c in (voc(k),isc(k))]),
            table(OUTPUT,U,[round(.2*i,1) for i in range(19)],[c for k in KINDS for c in (voltage(k),current(k))]))
    # 照片原始记录：未测项目保持空值。
    dark, light, output = [t.defaults for t in tables]
    dark[current('单晶硅')] = [-.1,-.079,-.062,-.047,-.030,-.014,-.000,.010,.014,.023,.038,.065,.1,.2,.4,.8,1.6,3.1,5.9,10.,15.2]
    dark[current('多晶硅')] = [-.2,-.1,-.068,-.049,-.030,-.015,-.001,.010,.015,.023,.039,.063,.1,.2,.4,.8,1.7,3.8,7.2,12.1,18.1]
    light[E] = [16128,10644,7603,6036,4907,3962,3179,2638]
    light[voc('单晶硅')] = [3.693,3.573,3.489,3.420,3.355,3.302,3.252,3.205]
    light[isc('单晶硅')] = [91.3,53.7,36.6,26.7,20.4,16.2,13.1,10.8]
    light[voc('多晶硅')] = [3.630,3.501,3.417,3.347,3.284,3.237,3.190,3.152]
    light[isc('多晶硅')] = [86.6,50.2,34.1,25.,19.,15.,12.,9.9]
    output.loc[:9,voltage('单晶硅')] = [.041,.209,.397,.607,.793,1.004,1.210,1.400,1.604,1.806]
    output.loc[:9,voltage('多晶硅')] = [.035,.197,.400,.608,.797,.995,1.200,1.403,1.600,1.806]
    output.loc[:9,current('单晶硅')] = [26.3,26.4,26.3,26.3,26.3,26.3,26.3,26.2,26.2,26.1]
    output.loc[:9,current('多晶硅')] = [21.8,21.8,21.7,21.7,21.7,21.8,21.8,21.8,21.8,21.8]
    output.loc[10:17,voltage('单晶硅')] = [2.004,2.209,2.395,2.607,2.803,3.033,3.208,3.375]
    output.loc[10:16,voltage('多晶硅')] = [2.007,2.204,2.402,2.597,2.805,3.006,3.198]
    output.loc[10:17,current('单晶硅')] = [26.0,25.5,25.1,24.4,22.8,18.9,12.5,.4]
    output.loc[10:16,current('多晶硅')] = [21.7,21.4,21.0,20.3,18.4,14.4,5.0]
    params=[ParameterSpec('distance','输出测量距离 / cm',30.,optional=True,positive=True),ParameterSpec('intensity','输出测量光强 / (W/m²)',234.,optional=True,positive=True),ParameterSpec('area','电池受光面积 / mm²',3600.,positive=True,help='报告给定约 60 mm × 60 mm。')]
    for k in KINDS:
        params += [ParameterSpec(f'voc_{k}',f'{k}同光照开路电压 / V',{'单晶硅': 3.381, '多晶硅': 3.300}.get(k),optional=True,positive=True),ParameterSpec(f'isc_{k}',f'{k}同光照短路电流 / mA',{'单晶硅': 26.7, '多晶硅': 25.0}.get(k),optional=True,positive=True)]
    return ExperimentSpec('lower_09_solar_cell','太阳能电池特性的测量','下册',9,'比较三种硅太阳能电池的电学与光电转换特性。',DESCRIPTION,tables,tuple(params),compute,explain,format_tables=format_tables,build_plot=build_plot,plot_kind='matplotlib',discussion=DISCUSSION,plot_caption='仅绘制有实测记录的电池；输出曲线使用各自的实际电压，空白测量保持断线。')


def principle_diagram():
    """定性原理图，不作为测量数据。"""
    from io import StringIO
    from matplotlib import pyplot as plt
    from matplotlib.patches import Rectangle
    with report_style():
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), layout='constrained')
        ax = axes[0]
        for x, label, color in [(0,'P 区','#F6DDCC'),(1,'空间电荷区','#EEEEEE'),(2,'N 区','#D6EAF8')]:
            ax.add_patch(Rectangle((x,0),1,1,facecolor=color,edgecolor='black'))
            ax.text(x+.5,.5,label,ha='center')
        ax.annotate('内建电场',xy=(.8,1.2),xytext=(2.1,1.2),arrowprops={'arrowstyle':'->'})
        ax.text(.5,-.3,'空穴向 P 区',ha='center'); ax.text(2.5,-.3,'电子向 N 区',ha='center')
        ax.set(xlim=(-.2,3.2),ylim=(-.6,1.6),title='PN 结与光生载流子分离');ax.axis('off')
        ax=axes[1]; u=np.linspace(0,1,100); current=1-u**6
        ax.plot(u,current,label='电流（归一化）')
        ax.plot(u,u*current,'--',label='功率（归一化）')
        peak=np.argmax(u*current)
        ax.plot(u[peak],(u*current)[peak],'o');ax.annotate('最大功率点',(u[peak],(u*current)[peak]),xytext=(.2,.3),arrowprops={'arrowstyle':'->'})
        ax.set(xlabel='电压（归一化）',ylabel='归一化量',title='输出特性示意（非实测）');ax.legend(fontsize=8)
        buf=StringIO();fig.savefig(buf,format='svg');plt.close(fig)
        return buf.getvalue()
