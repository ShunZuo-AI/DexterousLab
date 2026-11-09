"""The experiment must fail closed on lifted-but-dropped and passive rollouts."""

import importlib.util
from pathlib import Path

from dexterous_lab.config import PROJECT_ROOT, read_toml


def experiment():
    spec = importlib.util.spec_from_file_location('first_grasp', PROJECT_ROOT / 'scripts/first_grasp_experiment.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_trial_completion_and_transient_lift_do_not_imply_grasp_success():
    module = experiment()
    criteria = {'lift_height_m': 0.03, 'hold_steps': 20}
    assert module.outcome(0, 0, criteria) == (False, 'no_lift')
    assert module.outcome(0, 20, criteria) == (False, 'no_lift')
    assert module.outcome(0.10, 0, criteria) == (False, 'no_sustained_multifinger_hold')
    assert module.outcome(0.10, 19, criteria) == (False, 'no_sustained_multifinger_hold')
    assert module.outcome(0.10, 20, criteria) == (True, None)


def test_comparison_configuration_has_same_object_and_phases():
    values = read_toml(PROJECT_ROOT / 'configs/experiments/first_grasp.toml')
    assert sum(values[name] for name in ('settle_steps', 'approach_steps', 'descend_steps',
                                        'close_steps', 'lift_steps', 'hold_steps')) == 480
    assert values['robot_gravity_compensation'] is True
    assert values['criteria']['hold_steps'] <= values['hold_steps']
    assert not any(name.startswith('rh_') for name in values['allegro']['open_joints'])
    assert all(name.startswith('rh_') for name in values['shadow']['open_joints'])
