"""Reproducible small sequential GPU verification; run with shared Python + PYTHONPATH=src."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
ids = ['unitree/dex3_1/right', 'leap/leap_hand_v1/right', 'wuji/hand_v1/right',
       'custom/cube', 'custom/cylinder']
results = []
for asset in ids:
    command = [str(ROOT / 'scripts/dexlab'), 'assets', 'validate', '--id', asset, '--steps', '100']
    child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    log = ROOT / 'docs/asset_aggregation' / (asset.replace('/', '-') + '-command.log')
    log.write_text(child.stdout + child.stderr)
    entry = {'asset_id': asset, 'command': command, 'return_code': child.returncode, 'command_log': str(log)}
    results.append(entry)
    print(asset, child.returncode, flush=True)
(ROOT / 'docs/asset_aggregation/batch-results.json').write_text(json.dumps(results, indent=2) + '\n')
sys.exit(int(any(entry['return_code'] for entry in results)))
