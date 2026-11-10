import json
from pathlib import Path
from unittest.mock import patch

from dexterous_lab.runtime import run_worker, runtime_environment


def test_library_path_is_prepend_only():
    environment = runtime_environment({"LD_LIBRARY_PATH": "/existing/lib", "PYTHONPATH": "/existing/python"})
    assert environment["LD_LIBRARY_PATH"].endswith(":/existing/lib")
    assert "/torch/lib:" in environment["LD_LIBRARY_PATH"]
    assert environment["PYTHONPATH"].endswith(":/existing/python")
    assert runtime_environment(environment)["LD_LIBRARY_PATH"] == environment["LD_LIBRARY_PATH"]


def test_exit_zero_without_step_evidence_is_failure(tmp_path):
    request = {"kind": "scene", "steps": 20}
    with patch("dexterous_lab.runtime.subprocess.Popen") as process:
        process.return_value.wait.return_value = 0
        assert run_worker(request, tmp_path) == 1
    result = json.loads((Path(request["run_dir"]) / "result.json").read_text())
    assert result["passed"] is False
    assert result["grasp_success"] is None


def test_relative_output_directory_passes_absolute_request_to_child(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    request = {"kind": "scene", "steps": 100}
    with patch("dexterous_lab.runtime.subprocess.Popen") as process:
        process.return_value.wait.return_value = 0
        assert run_worker(request, Path("relative-output")) == 1
        command = process.call_args.args[0]
        assert Path(command[-1]).is_absolute()
        assert Path(command[-1]).is_file()


def test_worker_timeout_terminates_and_reaps_process():
    import subprocess
    from unittest.mock import Mock

    from dexterous_lab.runtime import wait_for_process

    child = Mock()
    child.wait.side_effect = [subprocess.TimeoutExpired("worker", 1), 0]
    assert wait_for_process(child, 1) == (None, "TimeoutExpired")
    child.terminate.assert_called_once()
    child.kill.assert_not_called()
    assert child.wait.call_count == 2


def test_worker_ignoring_termination_is_killed_and_reaped():
    import subprocess
    from unittest.mock import Mock

    from dexterous_lab.runtime import wait_for_process

    child = Mock()
    child.wait.side_effect = [
        subprocess.TimeoutExpired("worker", 1),
        subprocess.TimeoutExpired("worker", 10),
        -9,
    ]
    assert wait_for_process(child, 1) == (None, "TimeoutExpired")
    child.terminate.assert_called_once()
    child.kill.assert_called_once()
    child.wait.assert_called_with()


def test_worker_interruption_also_reaps_process():
    from unittest.mock import Mock

    from dexterous_lab.runtime import wait_for_process

    child = Mock()
    child.wait.side_effect = [KeyboardInterrupt(), 0]
    assert wait_for_process(child, 300) == (None, "KeyboardInterrupt")
    child.terminate.assert_called_once()
    assert child.wait.call_count == 2
