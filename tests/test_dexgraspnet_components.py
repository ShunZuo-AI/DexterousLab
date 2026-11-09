from types import SimpleNamespace

import pytest
import torch

from dexterous_lab.grasp_generation.dexgraspnet.energy import EnergyWeights, evaluate_energy, self_penetration_penalty
from dexterous_lab.grasp_generation.dexgraspnet.optimizer import AnnealingConfig, AnnealingOptimizer


def energy_fixture(dtype=torch.float64):
    generator = torch.Generator().manual_seed(9)
    return {
        "contact_points": torch.randn(2, 4, 3, dtype=dtype, generator=generator, requires_grad=True),
        "contact_distances": torch.tensor([[0.1, -0.1, 0.2, -0.2]] * 2, dtype=dtype, requires_grad=True),
        "contact_normals": torch.randn(2, 4, 3, dtype=dtype, generator=generator, requires_grad=True),
        "object_in_hand_distances": torch.tensor([[0.1, -0.2, 0.3]] * 2, dtype=dtype, requires_grad=True),
        "self_penetration": torch.tensor([0.02, 0.03], dtype=dtype, requires_grad=True),
        "joint_positions": torch.tensor([[-2.0, 2.0], [0.5, -0.5]], dtype=dtype, requires_grad=True),
        "lower_limits": torch.tensor([-1.0, -1.0], dtype=dtype),
        "upper_limits": torch.tensor([1.0, 1.0], dtype=dtype),
    }


def test_energy_components_and_original_normal_gradient_contract():
    values = energy_fixture()
    terms = evaluate_energy(**values)
    torch.testing.assert_close(terms.distance, torch.tensor([0.6, 0.6], dtype=torch.float64))
    torch.testing.assert_close(terms.penetration, torch.tensor([0.4, 0.4], dtype=torch.float64))
    torch.testing.assert_close(terms.joints, torch.tensor([2.0, 0.0], dtype=torch.float64))
    terms.total.sum().backward()
    assert values["contact_normals"].grad is None
    assert torch.isfinite(values["contact_points"].grad).all()
    assert values["object_in_hand_distances"].grad[0].tolist() == [100.0, 0.0, 100.0]


def test_energy_gradient_finite_difference():
    values = energy_fixture()
    contacts = values.pop("contact_points")
    assert torch.autograd.gradcheck(lambda points: evaluate_energy(contact_points=points, **values).total, (contacts,))


def test_self_collision_is_ordered_and_coincident_pairs_are_masked():
    points = torch.tensor([[[0.0, 0, 0], [0.01, 0, 0]]], dtype=torch.float64, requires_grad=True)
    penalty = self_penetration_penalty(points)
    assert penalty.item() == pytest.approx(0.02)
    penalty.sum().backward()
    assert torch.isfinite(points.grad).all()
    assert self_penetration_penalty(torch.zeros(1, 3, 3)).item() == 0


def test_bad_shapes_and_nonfinite_energy_are_rejected():
    values = energy_fixture()
    values["contact_distances"] = torch.zeros(2, 3)
    with pytest.raises(ValueError, match="shape"):
        evaluate_energy(**values)
    values = energy_fixture()
    values["self_penetration"] = torch.tensor([float("nan"), 0.0])
    with pytest.raises(ValueError, match="finite"):
        evaluate_energy(**values)


@pytest.mark.parametrize("config", [{"decay": 0}, {"initial_temperature": -1}, {"step_period": 0},
                                    {"current_gradient_weight": 1.2}, {"switch_probability": float("nan")}])
def test_optimizer_config_errors(config):
    with pytest.raises(ValueError):
        AnnealingConfig(**config)


def test_optimizer_improves_differentiable_objective_and_remains_leaf():
    optimizer = AnnealingOptimizer(torch.ones(2, 11), torch.zeros(2, 4, dtype=torch.long), 8,
                                   AnnealingConfig(switch_probability=0, preserve_source_graph=False), seed=5)
    objective = lambda parameters, indices: parameters.square().sum(dim=1)
    start = objective(optimizer.parameters, optimizer.contact_indices).detach()
    for _ in range(10):
        result = optimizer.step(objective)
        assert optimizer.parameters.is_leaf
        assert result["accepted"].all()
    assert (result["energy"] < start).all()


def test_optimizer_rolls_back_nonfinite_proposal():
    optimizer = AnnealingOptimizer(torch.ones(2, 11), torch.zeros(2, 2, dtype=torch.long), 4)
    previous = optimizer.parameters.detach().clone()
    calls = []

    def objective(parameters, indices):
        calls.append(None)
        return parameters.square().sum(dim=1) * (float("nan") if len(calls) == 2 else 1)

    with pytest.raises(ValueError, match="finite"):
        optimizer.step(objective)
    torch.testing.assert_close(optimizer.parameters, previous)
    assert optimizer.parameters.is_leaf
