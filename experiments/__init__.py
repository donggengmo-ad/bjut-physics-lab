"""轻量显式注册表，选中页面时才加载实验。"""
from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module

@dataclass(frozen=True)
class ExperimentEntry:
    id: str
    volume: str
    number: int
    title: str
    module: str
    icon: str

EXPERIMENTS = (
    ExperimentEntry('upper_02_elasticity', '上册', 2, '金属弹性模量', 'exp02_弹性模量', 'straighten'),
    ExperimentEntry('upper_03_torsion', '上册', 3, '扭摆与转动惯量', 'exp03_扭摆', 'rotate_right'),
    ExperimentEntry('upper_06_magnetic_field', '上册', 6, '非均匀磁场', 'exp06_非均匀磁场', 'explore'),
    ExperimentEntry('upper_07_spectrometer', '上册', 7, '分光计', 'exp07_分光仪', 'architecture'),
    ExperimentEntry('upper_08_newton_rings', '上册', 8, '牛顿环', 'exp08_牛顿环', 'blur_circular'),
    ExperimentEntry('upper_09_franck_hertz', '上册', 9, '弗兰克–赫兹', 'exp09_弗兰克赫兹', 'show_chart'),
    ExperimentEntry('lower_02_resonance', '下册', 2, '交流电路谐振', 'exp_lower_02_交流电路谐振', 'graphic_eq'),
    ExperimentEntry('lower_04_diffraction_grating', '下册', 4, '衍射光栅', 'exp_lower_04_衍射光栅', 'flare'),
    ExperimentEntry('lower_05_sound_speed', '下册', 5, '声速测量', 'exp_lower_05_声速测量', 'waves'),
    ExperimentEntry('lower_06_millikan_oil_drop', '下册', 6, '密立根油滴', 'exp_lower_06_密立根油滴', 'water_drop'),
)

@lru_cache(maxsize=10)
def get_spec(experiment_id):
    entry = next((e for e in EXPERIMENTS if e.id == experiment_id), None)
    if entry is None:
        raise KeyError(f'未知实验：{experiment_id}')
    return import_module(f'experiments.{entry.module}').get_spec()
