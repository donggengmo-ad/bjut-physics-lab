"""报告字体：宋体与 Times New Roman 优先，随项目提供明确标识的开源兜底。"""
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parents[1] / 'assets' / 'fonts'


@dataclass(frozen=True)
class ReportFonts:
    chinese: str
    latin: str

    @property
    def families(self):
        # 拉丁字体放在前面，中文逐字回退到宋体，不能反过来让中文字体接管数字。
        return [self.latin, self.chinese, 'DejaVu Serif']

    @property
    def caption(self):
        fallback = self.chinese == 'Source Han Serif SC' or self.latin == 'Liberation Serif'
        return (f'报告字体：中文 {self.chinese}；英文与数字 {self.latin}。'
                + ('当前环境缺少部分指定字体，已使用随项目提供的开源替代字体。' if fallback else ''))


def choose_fonts(available):
    chinese = next((name for name in ('SimSun', 'NSimSun', 'Songti SC', 'Source Han Serif SC')
                    if name in available), None)
    latin = next((name for name in ('Times New Roman', 'Liberation Serif') if name in available), None)
    if not chinese or not latin:
        raise RuntimeError('报告字体不完整：请恢复 assets/fonts 中的思源宋体和 Liberation Serif 字体文件。')
    return ReportFonts(chinese, latin)


@lru_cache(maxsize=1)
def report_fonts():
    from matplotlib import font_manager
    paths = sorted([*FONT_DIR.glob('*.otf'), *FONT_DIR.glob('*.ttf')])
    if not paths:
        raise RuntimeError('缺少 assets/fonts 字体资源，无法保证报告字体。')
    # addfont 每个进程注册一次；不要求操作系统安装，也不依赖网络或可写字体缓存。
    for path in paths:
        font_manager.fontManager.addfont(str(path))
    return choose_fonts({entry.name for entry in font_manager.fontManager.ttflist})


@contextmanager
def report_style():
    import matplotlib as mpl
    fonts = report_fonts()
    with mpl.rc_context({
        'font.family': fonts.families, 'font.size': 11,
        'mathtext.fontset': 'custom', 'mathtext.rm': fonts.latin,
        'mathtext.it': f'{fonts.latin}:italic', 'mathtext.bf': f'{fonts.latin}:bold',
        'mathtext.bfit': f'{fonts.latin}:italic:bold', 'mathtext.cal': 'STIXGeneral:italic',
        'mathtext.sf': fonts.latin, 'mathtext.tt': fonts.latin, 'mathtext.fallback': 'stix',
        'figure.facecolor': 'white', 'axes.facecolor': 'white', 'text.color': '#1F2328',
        'axes.labelcolor': '#1F2328', 'xtick.color': '#1F2328', 'ytick.color': '#1F2328',
        'axes.unicode_minus': False, 'svg.fonttype': 'path', 'pdf.fonttype': 42,
        'ps.fonttype': 42, 'text.usetex': False,
    }):
        yield


def apply_report_fonts(figure):
    """保存前再次统一已有文字，避免局部字体覆盖或样式上下文退出导致导出回退。"""
    from matplotlib.text import Text
    for text in figure.findobj(match=Text):
        text.set_fontfamily(report_fonts().families)
