from dataclasses import replace
import json

import pytest

from dexterous_lab.cli import main
from dexterous_lab.config import ObjectConfig, RobotConfig, checked_dataclass, load_scene, named_config
from dexterous_lab.objects.geometry import scaled_size


def test_default_scene():
    specification = load_scene()
    assert specification["hand_id"] == "allegro"
    assert specification["robot"]["requires_arm"] is True
    assert specification["robot"]["action_dim"] == 23


def test_shadow_has_independent_coordinates():
    configuration = load_scene(hand="shadow")["robot"]
    assert configuration["requires_arm"] is False
    assert len(configuration["joint_names"]) == 16
    assert len(configuration["tendon_names"]) == 4
    assert len(configuration["fingertip_names"]) == 5
    assert configuration["action_dim"] == 20


@pytest.mark.parametrize("object_id", ["cube", "sphere", "cylinder"])
def test_procedural_objects(object_id):
    assert load_scene(object_id=object_id)["object"]["kind"] == object_id


@pytest.mark.parametrize("kwargs", [{"hand": "missing"}, {"object_id": "cup"}, {"backend": "newton"}, {"scene": "../tabletop"}])
def test_unsupported_selections_fail(kwargs):
    with pytest.raises(ValueError):
        load_scene(**kwargs)


@pytest.mark.parametrize("kwargs", [{"scale": (0, 1, 1)}, {"rotation_xyzw": (1, 1, 1, 1)}, {"mass": -1},
                                    {"position_xyz": (float("nan"), 0, 0)}, {"kind": "mesh"},
                                    {"kind": "usd", "usd_path": "/nonexistent.usd"}])
def test_invalid_objects(kwargs):
    with pytest.raises(ValueError):
        ObjectConfig(**kwargs)


def test_unknown_fields_fail():
    with pytest.raises(ValueError, match="Unsupported"):
        checked_dataclass(ObjectConfig, {"scalle": [2, 2, 2]})


def test_physical_dimensions():
    assert scaled_size(ObjectConfig(scale=(2, 3, 4))) == pytest.approx((0.1, 0.15, 0.2))


def test_robot_dimensions_checked():
    configuration = checked_dataclass(RobotConfig, named_config("robots", "allegro"))
    with pytest.raises(ValueError, match="action_dim"):
        replace(configuration, action_dim=16)


def test_cli_dry_run_and_inventory(capsys):
    assert main(["scene", "run", "--hand", "shadow", "--object", "cube", "--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["config"]["hand_id"] == "shadow"
    assert main(["scene", "list"]) == 0
    assert "tabletop" in json.loads(capsys.readouterr().out)["scenes"]


@pytest.mark.parametrize("args", [["scene", "run", "--hand", "unknown"], ["scene", "run", "--steps", "0"],
                                 ["scene", "run", "--num-envs", "5"], ["scene", "run", "--policy", "fake"]])
def test_cli_rejects_unimplemented_or_large_requests(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
