"""Discover hand configurations independently of articulation DOF or backend imports."""

from dexterous_lab.config import RobotConfig
from dexterous_lab.registry import ConfigurationRegistry


class HandRegistry(ConfigurationRegistry):
    category = "robots"
    config_type = RobotConfig

    def get(self, name, overrides=None):
        configuration = super().get(name, overrides)
        if configuration.hand_id != name:
            raise ValueError(f"Hand file {name} declares a different hand_id: {configuration.hand_id}")
        return configuration
