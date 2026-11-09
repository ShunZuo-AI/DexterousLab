"""DexGraspNet energy algebra, independently expressed from the inspected source.

Reference: PKU-EPIC/DexGraspNet bd1b13d, grasp_generation/utils/energy.py
and hand_model.py:self_penetration, by Jialiang Zhang and Ruicheng Wang.
Source README states CC BY-NC 4.0; see docs/paper_reproductions. This module
does not supply the original mesh SDF, hand FK, initializer or validation.
"""

from dataclasses import dataclass
from math import isfinite

import torch


@dataclass(frozen=True)
class EnergyWeights:
    distance: float = 100.0
    penetration: float = 100.0
    self_penetration: float = 10.0
    joints: float = 1.0

    def __post_init__(self):
        if any(not isfinite(value) or value < 0 for value in self.__dict__.values()):
            raise ValueError("Energy weights must be finite and nonnegative")


@dataclass
class EnergyTerms:
    force_closure: torch.Tensor
    distance: torch.Tensor
    penetration: torch.Tensor
    self_penetration: torch.Tensor
    joints: torch.Tensor
    total: torch.Tensor


def self_penetration_penalty(keypoints, separation=0.02):
    """Sum ordered keypoint-pair penalties, matching source coincidence masking.

    Args:
        keypoints: World or common-frame keypoint coordinates [B,K,3], in metres.
        separation: Minimum keypoint separation in metres.

    Returns:
        Per-candidate penalty [B]. This is not a mesh collision test.
    """
    if keypoints.ndim != 3 or keypoints.shape[-1] != 3 or keypoints.shape[1] < 1:
        raise ValueError("Self-penetration keypoints must have shape [B,K,3], K>0")
    if not isfinite(separation) or separation <= 0:
        raise ValueError("separation must be finite and positive")
    offsets = keypoints[:, :, None, :] - keypoints[:, None, :, :] + 1e-13
    distances = offsets.square().sum(dim=-1).sqrt()
    distances = torch.where(distances < 1e-6, torch.full_like(distances, 1e6), distances)
    return (separation - distances).clamp_min(0).sum(dim=(1, 2))


def evaluate_energy(contact_points, contact_distances, contact_normals, object_in_hand_distances,
                    self_penetration, joint_positions, lower_limits, upper_limits, weights=None):
    """Aggregate five source energy terms from a differentiable geometry backend.

    Args:
        contact_points: Hand contact positions [B,C,3] in one common metric frame.
        contact_distances: Inside-positive object SDF at those points [B,C].
        contact_normals: Source-compatible outward query normals [B,C,3]; detached here.
        object_in_hand_distances: Inside-positive hand SDF at object surface samples [B,N].
        self_penetration: Backend self-collision penalty [B].
        joint_positions: Optimized hand joint angles [B,J], excluding global pose.
        lower_limits: Joint lower bounds [J] or [B,J], in radians.
        upper_limits: Joint upper bounds [J] or [B,J], in radians.
        weights: EnergyWeights; source defaults apply when omitted.

    Returns:
        EnergyTerms containing each [B] term and weighted total. No success decision.
    """
    if contact_points.ndim != 3 or contact_points.shape[-1] != 3 or contact_points.shape[1] == 0:
        raise ValueError("contact_points must have shape [B,C,3], C>0")
    batch_size, contact_count, _ = contact_points.shape
    if contact_distances.shape != (batch_size, contact_count) or contact_normals.shape != contact_points.shape:
        raise ValueError("Contact distances/normals do not match contact point shape")
    if object_in_hand_distances.ndim != 2 or object_in_hand_distances.shape[0] != batch_size:
        raise ValueError("object_in_hand_distances must have shape [B,N]")
    if self_penetration.shape != (batch_size,) or joint_positions.ndim != 2 or joint_positions.shape[0] != batch_size:
        raise ValueError("Self-penetration/joints must have matching batch dimensions")
    for limits in (lower_limits, upper_limits):
        if limits.shape not in (joint_positions.shape, joint_positions.shape[1:]):
            raise ValueError("Joint bounds must have shape [J] or [B,J]")
    if torch.any(lower_limits > upper_limits).item():
        raise ValueError("Joint lower bounds exceed upper bounds")
    values = (contact_points, contact_distances, contact_normals, object_in_hand_distances,
              self_penetration, joint_positions, lower_limits, upper_limits)
    if any(not value.is_floating_point() or value.device != contact_points.device for value in values):
        raise ValueError("Energy inputs must be floating tensors on the same device")
    if any(not torch.isfinite(value).all().item() for value in values):
        raise ValueError("Energy inputs must be finite")
    weights = weights or EnergyWeights()
    normals = contact_normals.detach()
    resultant_force = normals.sum(dim=1)
    resultant_moment = torch.linalg.cross(contact_points, normals, dim=-1).sum(dim=1)
    force_closure = resultant_force.square().sum(dim=-1) + resultant_moment.square().sum(dim=-1)
    distance = contact_distances.abs().sum(dim=-1)
    penetration = object_in_hand_distances.clamp_min(0).sum(dim=-1)
    joints = ((joint_positions - upper_limits).clamp_min(0) + (lower_limits - joint_positions).clamp_min(0)).sum(dim=-1)
    total = (force_closure + weights.distance * distance + weights.penetration * penetration
             + weights.self_penetration * self_penetration + weights.joints * joints)
    return EnergyTerms(force_closure, distance, penetration, self_penetration, joints, total)


def evaluate_models(hand_model, object_model, weights=None):
    """Adapt the original HandModel/ObjectModel method contract without importing it.

    Args:
        hand_model: Differentiable model with contact_points, hand_pose, limits,
            cal_distance and self_penetration, following the inspected source API.
        object_model: Model with cal_distance, object_scale_tensor and surface_points_tensor.
        weights: Optional EnergyWeights.

    Returns:
        Five terms and weighted total, with the original scale application.
    """
    distances, normals = object_model.cal_distance(hand_model.contact_points)
    scales = object_model.object_scale_tensor.reshape(-1, 1, 1)
    object_samples = object_model.surface_points_tensor * scales
    return evaluate_energy(
        hand_model.contact_points, distances, normals, hand_model.cal_distance(object_samples),
        hand_model.self_penetration(), hand_model.hand_pose[:, 9:],
        hand_model.joints_lower, hand_model.joints_upper, weights,
    )
