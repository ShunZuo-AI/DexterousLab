"""Read and validate research configurations without loading the simulator."""

from dataclasses import asdict, dataclass, fields
from math import isclose, isfinite, sqrt
from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).absolute().parents[2]
CONFIG_ROOT = PROJECT_ROOT / "configs"


def finite_vector(values, length, label):
    result = tuple(float(value) for value in values)
    if len(result) != length or not all(isfinite(value) for value in result):
        raise ValueError(f"{label} must contain {length} finite numbers")
    return result


def unit_quaternion(values):
    result = finite_vector(values, 4, "rotation_xyzw")
    if not isclose(sqrt(sum(value * value for value in result)), 1.0, abs_tol=1e-5):
        raise ValueError("rotation_xyzw must be a unit quaternion in (x, y, z, w) order")
    return result


def read_toml(path):
    with Path(path).open("rb") as stream:
        return tomllib.load(stream)


def named_config(category, name):
    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError(f"Invalid {category} configuration name: {name!r}")
    path = CONFIG_ROOT / category / f"{name}.toml"
    if not path.is_file():
        raise ValueError(f"Unsupported {category}: {name}; no configuration at {path}")
    return read_toml(path)


def checked_dataclass(cls, mapping):
    unknown = set(mapping) - {field.name for field in fields(cls)}
    if unknown:
        raise ValueError(f"Unsupported {cls.__name__} fields: {sorted(unknown)}")
    return cls(**mapping)


@dataclass
class ObjectConfig:
    registry_name: str = "dexlab_cube"
    factory: str = "dexterous_lab.objects.factories:create_object"
    kind: str = "cube"
    position_xyz: tuple = (-0.55, 0.0, 0.285)
    rotation_xyzw: tuple = (0.0, 0.0, 0.0, 1.0)
    scale: tuple = (1.0, 1.0, 1.0)
    size: tuple = (0.05, 0.05, 0.05)
    mass: float = 0.1
    friction: float = 0.7
    usd_path: str | None = None
    asset_version: str = "procedural-v1"

    def __post_init__(self):
        if self.kind not in ("cube", "sphere", "cylinder", "usd"):
            raise ValueError(f"Object kind {self.kind!r} is not implemented; cup/URDF/mesh import is reserved")
        self.position_xyz = finite_vector(self.position_xyz, 3, "position_xyz")
        self.rotation_xyzw = unit_quaternion(self.rotation_xyzw)
        self.scale = finite_vector(self.scale, 3, "scale")
        self.size = finite_vector(self.size, 3, "size")
        if min(*self.scale, *self.size) <= 0 or not isfinite(self.mass) or self.mass <= 0:
            raise ValueError("Object size, scale and mass must be positive")
        if not isfinite(self.friction) or self.friction < 0:
            raise ValueError("Object friction must be finite and nonnegative")
        if self.kind == "sphere" and (len(set(self.scale)) != 1 or len(set(self.size)) != 1):
            raise ValueError("sphere requires equal size and scale on all axes")
        if self.kind == "cylinder" and (self.size[0] != self.size[1] or self.scale[0] != self.scale[1]):
            raise ValueError("cylinder requires equal x/y size and scale")
        if self.kind == "usd" and (not self.usd_path or not Path(self.usd_path).is_file()):
            raise ValueError("External USD requires an existing local usd_path; no automatic conversion")


@dataclass
class RobotConfig:
    hand_id: str
    registry_name: str
    requires_arm: bool
    joint_names: list[str]
    fingertip_names: list[str]
    action_dim: int
    tendon_names: list[str]
    factory: str = "dexterous_lab.robots.allegro:create_hand"
    palm_frame: str = "palm_link"
    position_xyz: tuple = (0.0, 0.0, 0.0)
    rotation_xyzw: tuple = (0.0, 0.0, 0.0, 1.0)

    def __post_init__(self):
        if not self.hand_id or not self.registry_name or not self.palm_frame:
            raise ValueError("hand_id, registry_name and palm_frame must be nonempty")
        self.position_xyz = finite_vector(self.position_xyz, 3, "robot position_xyz")
        self.rotation_xyzw = unit_quaternion(self.rotation_xyzw)
        if self.action_dim != len(self.joint_names) + len(self.tendon_names):
            raise ValueError("action_dim must equal direct joint coordinates plus tendon coordinates")
        if len(set(self.joint_names + self.tendon_names)) != self.action_dim:
            raise ValueError("Robot control coordinate names must be unique")


@dataclass
class SceneConfig:
    name: str = "tabletop"
    table_position_xyz: tuple = (-0.55, 0.0, 0.235)
    table_size: tuple = (0.8, 1.0, 0.04)
    light_intensity: float = 2000.0
    dt: float = 1 / 120
    decimation: int = 4

    def __post_init__(self):
        self.table_position_xyz = finite_vector(self.table_position_xyz, 3, "table position")
        self.table_size = finite_vector(self.table_size, 3, "table size")
        if min(self.table_size) <= 0 or not isfinite(self.dt) or self.dt <= 0:
            raise ValueError("Table dimensions and dt must be positive")
        if self.decimation < 1 or not isfinite(self.light_intensity) or self.light_intensity < 0:
            raise ValueError("Invalid control decimation or light intensity")


@dataclass
class TaskConfig:
    name: str = "lift"
    episode_length_s: float = 5.0
    goal_delta_xyz: tuple = (0.0, 0.0, 0.1)
    position_tolerance: float = 0.02

    def __post_init__(self):
        if self.name != "lift":
            raise ValueError(f"Task {self.name!r} is not implemented")
        self.goal_delta_xyz = finite_vector(self.goal_delta_xyz, 3, "goal_delta_xyz")
        if not isfinite(self.episode_length_s) or self.episode_length_s <= 0:
            raise ValueError("episode_length_s must be positive")
        if not isfinite(self.position_tolerance) or self.position_tolerance <= 0:
            raise ValueError("position_tolerance must be positive")


def load_scene(experiment=None, hand=None, object_id=None, scene=None, backend=None):
    from dexterous_lab.objects.registry import ObjectRegistry
    from dexterous_lab.robots.registry import HandRegistry

    path = Path(experiment) if experiment else CONFIG_ROOT / "experiments" / "tabletop.toml"
    data = read_toml(path)
    unknown = set(data) - {"hand", "object", "scene", "task", "backend", "object_overrides"}
    if unknown:
        raise ValueError(f"Unknown experiment fields: {sorted(unknown)}")
    hand = hand or data["hand"]
    object_id = object_id or data["object"]
    scene = scene or data["scene"]
    backend = backend or data["backend"]
    if backend != "physx":
        raise ValueError("Custom scenes currently support only physx; newton is not validated")
    return {
        "hand_id": hand,
        "object_id": object_id,
        "backend": backend,
        "robot": asdict(HandRegistry().get(hand)),
        "object": asdict(ObjectRegistry().get(object_id, data.get("object_overrides"))),
        "scene": asdict(checked_dataclass(SceneConfig, named_config("scenes", scene))),
        "task": asdict(checked_dataclass(TaskConfig, named_config("tasks", data["task"]))),
    }
