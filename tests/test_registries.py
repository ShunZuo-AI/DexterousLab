from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from dexterous_lab.cli import build_parser, main
from dexterous_lab.config import CONFIG_ROOT, RobotConfig
from dexterous_lab.objects.registry import ObjectRegistry
from dexterous_lab.registry import import_factory
from dexterous_lab.robots.registry import HandRegistry


def test_hand_and_object_discovery():
    assert HandRegistry().names() == ["allegro", "shadow"]
    assert {"cube", "cylinder", "sphere"}.issubset(ObjectRegistry().names())
    assert HandRegistry().get("shadow").palm_frame == "rh_palm"
    assert ObjectRegistry().get("cylinder").registry_name == "dexlab_cylinder"


def test_new_hand_can_be_added_without_changing_python(tmp_path):
    directory = tmp_path / "robots"
    directory.mkdir()
    original = (CONFIG_ROOT / "robots/allegro.toml").read_text()
    (directory / "research_hand.toml").write_text(original.replace('hand_id = "allegro"', 'hand_id = "research_hand"'))
    configuration = HandRegistry(tmp_path).get("research_hand")
    assert configuration.hand_id == "research_hand"
    assert configuration.action_dim == 23


def test_configured_factory_is_used(monkeypatch):
    import sys

    received = []
    factory = lambda configuration, arena: received.append((configuration, arena)) or "created"
    monkeypatch.setitem(sys.modules, "test_hand_plugin", SimpleNamespace(create=factory))
    configuration = HandRegistry().get("allegro", {"factory": "test_hand_plugin:create"})
    assert HandRegistry().create(configuration, "arena-registry") == "created"
    assert received == [(configuration, "arena-registry")]


@pytest.mark.parametrize("name", ["../allegro", "missing", "", "."])
def test_registry_never_falls_back(name):
    with pytest.raises(ValueError):
        HandRegistry().get(name)


def test_registry_checks_hand_identity():
    with pytest.raises(ValueError, match="different hand_id"):
        HandRegistry().get("allegro", {"hand_id": "shadow"})


def test_object_overrides_do_not_mutate_registry():
    assert ObjectRegistry().get("cube", {"mass": 0.2}).mass == 0.2
    assert ObjectRegistry().get("cube").mass == 0.1


@pytest.mark.parametrize("path", ["missingseparator", ":call", "module:"])
def test_invalid_factory_contract(path):
    with pytest.raises(ValueError, match="module:callable"):
        import_factory(path)


@pytest.mark.parametrize("flag", ["--physics", "--backend"])
def test_physics_cli_alias_and_hundred_steps_default(flag, capsys):
    assert main(["scene", "run", "--hand", "allegro", "--object", "cylinder", flag, "physx", "--dry-run"]) == 0
    request = json.loads(capsys.readouterr().out)
    assert request["backend"] == "physx"
    assert request["steps"] == 100
    assert request["config"]["object"]["kind"] == "cylinder"
    assert build_parser().parse_args(["arena", "run", "cube_goal_pose"]).steps == 20
