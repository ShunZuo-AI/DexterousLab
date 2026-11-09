"""Bounded pose capture/replay runs with preserved per-candidate failure evidence."""

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import uuid

from dexterous_lab.assets.catalog import save_json
from dexterous_lab.config import PROJECT_ROOT
from dexterous_lab.grasp_synthesis.candidate import GraspCandidate
from dexterous_lab.runtime import runtime_environment, shared_python
from dexterous_lab.scenes.builder import SceneBuilder


def read_candidates(path):
    path = Path(path)
    if path.suffix == '.jsonl':
        values = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    else:
        values = json.loads(path.read_text())
        values = values if isinstance(values, list) else [values]
    if not values or len(values) > 10:
        raise ValueError('Provide between 1 and 10 candidates')
    return [GraspCandidate(**value) for value in values]


class EvaluationRunner:
    def run(self, mode, *, input_path=None, object_id='cube', include_sphere=False, steps=100, seed=42, timeout=300):
        if mode not in ('capture', 'replay', 'batch') or steps < 100 or steps > 1000:
            raise ValueError('Supported modes capture/replay/batch require 100 to 1000 steps')
        candidates = read_candidates(input_path) if input_path else []
        if mode != 'capture' and not candidates:
            raise ValueError('Replay/batch requires an explicit candidate input')
        if mode == 'replay' and len(candidates) != 1:
            raise ValueError('Replay requires exactly one candidate')
        if any(candidate.hand_id != 'shadow' or candidate.object_id != object_id for candidate in candidates):
            raise ValueError('This initial evaluator supports Shadow and the selected matching object only')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        output = PROJECT_ROOT / 'outputs' / f'{stamp}-{mode}-{uuid.uuid4().hex[:8]}'
        output.mkdir(parents=True, exist_ok=False)
        request = {'mode': mode, 'steps': steps, 'seed': seed, 'run_dir': str(output),
                   'specification': SceneBuilder().specification('shadow', object_id, include_sphere),
                   'candidates': [candidate.to_dict() for candidate in candidates], 'policy': 'hold',
                   'criteria': {'lift_height_m': 0.03, 'hold_steps': 20, 'max_linear_speed_m_s': 0.1,
                                'contact_force_threshold_n': 0.01},
                   'scope': 'Rigid-object candidate replay; no DexGarmentLab policy/garment reproduction'}
        save_json(output / 'request.json', request)
        command = [shared_python(), '-m', 'dexterous_lab.evaluation.worker', str(output / 'request.json')]
        with (output / 'simulation.log').open('x') as stream:
            child = subprocess.Popen(command, env=runtime_environment(), cwd=output, stdout=stream, stderr=subprocess.STDOUT)
            try:
                code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                code = -1
        report = output / 'report.json'
        summary = json.loads(report.read_text()) if report.exists() else None
        passed = code == 0 and summary is not None and summary.get('completed') is True
        save_json(output / 'launch_result.json', {'command': command, 'return_code': code, 'passed': passed, 'report': summary})
        if not passed:
            raise ValueError(f'Experiment failed; inspect {output / "simulation.log"}')
        return {'run_directory': str(output), 'report': summary}


def summarize_trials(trials):
    total = len(trials)
    loaded = sum(bool(row.get('loaded')) for row in trials)
    simulated = sum(bool(row.get('simulation_completed')) for row in trials)
    evaluated = sum(row.get('success') is not None for row in trials)
    successful = sum(row.get('success') is True for row in trials)
    reasons = {}
    for row in trials:
        if row.get('failure_reason'):
            reasons[row['failure_reason']] = reasons.get(row['failure_reason'], 0) + 1
    return {'attempted': total, 'loaded': loaded, 'simulation_completed': simulated, 'evaluated': evaluated,
            'successful': successful, 'success_rate_evaluated': successful / evaluated if evaluated else None,
            'success_rate_attempted': successful / total if total and evaluated else None, 'failure_reasons': reasons}
