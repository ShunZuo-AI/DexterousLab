"""Run the studied generation loop against explicitly supplied differentiable models.

Reference: DexGraspNet bd1b13d, grasp_generation/scripts/generate_grasps.py:generate.
Models must already be initialized; this does not invent a replacement FK/SDF backend.
"""

from dataclasses import dataclass

import torch

from dexterous_lab.grasp_generation.dexgraspnet.energy import EnergyTerms, evaluate_models
from dexterous_lab.grasp_generation.dexgraspnet.optimizer import AnnealingOptimizer


@dataclass
class OptimizationResult:
    parameters: torch.Tensor
    contact_indices: torch.Tensor
    energy_terms: EnergyTerms
    trace: list[dict]
    reproduction_level: str = "algorithm-components-with-supplied-geometry-backends"


def optimize_models(hand_model, object_model, *, iterations, config=None, weights=None, seed=42):
    """Optimize initialized hand/object models with source-style annealing.

    Args:
        hand_model: Initialized model following the original hand API, including
            hand_pose, contact_point_indices and n_contact_candidates.
        object_model: Initialized object model with the original SDF/sample API.
        iterations: Positive number of optimization proposals.
        config: Optional AnnealingConfig; graph-history behavior is explicit there.
        weights: Optional EnergyWeights.
        seed: Random seed for contact proposals and acceptance.

    Returns:
        OptimizationResult with detached parameters and per-iteration diagnostics.
        Does not return physical success or imply a validated grasp dataset.
    """
    if type(iterations) is not int or iterations < 1:
        raise ValueError("iterations must be a positive integer")
    if hand_model.hand_pose is None or hand_model.contact_point_indices is None:
        raise ValueError("Supply initialized differentiable hand/object models; no fallback sampler is provided")
    optimizer = AnnealingOptimizer(hand_model.hand_pose, hand_model.contact_point_indices,
                                   hand_model.n_contact_candidates, config, seed)

    def objective(parameters, contacts):
        hand_model.set_parameters(parameters, contacts)
        return evaluate_models(hand_model, object_model, weights).total

    trace = []
    for iteration in range(iterations):
        step = optimizer.step(objective)
        trace.append({
            "iteration": iteration + 1, "mean_energy": float(step["energy"].mean().item()),
            "minimum_energy": float(step["energy"].min().item()),
            "accepted": int(step["accepted"].sum().item()), "step_size": step["step_size"],
            "temperature": step["temperature"],
        })
    hand_model.set_parameters(optimizer.parameters, optimizer.contact_indices)
    with torch.no_grad():
        terms = evaluate_models(hand_model, object_model, weights)
    return OptimizationResult(optimizer.parameters.detach().clone(), optimizer.contact_indices.clone(), terms, trace)
