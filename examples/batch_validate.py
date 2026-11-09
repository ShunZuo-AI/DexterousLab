"""Example C: validate an explicitly supplied file of up to 10 measured candidates."""

import argparse
import json
from pathlib import Path

from dexterous_lab.evaluation.runner import EvaluationRunner


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(EvaluationRunner().run('batch', input_path=args.input, include_sphere=True), indent=2))
