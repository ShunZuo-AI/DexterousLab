"""Assemble a DexterousLab tabletop using public Arena components."""

from dataclasses import dataclass, field

from isaaclab_arena.assets.register import register_environment
from isaaclab_arena.environments.arena_environment_factory import ArenaEnvironmentCfg, ArenaEnvironmentFactory
from isaaclab_arena.environments.isaaclab_arena_environment import IsaacLabArenaEnvironment
from isaaclab_arena.scene.scene import Scene
from isaaclab_arena.utils.pose import Pose

from dexterous_lab.assets import primitives
from dexterous_lab.config import ObjectConfig, RobotConfig, SceneConfig, TaskConfig, checked_dataclass
from dexterous_lab.tasks.lift import make_lift_task
from dexterous_lab.integrations.isaaclab.observations import StateObservationsCfg
from dexterous_lab.objects.registry import ObjectRegistry
from dexterous_lab.robots.registry import HandRegistry


@dataclass
class TabletopEnvironmentCfg(ArenaEnvironmentCfg):
    specification: dict = field(default_factory=dict)


@register_environment
class DexterousLabTabletopEnvironment(ArenaEnvironmentFactory[TabletopEnvironmentCfg]):
    name = "dexlab_tabletop"

    def build(self, cfg):
        specification = cfg.specification
        robot_cfg = checked_dataclass(RobotConfig, specification["robot"])
        object_cfg = checked_dataclass(ObjectConfig, specification["object"])
        scene_cfg = checked_dataclass(SceneConfig, specification["scene"])
        task_cfg = checked_dataclass(TaskConfig, specification["task"])
        if specification["backend"] != "physx":
            raise ValueError("DexterousLab tabletop is validated only on PhysX")
        embodiment = HandRegistry().create(robot_cfg, self.asset_registry)
        embodiment.observation_config = StateObservationsCfg()
        embodiment.set_initial_pose(Pose(robot_cfg.position_xyz, robot_cfg.rotation_xyzw))
        table = self.asset_registry.get_asset_by_name("dexlab_table")(config=scene_cfg)
        object_asset = ObjectRegistry().create(object_cfg, self.asset_registry)
        ground = self.asset_registry.get_asset_by_name("ground_plane")()
        light = self.asset_registry.get_asset_by_name("light")()
        light.set_intensity(scene_cfg.light_intensity)
        additional_assets = []
        names = {'object', 'table', 'robot', 'ground_plane', 'light'}
        for item in specification.get('additional_objects', []):
            name = item['name']
            if not name.isidentifier() or name in names:
                raise ValueError(f'Invalid or duplicate additional object name: {name}')
            names.add(name)
            configuration = checked_dataclass(ObjectConfig, item['config'])
            additional_assets.append(self.asset_registry.get_asset_by_name(configuration.registry_name)(
                config=configuration, name=name))

        def set_timing(env_cfg):
            from isaaclab.sensors import ContactSensorCfg
            from dexterous_lab.integrations.isaaclab.contact_paths import fingertip_filter_paths

            env_cfg.sim.dt = scene_cfg.dt
            env_cfg.decimation = scene_cfg.decimation
            env_cfg.sim.render_interval = scene_cfg.decimation
            env_cfg.scene.dexlab_object_contact = ContactSensorCfg(
                prim_path="{ENV_REGEX_NS}/Object",
                filter_prim_paths_expr=fingertip_filter_paths(env_cfg.scene.robot, robot_cfg.fingertip_names),
                track_contact_points=True,
                max_contact_data_count_per_prim=64,
            )
            return env_cfg

        return IsaacLabArenaEnvironment(
            name=self.name, scene=Scene(assets=[table, object_asset, ground, light, *additional_assets]), embodiment=embodiment,
            task=make_lift_task(object_asset, table, task_cfg), env_cfg_callback=set_timing,
        )


TabletopEnvironment = DexterousLabTabletopEnvironment
