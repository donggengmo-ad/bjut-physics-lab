import os
import importlib
import re

_CN_ORDER = ['一','二','三','四','五','六','七','八','九','十']
_CN_INDEX = {ch:i for i,ch in enumerate(_CN_ORDER)}
def _get_cn_key(name):
    ch = re.search(r'实验([一二三四五六七八九十])：', name)
    if ch:
        return _CN_INDEX[ch.group(0)[2]]
    return 100

def get_experiments():
    experiments = {}
    # 遍历当前目录下的所有文件
    for name in os.listdir(os.path.dirname(__file__)):
        # 找以"exp"开头, ".py" 结尾的文件
        if name.startswith("exp") and name.endswith(".py"):
            # 导入模块
            module_name = f'experiments.{name.replace(".py", "")}'
            module = importlib.import_module(module_name)
            # 获取模块中的Experiment类
            exp = module.Experiment()
            experiments[exp.name] = exp
    # 排序并返回
    sorted_exps = dict(sorted(experiments.items(), key=lambda x:_get_cn_key(x[0])))
    return sorted_exps
