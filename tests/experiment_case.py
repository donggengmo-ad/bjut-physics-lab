"""旧数值场景的测试夹具：只适配断言名称，调用新的公开纯计算接口。"""
from experiments import get_spec
from core.validation import normalize


class ExperimentCase:
    def __init__(self, experiment_id):
        self.spec = get_spec(experiment_id)
        self.inputs = self.spec.initial_state()
        self.result = self.spec.compute(self.inputs)

    @property
    def initial_df(self):
        return self.inputs.tables

    @property
    def final_df(self):
        return self.result.tables

    def __getattr__(self, name):
        aliases = {'name':'title'}
        if name in ('name','volume','number','description'):
            return getattr(self.spec, aliases.get(name,name))
        if name in self.inputs.parameters:
            return self.inputs.parameters[name]
        if name == 'input_issues':
            return self.result.notes
        return self.result.values[name]

    def fill_data(self):
        normalized, issues = normalize(self.spec, self.inputs)
        if any(i.severity == 'error' for i in issues):
            raise ValueError('\n'.join(map(str, issues)))
        self.result = self.spec.compute(normalized)

    def set_initial_df(self, frame, key):
        candidate = self.inputs.copy()
        candidate.tables[key] = frame
        normalized, issues = normalize(self.spec, candidate)
        if any(i.severity == 'error' for i in issues):
            raise ValueError('\n'.join(map(str, issues)))
        self.inputs = normalized

    def build_plot(self):
        return self.spec.build_plot(self.inputs, self.result)


def open_app(experiment_id):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file('app.py', default_timeout=30).run()
    if experiment_id != 'upper_02_elasticity':
        app.switch_page(f'app_pages/{experiment_id}.py').run()
    return app


def select_view(app, experiment_id, name):
    app.session_state[f'{experiment_id}:view'] = name
    return app.run()
