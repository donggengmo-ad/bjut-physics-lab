"""缺测友好的小型数值工具；不将缺测替换成零。"""

import math

import numpy as np


def finite_mean(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return float(finite.mean()) if len(finite) else math.nan


def sample_std(values):
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return float(finite.std(ddof=1)) if len(finite) > 1 else math.nan


def divide(numerator, denominator):
    return numerator / denominator if math.isfinite(denominator) and denominator != 0 else math.nan
