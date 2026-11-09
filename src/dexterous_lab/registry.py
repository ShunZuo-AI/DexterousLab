"""Configuration registries that stay usable without starting Isaac Sim."""

from importlib import import_module
from pathlib import Path

from dexterous_lab.config import CONFIG_ROOT, checked_dataclass, read_toml


def import_factory(path):
    module_name, separator, attribute = path.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError(f"Expected factory module:callable, got {path!r}")
    factory = getattr(import_module(module_name), attribute)
    if not callable(factory):
        raise ValueError(f"Factory {path!r} is not callable")
    return factory


class ConfigurationRegistry:
    category = None
    config_type = None

    def __init__(self, config_root=CONFIG_ROOT):
        self.directory = Path(config_root) / self.category

    def names(self):
        return sorted(path.stem for path in self.directory.glob("*.toml"))

    def get(self, name, overrides=None):
        if not name or Path(name).name != name or name in (".", ".."):
            raise ValueError(f"Invalid {self.category} name: {name!r}")
        path = self.directory / f"{name}.toml"
        if not path.is_file():
            raise ValueError(f"Unsupported {self.category}: {name}; available: {self.names()}")
        values = read_toml(path)
        values.update(overrides or {})
        return checked_dataclass(self.config_type, values)

    def create(self, configuration, asset_registry):
        """Instantiate a configured component after SimulationApp startup."""
        return import_factory(configuration.factory)(configuration, asset_registry)
