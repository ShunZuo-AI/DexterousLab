"""Serializable grasp candidates with explicit frames and unknown outcomes."""

from dataclasses import asdict, dataclass, field
from math import isfinite

from dexterous_lab.config import finite_vector, unit_quaternion


def pose_xyzw(value):
    result = finite_vector(value, 7, "pose [x,y,z,qx,qy,qz,qw]")
    unit_quaternion(result[3:])
    return result


@dataclass(frozen=True)
class GraspCandidate:
    object_id: str
    hand_id: str
    hand_root_pose: tuple
    joint_positions: dict[str, float]
    object_pose: tuple
    seed: int
    algorithm: str
    asset_version: str
    contact_points: tuple | None = None
    collision: bool | None = None
    stability: float | None = None
    success: bool | None = None
    frame: str = "W"
    hand_root_frame: str = "palm"
    quaternion_order: str = "xyzw"
    length_unit: str = "m"
    joint_unit: str = "rad"
    tendon_positions: dict[str, float] = field(default_factory=dict)
    schema_version: str = "1.0"

    def __post_init__(self):
        for name in ("object_id", "hand_id", "algorithm", "asset_version", "hand_root_frame"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a nonempty string")
        if self.frame != "W" or self.quaternion_order != "xyzw" or self.length_unit != "m" or self.joint_unit != "rad":
            raise ValueError("Schema 1.0 requires world frame W, xyzw, metres and radians")
        if self.schema_version != "1.0":
            raise ValueError("Unsupported grasp schema version")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        object.__setattr__(self, "hand_root_pose", pose_xyzw(self.hand_root_pose))
        object.__setattr__(self, "object_pose", pose_xyzw(self.object_pose))
        for name in ("joint_positions", "tendon_positions"):
            mapping = getattr(self, name)
            if not isinstance(mapping, dict) or (name == "joint_positions" and not mapping):
                raise ValueError(f"{name} must be a name-to-radians mapping")
            if any(not isinstance(key, str) or not key or not isfinite(value) for key, value in mapping.items()):
                raise ValueError(f"Invalid {name}")
            object.__setattr__(self, name, dict(mapping))
        if self.contact_points is not None:
            points = tuple(finite_vector(point, 3, "contact point in W") for point in self.contact_points)
            object.__setattr__(self, "contact_points", points)
        for name in ("collision", "success"):
            if getattr(self, name) is not None and type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be bool or None")
        if self.stability is not None and (not isfinite(self.stability) or not 0 <= self.stability <= 1):
            raise ValueError("stability must be None or a finite score in [0,1]")
        if self.success is True and (self.collision is not False or self.stability is None):
            raise ValueError("Successful validation requires a measured stability score and collision=False")

    def to_dict(self):
        return asdict(self)
