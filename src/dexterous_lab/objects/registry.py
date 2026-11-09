"""Discover named object assets and their construction adapters."""

from dexterous_lab.config import ObjectConfig
from dexterous_lab.registry import ConfigurationRegistry


class ObjectRegistry(ConfigurationRegistry):
    category = "objects"
    config_type = ObjectConfig
