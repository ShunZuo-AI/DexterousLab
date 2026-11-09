"""Asset construction adapters selected by object configuration."""


def create_object(configuration, asset_registry):
    from dexterous_lab.assets import primitives

    if configuration.kind == "usd":
        import isaaclab.sim as sim_utils
        from isaaclab_arena.assets.object import Object
        from isaaclab_arena.assets.object_type import ObjectType
        from isaaclab_arena.utils.pose import Pose

        return Object(
            name="object", prim_path="{ENV_REGEX_NS}/Object", object_type=ObjectType.RIGID,
            usd_path=configuration.usd_path, scale=configuration.scale,
            initial_pose=Pose(configuration.position_xyz, configuration.rotation_xyzw),
            spawn_cfg_addon={
                "activate_contact_sensors": True,
                "mass_props": sim_utils.MassPropertiesCfg(mass=configuration.mass),
                "physics_material": sim_utils.RigidBodyMaterialCfg(
                    static_friction=configuration.friction, dynamic_friction=configuration.friction,
                ),
            },
        )
    return asset_registry.get_asset_by_name(configuration.registry_name)(config=configuration)
