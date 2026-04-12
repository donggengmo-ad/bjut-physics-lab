import os
import importlib

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
    sorted_exps = dict(sorted(experiments.items()))
    return sorted_exps
