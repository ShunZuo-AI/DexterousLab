"""Generate explicitly labelled local baseline perturbations, not paper grasp synthesis."""

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from dexterous_lab.datasets.writer import GraspDatasetWriter
from dexterous_lab.evaluation.runner import read_candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seed', default=42, type=int)
    args = parser.parse_args()
    candidates = read_candidates(args.input)
    if len(candidates) != 1:
        raise ValueError('Provide one measured reference pose')
    baseline = candidates[0]
    rng = np.random.default_rng(args.seed)
    with GraspDatasetWriter(args.output) as writer:
        for index in range(10):
            pose = list(baseline.hand_root_pose)
            if index:
                pose[:2] = np.array(pose[:2]) + rng.uniform(-0.01, 0.01, 2)
            writer.write(replace(baseline, hand_root_pose=pose, seed=args.seed + index,
                algorithm='measured-pose-local-translation-perturbation:not-paper-grasp-generation',
                success=None, collision=None, stability=None, contact_points=None))
    print(args.output)


if __name__ == '__main__':
    main()
