"""Algorithm contract; paper implementations are not bundled."""

from abc import ABC, abstractmethod
from collections.abc import Iterable

from dexterous_lab.grasp_synthesis.candidate import GraspCandidate


class GraspGenerator(ABC):
    @abstractmethod
    def generate(self, *, object_id: str, hand_id: str, seed: int) -> Iterable[GraspCandidate]:
        """Generate candidates; all unevaluated physical outcomes must remain unknown."""
        raise NotImplementedError
