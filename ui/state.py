import streamlit as st
from core.session import ExperimentSession
from experiments import get_spec


def get_session(experiment_id):
    sessions = st.session_state.setdefault('lab_sessions', {})
    if experiment_id not in sessions:
        sessions[experiment_id] = ExperimentSession.create(get_spec(experiment_id))
    return sessions[experiment_id]


def editor_key(experiment_id, table_index, generation):
    return f'{experiment_id}:table:{table_index}:{generation}'


def parameter_key(experiment_id, parameter_id, generation):
    return f'{experiment_id}:parameter:{parameter_id}:{generation}'
