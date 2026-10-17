"""字体验收检查实际字形和导出，不只检查 rcParams 中的名称。"""
import hashlib
import json
from pathlib import Path
import unittest
import warnings
from unittest.mock import patch

import matplotlib as mpl
from matplotlib import font_manager as fm
from matplotlib.font_manager import FontProperties

from core.fonts import FONT_DIR, apply_report_fonts, choose_fonts, report_fonts, report_style
from core.plots import report_from_plotly
from experiments import EXPERIMENTS, get_spec
from ui.charts import figure_bytes


class ReportFontTests(unittest.TestCase):
    def test_requested_families_take_precedence_and_fallback_is_explicit(self):
        fonts = choose_fonts({'SimSun', 'Songti SC', 'Times New Roman', 'Source Han Serif SC', 'Liberation Serif'})
        self.assertEqual(fonts.families, ['Times New Roman', 'SimSun', 'DejaVu Serif'])
        fallback = choose_fonts({'Source Han Serif SC', 'Liberation Serif'})
        self.assertEqual(fallback.families, ['Liberation Serif', 'Source Han Serif SC', 'DejaVu Serif'])
        self.assertIn('替代', fallback.caption)
        with self.assertRaises(RuntimeError):
            choose_fonts({'DejaVu Sans'})

    def test_bundled_font_files_match_recorded_hashes(self):
        records = json.loads((FONT_DIR / 'sources.json').read_text())
        self.assertEqual({r['file'] for r in records}, {p.name for p in FONT_DIR.iterdir() if p.suffix in ('.ttf', '.otf', '.txt')})
        for record in records:
            self.assertEqual(hashlib.sha256((FONT_DIR / record['file']).read_bytes()).hexdigest(), record['sha256'])

    def assert_actual_glyphs(self):
        fonts = report_fonts()
        prop = FontProperties(family=fonts.families)
        paths = fm.fontManager._find_fonts_by_props(prop)
        font = fm.get_font(paths)
        mapping = font._get_fontmap('中文宋体谐振衍射频率电流0123HzΩλφΔ√−×₁₂°')
        for char, face in mapping.items():
            self.assertNotEqual(face.get_char_index(ord(char)), 0, char)
            if char in '中文宋体谐振衍射频率电流':
                self.assertEqual(face.family_name, fonts.chinese)
            elif char in '0123Hz':
                self.assertEqual(face.family_name, fonts.latin)

    def test_actual_mixed_glyphs_and_rc_context_restoration(self):
        old_family = list(mpl.rcParams['font.family'])
        with report_style():
            self.assert_actual_glyphs()
            self.assertEqual(mpl.rcParams['mathtext.rm'], report_fonts().latin)
        self.assertEqual(mpl.rcParams['font.family'], old_family)

    def test_all_plots_render_with_only_bundled_and_matplotlib_fonts(self):
        # 保留 Matplotlib 自带符号字体，剔除所有操作系统字体，模拟无中文字体的 Linux。
        report_fonts()
        manager = fm.fontManager
        before = list(manager.ttflist)
        mpl_fonts = (Path(mpl.get_data_path()) / 'fonts').resolve()
        try:
            manager.ttflist = [font for font in before if Path(font.fname).resolve().is_relative_to(FONT_DIR)
                              or Path(font.fname).resolve().is_relative_to(mpl_fonts)]
            manager._findfont_cached.cache_clear()
            report_fonts.cache_clear()
            self.assertEqual(report_fonts().families, ['Liberation Serif', 'Source Han Serif SC', 'DejaVu Serif'])
            self.assert_actual_glyphs()
            for entry in EXPERIMENTS:
                spec = get_spec(entry.id)
                if spec.build_plot is None:
                    continue
                with self.subTest(experiment=entry.id), warnings.catch_warnings(record=True) as caught, self.assertNoLogs('matplotlib', level='WARNING'):
                    warnings.simplefilter('always')
                    state = spec.initial_state()
                    plot = spec.build_plot(state, spec.compute(state))
                    figure = plot if spec.plot_kind == 'matplotlib' else report_from_plotly(plot)
                    try:
                        apply_report_fonts(figure)
                        png = figure_bytes(figure, 'png')
                        svg = figure_bytes(figure, 'svg')
                        self.assertTrue(png.startswith(b'\x89PNG'))
                        self.assertIn(b'<path', svg)
                        self.assertNotIn(b'<text', svg)
                        pdf = figure_bytes(figure, 'pdf')
                        self.assertIn(b'%PDF', pdf)
                        self.assertIn(b'/FontFile', pdf)
                    finally:
                        figure.clear()
                    self.assertFalse([str(w.message) for w in caught if 'Glyph' in str(w.message)], entry.id)
        finally:
            manager.ttflist = before
            manager._findfont_cached.cache_clear()
            report_fonts.cache_clear()

    def test_font_policy_change_discards_only_old_chart_exports(self):
        from core.session import ExperimentSession
        from ui.charts import render_chart
        spec = get_spec('lower_04_diffraction_grating')
        session = ExperimentSession.create(spec)
        session.evaluate(spec)
        session.exports.update({'plot:preview': b'old-font-image', 'plot:png': b'old-font-export',
                                'csv:measurements': b'keep'})
        with patch('ui.charts.st') as streamlit:
            streamlit.button.return_value = False
            render_chart(spec, session)
        self.assertTrue(session.exports['plot:preview'].startswith(b'\x89PNG'))
        self.assertNotIn('plot:png', session.exports)
        self.assertEqual(session.exports['csv:measurements'], b'keep')


if __name__ == '__main__':
    unittest.main()
