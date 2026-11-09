"""Check composition and telemetry against a real bounded-run evidence bundle."""

import json
from pathlib import Path

import pytest

from dexterous_lab.config import PROJECT_ROOT, load_scene


def test_pose_override_is_consumed():
    config_path = PROJECT_ROOT / "configs/experiments/posed_cube.toml"
    specification = load_scene(config_path)
    assert specification["object"]["position_xyz"] == (-0.5, 0.05, 0.3)
    assert specification["object"]["scale"] == (1.2, 1.2, 1.2)
    assert specification["object"]["rotation_xyzw"][2] == pytest.approx(0.3826834323650898)


def test_cli_does_not_import_simulator_in_help_child():
    import os
    import subprocess
    import sys

    environment = dict(os.environ, PYTHONPATH=str(PROJECT_ROOT / "src"))
    child = subprocess.run(
        [sys.executable, "-c", "from dexterous_lab.cli import build_parser; import sys; build_parser(); "
         "assert 'isaacsim' not in sys.modules; assert 'pxr' not in sys.modules"],
        env=environment, capture_output=True, text=True, timeout=10,
    )
    assert child.returncode == 0, child.stderr
