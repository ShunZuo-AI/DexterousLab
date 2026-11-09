"""Independent numeric episode writer informed by DexGarmentLab BaseEnv recording.

Reuse existing GraspCandidate serialization; NPZ contains no object arrays or pickle.
"""

import json
from pathlib import Path

import numpy as np

from dexterous_lab.assets.catalog import save_json
from dexterous_lab.datasets.writer import GraspDatasetWriter
from dexterous_lab.grasp_synthesis.candidate import GraspCandidate


class DatasetCollector:
    def __init__(self, directory, metadata):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=False)
        save_json(self.directory / 'metadata.json', metadata)
        self.stream = (self.directory / 'states.jsonl').open('x')
        self.frames = []

    def record(self, snapshot, action):
        row = dict(snapshot, action=np.asarray(action, dtype=float).tolist())
        encoded = json.dumps(row, allow_nan=False)
        self.stream.write(encoded + '\n')
        self.stream.flush()
        self.frames.append(row)

    def save_candidate(self, snapshot, *, object_id, hand_id, seed, asset_version, tendon_positions):
        candidate = GraspCandidate(
            object_id=object_id, hand_id=hand_id, hand_root_pose=snapshot['hand_root_pose'][0],
            hand_root_frame=snapshot['hand_root_frame'],
            joint_positions=dict(zip(snapshot['joint_names'], snapshot['joint_positions'][0], strict=True)),
            object_pose=snapshot['object_pose'][0], seed=seed, asset_version=asset_version,
            tendon_positions=tendon_positions, algorithm='measured-pose-capture:not-a-grasp-generator',
            contact_points=snapshot['contact_points'][0],
        )
        with GraspDatasetWriter(self.directory / 'candidates.jsonl') as writer:
            writer.write(candidate)
        save_json(self.directory / 'candidate.json', candidate.to_dict())
        return candidate

    def finish(self, result):
        self.stream.close()
        if not self.frames:
            raise ValueError('No episode frames collected')
        names = self.frames[0]['joint_names']
        if any(frame['joint_names'] != names for frame in self.frames):
            raise ValueError('Joint ordering changed within episode')
        points, offsets = [], [0]
        for frame in self.frames:
            points.extend(frame['contact_points'][0])
            offsets.append(len(points))
        with (self.directory / 'trajectory.npz').open('xb') as stream:
            np.savez_compressed(stream, step=np.array([f['step'] for f in self.frames]), joint_names=np.array(names),
                joint_positions=np.array([f['joint_positions'][0] for f in self.frames]),
                joint_velocities=np.array([f['joint_velocities'][0] for f in self.frames]),
                hand_root_pose=np.array([f['hand_root_pose'][0] for f in self.frames]),
                robot_base_pose=np.array([f['robot_base_pose'][0] for f in self.frames]),
                object_pose=np.array([f['object_pose'][0] for f in self.frames]),
                action=np.array([f['action'] for f in self.frames]), contact_points=np.array(points).reshape(-1, 3),
                contact_offsets=np.array(offsets),
                contact_normal_forces_W=np.array([f['contact_normal_forces_W'][0] for f in self.frames]))
        save_json(self.directory / 'result.json', result)
