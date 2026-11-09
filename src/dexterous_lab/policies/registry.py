"""Named policy factories with a uniform reset/predict observation interface.

Inspired by DexGarmentLab SADP.py/RobotRunner.get_action separation.
This module contains no HALO, GAM, DP or DP3 implementation.
"""

import numpy as np


class HoldPolicy:
    def __init__(self, target_action):
        self.target = np.asarray(target_action, dtype=np.float32)
        if self.target.ndim != 1 or not np.isfinite(self.target).all():
            raise ValueError('Policy target must be a finite action vector')

    def reset(self):
        return None

    def predict(self, observation):
        return self.target.copy()


class PolicyRegistry:
    def __init__(self):
        self.factories = {'hold': HoldPolicy}

    def register(self, name, factory):
        if not name or name in self.factories or not callable(factory):
            raise ValueError('Policy name must be new and factory must be callable')
        self.factories[name] = factory

    def load(self, name, **configuration):
        if name not in self.factories:
            raise ValueError(f'Policy {name!r} is not implemented; available: {sorted(self.factories)}')
        return self.factories[name](**configuration)
