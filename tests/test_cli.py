"""Public commands preserve configuration selection and worker boundaries."""

import json
import subprocess
import sys
from unittest.mock import patch

import pytest

from dexterous_lab.cli import main
from dexterous_lab.config import PROJECT_ROOT


@pytest.mark.parametrize(
    ("hand", "object_id", "action_dim"),
    [("allegro", "cube", 23), ("allegro", "cylinder", 23), ("shadow", "cube", 20)],
)
def test_scene_dry_run_selects_components_without_starting_simulation(
    hand, object_id, action_dim, capsys
):
    with patch("dexterous_lab.cli.run_worker") as worker:
        assert main([
            "scene", "run", "--hand", hand, "--object", object_id,
            "--physics", "physx", "--dry-run",
        ]) == 0
    worker.assert_not_called()
    request = json.loads(capsys.readouterr().out)
    assert request["config"]["hand_id"] == hand
    assert request["config"]["object_id"] == object_id
    assert request["config"]["robot"]["action_dim"] == action_dim
    assert request["steps"] == 100


def test_official_run_keeps_worker_arguments():
    with patch("dexterous_lab.cli.run_worker", return_value=0) as worker:
        assert main(["arena", "run", "dexsuite_lift", "--steps", "100"]) == 0
    request, output_dir, timeout = worker.call_args.args
    assert request == {
        "kind": "arena", "steps": 100, "num_envs": 1, "seed": 42,
        "backend": "physx", "policy": "zero_action", "environment": "dexsuite_lift",
    }
    assert output_dir is None
    assert timeout == 300


def test_inventory_distinguishes_configuration_from_validation(capsys):
    assert main(["assets", "list"]) == 0
    inventory = json.loads(capsys.readouterr().out)
    assert set(inventory["robots"]) == {"allegro", "shadow"}
    assert "not evidence" in inventory["notice"]
    assert main(["scene", "list"]) == 0
    assert json.loads(capsys.readouterr().out)["grasp_validation"] is False


@pytest.mark.parametrize("action", ["capture", "replay", "batch"])
def test_experiment_dispatch_keeps_options(action, capsys):
    arguments = ["experiment", action, "--object", "cylinder", "--steps", "120"]
    if action != "capture":
        arguments += ["--input", "candidates.jsonl"]
    with patch("dexterous_lab.evaluation.runner.EvaluationRunner.run", return_value={}) as run:
        assert main(arguments) == 0
    assert run.call_args.args == (action,)
    assert run.call_args.kwargs["object_id"] == "cylinder"
    assert run.call_args.kwargs["steps"] == 120
    assert json.loads(capsys.readouterr().out) == {}


@pytest.mark.parametrize("action", ["fetch", "convert", "validate", "preview"])
def test_asset_dispatch_calls_only_selected_operation(action, capsys):
    with patch("dexterous_lab.assets.manager.AssetManager") as manager:
        operation = getattr(manager.return_value, action)
        operation.return_value = {"status": "test"}
        assert main(["assets", action, "--id", "vendor/hand/right"]) == 0
    assert operation.call_args.args[0] == "vendor/hand/right"
    assert json.loads(capsys.readouterr().out) == {"status": "test"}


def test_invalid_hand_reports_error_in_child_process(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT / "src"))
    result = subprocess.run(
        [sys.executable, "-m", "dexterous_lab", "scene", "run",
         "--hand", "missing", "--dry-run"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 2
    assert "Unsupported robots" in result.stderr
    assert not result.stdout


def test_parser_does_not_import_simulator(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(PROJECT_ROOT / "src"))
    code = (
        "import sys; from dexterous_lab.cli import build_parser; build_parser(); "
        "assert not any(name in sys.modules for name in ('isaacsim', 'isaaclab', 'pxr'))"
    )
    subprocess.run([sys.executable, "-c", code], check=True, timeout=30)


def test_screenshot_is_explicit_and_does_not_change_default(capsys):
    assert main(["scene", "run", "--dry-run", "--screenshot"]) == 0
    request = json.loads(capsys.readouterr().out)
    assert request["screenshot"] is True
    assert main(["scene", "run", "--dry-run"]) == 0
    assert "screenshot" not in json.loads(capsys.readouterr().out)
