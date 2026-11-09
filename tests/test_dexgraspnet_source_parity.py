"""Compare migrated algebra against read-only fixed-revision reference functions.

The fixtures below are analytic test geometries, not a Shadow model or a grasp generator.
No paper entry point, installer, mesh loader or simulator is executed.
"""

from pathlib import Path
from types import SimpleNamespace
import hashlib
import json

import pytest
import torch

from dexterous_lab.grasp_generation.dexgraspnet.energy import evaluate_models
from dexterous_lab.grasp_generation.dexgraspnet.optimizer import AnnealingConfig, AnnealingOptimizer
from dexterous_lab.grasp_generation.dexgraspnet.optimization import optimize_models
from dexterous_lab.config import PROJECT_ROOT


REFERENCE = PROJECT_ROOT / "research-repos/DexGraspNet/grasp_generation/utils"


def reference_function(filename, name):
    path = REFERENCE / filename
    if not path.is_file():
        pytest.skip("Read-only DexGraspNet reference checkout is required for source parity")
    manifest = json.loads((PROJECT_ROOT / "docs/paper_reproductions/source_manifest.json").read_text())
    source_record = manifest["repositories"]["DexGraspNet"]
    assert source_record["commit"] == "bd1b13d7248729af117e1d46aaa6266b147a3c7b"
    fingerprint = source_record["files"][f"grasp_generation/utils/{filename}"]["sha256"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == fingerprint, "Reference source changed after analysis"
    namespace = {"__file__": str(path)}
    exec(compile(path.read_text(), str(path), "exec"), namespace)
    return namespace[name]


class AnalyticFixtureHand:
    n_dofs = 2
    n_contact_candidates = 7

    def __init__(self, parameters, indices):
        self.joints_lower = torch.tensor([-0.5, -0.5], device=parameters.device)
        self.joints_upper = -self.joints_lower
        self.chain = SimpleNamespace(forward_kinematics=lambda joints: {"test": joints})
        self.set_parameters(parameters, indices)

    def set_parameters(self, parameters, indices):
        self.hand_pose = parameters
        parameters.retain_grad()
        self.contact_point_indices = indices
        self.global_translation = parameters[:, :3]
        self.global_rotation = torch.eye(3, device=parameters.device).repeat(len(parameters), 1, 1)
        self.current_status = self.chain.forward_kinematics(parameters[:, 9:])
        offsets = indices.to(parameters.dtype).unsqueeze(-1) * torch.tensor([0.02, -0.01, 0.03], device=parameters.device)
        self.contact_points = parameters[:, None, :3] + offsets + parameters[:, None, 9:10] * 0.05

    def cal_distance(self, points):
        return 0.8 - torch.linalg.vector_norm(points - self.hand_pose[:, None, :3], dim=-1)

    def self_penetration(self):
        return self.hand_pose[:, 9:].square().sum(dim=1) * 0.01


class AnalyticFixtureObject:
    def __init__(self, device):
        self.device = device
        self.object_scale_tensor = torch.tensor([[0.5, 0.7]], device=device)
        self.surface_points_tensor = torch.tensor([[[0.1, 0.2, 0.3], [1.0, 0, 0]]] * 2, device=device)

    def cal_distance(self, points):
        normals = points.detach() / points.detach().norm(dim=-1, keepdim=True)
        return 0.6 - points.norm(dim=-1), normals


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_five_terms_and_parameter_gradients_match_original_source(device):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    parameters = torch.linspace(0.1, 1.0, 22, device=device).reshape(2, 11).requires_grad_()
    indices = torch.tensor([[0, 1, 2, 3], [3, 4, 5, 6]], device=device)
    hand = AnalyticFixtureHand(parameters, indices)
    object_model = AnalyticFixtureObject(device)
    original = reference_function("energy.py", "cal_energy")(hand, object_model, verbose=True)
    expected_gradient = torch.autograd.grad(original[0].sum(), parameters, retain_graph=True)[0]
    migrated = evaluate_models(hand, object_model)
    actual_gradient = torch.autograd.grad(migrated.total.sum(), parameters)[0]
    actual = (migrated.total, migrated.force_closure, migrated.distance, migrated.penetration,
              migrated.self_penetration, migrated.joints)
    for actual_term, expected_term in zip(actual, original, strict=True):
        torch.testing.assert_close(actual_term, expected_term, rtol=2e-5, atol=2e-5)
    torch.testing.assert_close(actual_gradient, expected_gradient, rtol=2e-5, atol=2e-5)


@pytest.mark.parametrize("switch_probability", [0.0, 1.0])
def test_annealing_updates_indices_acceptance_and_rollback_match_source(switch_probability):
    parameters = torch.linspace(0.1, 1.0, 22).reshape(2, 11).requires_grad_()
    indices = torch.zeros(2, 4, dtype=torch.long)
    hand = AnalyticFixtureHand(parameters, indices)
    original = reference_function("optimizer.py", "Annealing")(
        hand, switch_possibility=switch_probability, starting_temperature=0.001,
        annealing_period=2, stepsize_period=3, device="cpu",
    )
    migrated = AnnealingOptimizer(parameters, indices, 7, AnnealingConfig(
        switch_probability=switch_probability, initial_temperature=0.001, temperature_period=2, step_period=3,
    ), seed=123)

    def objective(values, contacts):
        return values.square().sum(dim=1) + contacts.float().sum(dim=1) * 10

    energy = objective(hand.hand_pose, hand.contact_point_indices)
    energy.sum().backward(retain_graph=True)
    torch.manual_seed(123)
    for _ in range(6):
        step_size = original.try_step()
        original.zero_grad()
        proposed_energy = objective(hand.hand_pose, hand.contact_point_indices)
        proposed_energy.sum().backward(retain_graph=True)
        accepted, temperature = original.accept_step(energy, proposed_energy)
        with torch.no_grad():
            energy[accepted] = proposed_energy[accepted]
        result = migrated.step(objective)
        torch.testing.assert_close(migrated.parameters, hand.hand_pose)
        torch.testing.assert_close(migrated.contact_indices, hand.contact_point_indices)
        torch.testing.assert_close(migrated.parameters.grad, hand.hand_pose.grad)
        torch.testing.assert_close(migrated.second_moment, original.ema_grad_hand_pose)
        torch.testing.assert_close(result["accepted"], accepted)
        torch.testing.assert_close(result["energy"], energy)
        assert result["step_size"] == pytest.approx(step_size.item(), rel=1e-6)
        assert result["temperature"] == pytest.approx(temperature.item(), rel=1e-6)
    if switch_probability:
        assert not result["accepted"].any()


def test_supplied_model_optimization_loop_returns_consistent_final_state():
    parameters = torch.linspace(0.1, 1.0, 22).reshape(2, 11).requires_grad_()
    indices = torch.tensor([[0, 1, 2, 3], [3, 4, 5, 6]])
    hand = AnalyticFixtureHand(parameters, indices)
    result = optimize_models(hand, AnalyticFixtureObject("cpu"), iterations=3, seed=123)
    assert len(result.trace) == 3
    torch.testing.assert_close(hand.hand_pose, result.parameters)
    torch.testing.assert_close(hand.contact_point_indices, result.contact_indices)
    assert torch.isfinite(result.energy_terms.total).all()
    assert "success" not in result.trace[-1]
