"""Example B: record a measured Shadow pose, reload its JSON and replay through PhysX."""

import json
from pathlib import Path

from dexterous_lab.evaluation.runner import EvaluationRunner


if __name__ == '__main__':
    runner = EvaluationRunner()
    captured = runner.run('capture', include_sphere=True)
    candidate = Path(captured['run_directory']) / 'trial_000/candidate.json'
    replay = runner.run('replay', input_path=candidate, include_sphere=True)
    print(json.dumps({'captured': captured, 'replayed': replay}, indent=2))
