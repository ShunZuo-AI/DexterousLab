"""Registered procedural assets; import only inside SimulationApp."""

import isaaclab.sim as sim_utils
from isaaclab_arena.assets.object import Object
from isaaclab_arena.assets.object_type import ObjectType
from isaaclab_arena.assets.register import register_asset
from isaaclab_arena.utils.pose import Pose

from dexterous_lab.config import ObjectConfig
from dexterous_lab.objects.geometry import scaled_size


class PrimitiveObject(Object):
    tags = ["object", "procedural", "dexlab"]

    def __init__(self, config=None, name="object"):
        config = config or ObjectConfig(kind=self.kind)
        dimensions = scaled_size(config)
        common = dict(
            activate_contact_sensors=True,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False),
            collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.002),
            mass_props=sim_utils.MassPropertiesCfg(mass=config.mass),
            physics_material=sim_utils.RigidBodyMaterialCfg(
                static_friction=config.friction, dynamic_friction=config.friction
            ),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.2, 0.5, 0.8)),
        )
        if config.kind == "cube":
            spawner = sim_utils.CuboidCfg(size=dimensions, **common)
        elif config.kind == "sphere":
            spawner = sim_utils.SphereCfg(radius=dimensions[0] / 2, **common)
        elif config.kind == "cylinder":
            spawner = sim_utils.CylinderCfg(radius=dimensions[0] / 2, height=dimensions[2], **common)
        else:
            raise ValueError(f"Procedural asset cannot spawn {config.kind}")
        super().__init__(
            name=name, prim_path="{ENV_REGEX_NS}/" + ("Object" if name == "object" else name), object_type=ObjectType.RIGID,
            spawner_cfg=spawner,
            initial_pose=Pose(position_xyz=config.position_xyz, rotation_xyzw=config.rotation_xyzw),
        )


@register_asset
class Cube(PrimitiveObject):
    registry_name = "dexlab_cube"
    kind = "cube"


@register_asset
class Sphere(PrimitiveObject):
    registry_name = "dexlab_sphere"
    kind = "sphere"


@register_asset
class Cylinder(PrimitiveObject):
    registry_name = "dexlab_cylinder"
    kind = "cylinder"


@register_asset
class Table(Object):
    registry_name = "dexlab_table"
    tags = ["background", "procedural", "dexlab"]
    object_min_z = 0.0

    def __init__(self, config):
        spawner = sim_utils.CuboidCfg(
            size=config.table_size,
            rigid_props=sim_utils.RigidBodyPropertiesCfg(kinematic_enabled=True),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.45, 0.32, 0.2)),
        )
        super().__init__(
            name="table", object_type=ObjectType.RIGID, spawner_cfg=spawner,
            initial_pose=Pose(position_xyz=config.table_position_xyz),
        )
