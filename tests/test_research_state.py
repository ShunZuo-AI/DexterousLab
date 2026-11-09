import json
from types import SimpleNamespace

import pytest
import torch

from dexterous_lab.integrations.isaaclab.state import ResearchState


@pytest.fixture
def state():
    pose = torch.tensor([[0.0, 0.0, 0.3, 0.0, 0.0, 0.0, 1.0]])
    forces = torch.tensor([[[[0.0, 0.0, 2.0], [0.0, 0.0, 0.0]]]])
    points = torch.tensor([[[[0.0, 0.0, 0.31], [float("nan"), float("nan"), float("nan")]]]])
    robot = SimpleNamespace(
        joint_names=["joint"], body_names=["configured_palm"],
        data=SimpleNamespace(joint_pos=torch.zeros(1, 1), joint_vel=torch.zeros(1, 1),
                             body_pose_w=pose[:, None, :], root_pose_w=pose),
    )
    scene = dict(robot=robot, object=SimpleNamespace(data=SimpleNamespace(root_pose_w=pose)))

    class Scene(dict):
        pass

    scene = Scene(scene)
    scene.sensors = {"dexlab_object_contact": SimpleNamespace(
        data=SimpleNamespace(normal_force_matrix_w=forces, contact_pos_w=points))}
    env = SimpleNamespace(scene=scene, num_envs=1)
    env.unwrapped = env
    return ResearchState(env, {"palm_frame": "configured_palm", "fingertip_names": ["tip1", "tip2"]})


def test_contact_nan_sentinels_are_not_serialized(state):
    snapshot = state.snapshot(1)
    json.dumps(snapshot, allow_nan=False)
    assert len(snapshot["contact_points"][0]) == 1
    assert snapshot["hand_root_frame"] == "configured_palm"
    assert snapshot["success"] is None
    assert snapshot["joint_velocities"] == [[0.0]]


def test_empty_contacts_are_measured_empty_not_unknown(state):
    state.env.scene.sensors["dexlab_object_contact"].data.normal_force_matrix_w.zero_()
    assert state.snapshot(1)["contact_points"] == [[]]


def test_contact_invalid_force_is_failure(state):
    state.env.scene.sensors["dexlab_object_contact"].data.normal_force_matrix_w.fill_(float("nan"))
    with pytest.raises(RuntimeError, match="non-finite"):
        state.contacts()


def test_active_contact_missing_position_is_failure(state):
    state.env.scene.sensors["dexlab_object_contact"].data.contact_pos_w.fill_(float("nan"))
    with pytest.raises(RuntimeError, match="Active contact"):
        state.contacts()


def test_missing_palm_never_falls_back(state):
    state.configuration["palm_frame"] = "missing"
    with pytest.raises(ValueError, match="not loaded"):
        state.palm_pose()
