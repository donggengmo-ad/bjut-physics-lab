"""度.分记录与十进制度互转；原始文本不覆盖。"""

import math
import re

import pandas as pd


def parse_angle(value):
    if pd.isna(value) or str(value).strip() == '':
        return math.nan
    text = str(value).strip()
    # pandas/CSV 可能读成 30.1；约定与原实验一致，代表 30°10′。
    match = re.fullmatch(r'(\d{1,3})(?:\.(\d{1,2})|[:°度](\d{1,2})[′\'分]?)?', text)
    if not match:
        raise ValueError('角度请用度.分、度:分或度°分′，例如 30.15。')
    degrees = int(match[1])
    minutes = int(match[2].ljust(2, '0')) if match[2] is not None else int(match[3] or 0)
    if minutes >= 60 or degrees > 360 or (degrees == 360 and minutes != 0):
        raise ValueError('角度应在 0°–360°，分数应小于 60。')
    return (degrees + minutes / 60) % 360


def angle_text(value, *, latex=True):
    if value is None or not math.isfinite(value):
        return '—'
    sign = '-' if value < 0 else ''
    seconds = round(abs(value) * 3600)
    degrees, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if latex:
        text = rf'{sign}{degrees}^{{\circ}}{minutes:02d}^{{\prime}}'
        return text + (rf'{seconds:02d}^{{\prime\prime}}' if seconds else '')
    return f'{sign}{degrees}°{minutes:02d}′' + (f'{seconds:02d}″' if seconds else '')
