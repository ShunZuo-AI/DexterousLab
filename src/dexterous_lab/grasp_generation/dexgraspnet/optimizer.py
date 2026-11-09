"""Batched DexGraspNet-style proposal/acceptance algorithm over an explicit state.

Algorithm reference: PKU-EPIC/DexGraspNet bd1b13d,
grasp_generation/utils/optimizer.py:Annealing by Jialiang Zhang.
See the source and license analysis in docs/paper_reproductions.
"""

from dataclasses import dataclass
from math import isfinite

import torch


@dataclass(frozen=True)
class AnnealingConfig:
    switch_probability: float = 0.5
    initial_temperature: float = 18.0
    decay: float = 0.95
    temperature_period: int = 30
    step_size: float = 0.005
    step_period: int = 50
    current_gradient_weight: float = 0.98
    preserve_source_graph: bool = True

    def __post_init__(self):
        if type(self.preserve_source_graph) is not bool:
            raise ValueError("preserve_source_graph must be boolean")
        for name in ("switch_probability", "current_gradient_weight"):
            value = getattr(self, name)
            if not isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0,1]")
        if not isfinite(self.decay) or not 0 < self.decay <= 1:
            raise ValueError("decay must be in (0,1]")
        if any(not isfinite(value) or value <= 0 for value in (self.initial_temperature, self.step_size)):
            raise ValueError("Temperature and step size must be finite and positive")
        if any(type(value) is not int or value < 1 for value in (self.temperature_period, self.step_period)):
            raise ValueError("Annealing periods must be positive integers")


class AnnealingOptimizer:
    """Preserve original graph/gradient history, or explicitly opt into leaf proposals."""

    def __init__(self, parameters, contact_indices, contact_candidate_count, config=None, seed=42):
        if parameters.ndim != 2 or parameters.shape[0] == 0 or parameters.shape[1] < 9:
            raise ValueError("parameters must have shape [B,9+J]")
        if not parameters.is_floating_point() or not torch.isfinite(parameters).all().item():
            raise ValueError("parameters must be finite floating-point values")
        if type(contact_candidate_count) is not int or contact_candidate_count < 1:
            raise ValueError("contact_candidate_count must be positive")
        if (contact_indices.ndim != 2 or contact_indices.shape[0] != parameters.shape[0]
                or contact_indices.shape[1] == 0 or contact_indices.dtype != torch.long
                or contact_indices.device != parameters.device):
            raise ValueError("contact_indices must be a same-device long tensor [B,C]")
        if ((contact_indices < 0) | (contact_indices >= contact_candidate_count)).any().item():
            raise ValueError("Contact index is out of range")
        self.parameters = parameters.detach().clone().requires_grad_(True)
        self.contact_indices = contact_indices.detach().clone()
        self.candidate_count = contact_candidate_count
        self.config = config or AnnealingConfig()
        self.second_moment = torch.zeros(parameters.shape[1], dtype=parameters.dtype, device=parameters.device)
        self.iteration = 0
        self._energy = None
        self.generator = torch.Generator(device=parameters.device).manual_seed(seed)

    def _evaluate(self, objective):
        if self.parameters.grad is not None:
            self.parameters.grad.zero_()
        energy = objective(self.parameters, self.contact_indices)
        if energy.shape != (self.parameters.shape[0],) or not torch.isfinite(energy).all().item():
            raise ValueError("Objective must return one finite energy per candidate")
        energy.sum().backward(retain_graph=self.config.preserve_source_graph)
        if self.parameters.grad is None or not torch.isfinite(self.parameters.grad).all().item():
            raise ValueError("Objective must provide finite parameter gradients")
        return energy.detach(), self.parameters.grad

    def step(self, objective):
        """Propose continuous/discrete updates and atomically accept each candidate.

        Args:
            objective: Callable(parameters, indices) -> energy[B]. It must rebuild
                differentiable geometry from its arguments and have no lasting side effects.

        Returns:
            Detached energy[B], acceptance mask[B], step size and temperature.
            Source mode retains non-leaf proposals and legacy gradient accumulation.
            Leaf mode explicitly changes that behavior. No grasp-success decision.
        """
        if self._energy is None:
            old_energy, old_gradient = self._evaluate(objective)
        else:
            old_energy, old_gradient = self._energy, self.parameters.grad
        config = self.config
        self.second_moment = (config.current_gradient_weight * old_gradient.square().mean(dim=0)
                              + (1 - config.current_gradient_weight) * self.second_moment)
        step_size = config.step_size * config.decay ** (self.iteration // config.step_period)
        previous_parameters = self.parameters if config.preserve_source_graph else self.parameters.detach().clone()
        previous_indices = self.contact_indices.clone()
        proposed = previous_parameters - step_size * old_gradient / (self.second_moment.sqrt() + 1e-6)
        switch = torch.rand(self.contact_indices.shape, device=self.parameters.device, generator=self.generator) < config.switch_probability
        proposal_indices = previous_indices.clone()
        proposal_indices[switch] = torch.randint(
            self.candidate_count, (int(switch.sum().item()),), device=self.parameters.device, generator=self.generator,
        )
        self.parameters = proposed if config.preserve_source_graph else proposed.detach().requires_grad_(True)
        self.parameters.retain_grad()
        self.contact_indices = proposal_indices
        self.iteration += 1
        try:
            new_energy, new_gradient = self._evaluate(objective)
        except Exception:
            self.parameters = previous_parameters.requires_grad_(True)
            self.parameters.grad = old_gradient
            self.contact_indices = previous_indices
            raise
        temperature = config.initial_temperature * config.decay ** (self.iteration // config.temperature_period)
        uniforms = torch.rand(old_energy.shape, device=self.parameters.device, generator=self.generator)
        acceptance = uniforms < torch.exp((old_energy - new_energy) / temperature)
        with torch.no_grad():
            self.parameters[~acceptance] = previous_parameters[~acceptance]
            self.contact_indices[~acceptance] = previous_indices[~acceptance]
        self.parameters.grad = torch.where(acceptance[:, None], new_gradient, old_gradient)
        energy = torch.where(acceptance, new_energy, old_energy)
        self._energy = energy.detach().clone()
        return {"energy": energy, "accepted": acceptance, "step_size": step_size, "temperature": temperature}
