"""Explicit pose/data adapter, not a physical grasp validator.

Input format reference: DexGraspNet bd1b13d, grasp_generation/main.py
qpos serialization and scripts/validate_grasps.py pose decoding.
No Shadow joint correspondences or palm calibration are assumed.
"""

from math import isfinite

import numpy as np
from scipy.spatial.transform import Rotation

from dexterous_lab.grasp_synthesis.candidate import GraspCandidate


def checked_transform(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (4, 4) or not np.isfinite(result).all():
        raise ValueError("Frame transforms must be finite 4x4 matrices")
    if not np.allclose(result[3], [0, 0, 0, 1], atol=1e-7):
        raise ValueError("Transform has an invalid homogeneous row")
    rotation = result[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(rotation), 1.0):
        raise ValueError("Transform rotation must belong to SO(3)")
    return result


def source_qpos_to_candidate(qpos, *, joint_map, fixed_joint_positions, target_joint_limits,
                             T_W_O, T_Hsource_Htarget, object_id, hand_id, palm_frame,
                             seed, asset_version):
    """Convert an original source qpos to an explicitly calibrated candidate.

    Args:
        qpos: Source dict with WRJTxyz [m], WRJRxyz [extrinsic xyz radians], hand joints.
        joint_map: Explicit complete source->target joint-name correspondence. This
            alone does not establish axis equivalence or tendon executability.
        fixed_joint_positions: Explicit positions for extra target joints, e.g. wrists.
        target_joint_limits: Target joint-name->(lower,upper), covering all output joints.
        T_W_O: Object frame O to world W, 4x4.
        T_Hsource_Htarget: Calibrated target palm to source palm transform, 4x4.
        object_id: Object configuration identifier.
        hand_id: Hand configuration identifier.
        palm_frame: Actual target palm body name.
        seed: Candidate provenance seed.
        asset_version: Asset version or content fingerprint.

    Returns:
        GraspCandidate with unknown physical outcomes. Requires separate FK,
        tendon-constraint and physics checks before execution.
    """
    translations = ("WRJTx", "WRJTy", "WRJTz")
    rotations = ("WRJRx", "WRJRy", "WRJRz")
    pose_names = set(translations + rotations)
    if not pose_names.issubset(qpos):
        raise ValueError("Source qpos is missing translation or Euler fields")
    if set(qpos) - pose_names != set(joint_map):
        raise ValueError("joint_map must cover every source joint exactly")
    targets = list(joint_map.values())
    if len(set(targets)) != len(targets) or set(targets) & set(fixed_joint_positions):
        raise ValueError("Target joints must be unique and cannot overlap fixed joints")
    joints = {target: float(qpos[source]) for source, target in joint_map.items()}
    joints.update({name: float(value) for name, value in fixed_joint_positions.items()})
    if set(target_joint_limits) != set(joints):
        raise ValueError("target_joint_limits must cover the complete target joint set")
    for name, value in joints.items():
        lower, upper = target_joint_limits[name]
        if not all(isfinite(number) for number in (lower, upper, value)) or lower > upper or not lower <= value <= upper:
            raise ValueError(f"Target joint {name} is outside its valid finite range")
    T_O_Hsource = np.eye(4)
    T_O_Hsource[:3, :3] = Rotation.from_euler("xyz", [qpos[name] for name in rotations]).as_matrix()
    T_O_Hsource[:3, 3] = [qpos[name] for name in translations]
    T_W_O = checked_transform(T_W_O)
    T_W_Htarget = checked_transform(T_W_O @ checked_transform(T_O_Hsource) @ checked_transform(T_Hsource_Htarget))
    hand_pose = tuple(T_W_Htarget[:3, 3]) + tuple(Rotation.from_matrix(T_W_Htarget[:3, :3]).as_quat())
    object_pose = tuple(T_W_O[:3, 3]) + tuple(Rotation.from_matrix(T_W_O[:3, :3]).as_quat())
    return GraspCandidate(
        object_id=object_id, hand_id=hand_id, hand_root_pose=hand_pose, joint_positions=joints,
        object_pose=object_pose, seed=seed, algorithm="dexgraspnet-source-qpos-adapter:bd1b13d:unvalidated",
        asset_version=asset_version, hand_root_frame=palm_frame,
    )
