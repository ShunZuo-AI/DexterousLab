"""Physics validation contract; a passive rollout is not a validator."""

from abc import ABC, abstractmethod

from dexterous_lab.grasp_synthesis.candidate import GraspCandidate


class GraspValidator(ABC):
    @abstractmethod
    def validate(self, candidate: GraspCandidate) -> GraspCandidate:
        """Return a measured result after collision and grasp-stability testing."""
        raise NotImplementedError
