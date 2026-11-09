"""Launch child processes in the existing Arena environment and retain evidence."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

from dexterous_lab.config import PROJECT_ROOT
from dexterous_lab.storage import ensure_storage, storage_environment


def arena_root():
    return Path(os.environ.get("DEXLAB_ARENA_ROOT", "/root/gpufree-data/IsaacLab-Arena"))


def runtime_environment(base=None):
    result = dict(os.environ if base is None else base)
    ensure_storage()
    result.update(storage_environment())
    torch_lib = arena_root() / ".venv/lib/python3.12/site-packages/torch/lib"
    paths = [str(torch_lib)]
    paths.extend(path for path in result.get("LD_LIBRARY_PATH", "").split(":") if path and path != str(torch_lib))
    result["LD_LIBRARY_PATH"] = ":".join(paths)
    sources = [str(PROJECT_ROOT / "src"), str(arena_root())]
    sources.extend(path for path in result.get("PYTHONPATH", "").split(":") if path)
    result["PYTHONPATH"] = ":".join(dict.fromkeys(sources))
    result["PYTHONDONTWRITEBYTECODE"] = "1"
    result["PYTHONUNBUFFERED"] = "1"
    result["OMNI_KIT_ACCEPT_EULA"] = "YES"
    result["ACCEPT_EULA"] = "Y"
    result["ISAACLAB_ARENA_FORCE_EXIT_ON_COMPLETE"] = "1"
    return result


def shared_python():
    python = arena_root() / ".venv/bin/python"
    if not python.is_file():
        raise ValueError(f"Shared Arena interpreter is missing: {python}; no environment will be created")
    return str(python)


def write_json(path, data):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def run_worker(request, output_root=None, timeout=300):
    root = (Path(output_root) if output_root else PROJECT_ROOT / "outputs").absolute()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = root / f"{stamp}-{request['kind']}-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    request["run_dir"] = str(run_dir.absolute())
    write_json(run_dir / "request.json", request)
    command = [shared_python(), "-m", "dexterous_lab.integrations.arena.worker", str(run_dir / "request.json")]
    print(f"Run: {run_dir}", flush=True)
    return_code = None
    error = None
    try:
        with (run_dir / "simulation.log").open("x", encoding="utf-8") as stream:
            child = subprocess.Popen(command, cwd=run_dir, env=runtime_environment(), stdout=stream, stderr=subprocess.STDOUT)
            try:
                return_code = child.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                child.terminate()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                error = type(exc).__name__
    except OSError as exc:
        error = str(exc)
    evidence_path = run_dir / "simulation_result.json"
    evidence = json.loads(evidence_path.read_text()) if evidence_path.is_file() else None
    ok = return_code == 0 and evidence is not None and evidence.get("steps_completed") == request["steps"]
    result = {"passed": ok, "return_code": return_code, "error": error, "command": command,
              "simulation": evidence, "grasp_success": None,
              "scope": "zero-action environment smoke test; no grasp validation"}
    write_json(run_dir / "result.json", result)
    print(json.dumps(result, indent=2), flush=True)
    if not ok:
        log = run_dir / "simulation.log"
        if log.is_file():
            print("\n".join(log.read_text(errors="replace").splitlines()[-35:]), file=sys.stderr)
    return 0 if ok else 1
