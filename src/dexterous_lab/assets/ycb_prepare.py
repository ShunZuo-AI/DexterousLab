"""Launch YCB conversion in the installed Arena runtime."""

from datetime import datetime, timezone
import json
import subprocess
import uuid

from dexterous_lab.assets.ycb import OBJECTS
from dexterous_lab.config import PROJECT_ROOT
from dexterous_lab.runtime import runtime_environment, shared_python, wait_for_process, write_json


def prepare_objects(names):
    """Convert downloaded samples and create scene configurations in a child process."""
    if not names or any(name not in OBJECTS for name in names):
        raise ValueError("Select at least one supported YCB sample")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = PROJECT_ROOT / "outputs" / f"{stamp}-ycb-prepare-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    write_json(run_dir / "request.json", {"objects": names, "run_dir": str(run_dir)})
    command = [shared_python(), "-m", "dexterous_lab.assets.ycb_worker", str(run_dir / "request.json")]
    print(f"YCB preparation log: {run_dir / 'conversion.log'}", flush=True)
    with (run_dir / "conversion.log").open("x") as stream:
        child = subprocess.Popen(
            command, cwd=run_dir, env=runtime_environment(),
            stdout=stream, stderr=subprocess.STDOUT,
        )
        code, error = wait_for_process(child, timeout=300)
    report_path = run_dir / "result.json"
    if code != 0 or not report_path.is_file():
        raise ValueError(f"YCB preparation failed ({error or code}); see {run_dir / 'conversion.log'}")
    return json.loads(report_path.read_text())
