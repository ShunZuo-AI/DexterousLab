"""Standalone Shadow embodiment using the checked-out official PhysX asset."""

import isaaclab.envs.mdp as mdp
from isaaclab.managers import ObservationGroupCfg, ObservationTermCfg
from isaaclab.utils.configclass import configclass
from isaaclab_assets.robots.shadow_hand import (
    FINGERTIP_NAMES, JOINT_NAMES, SHADOW_HAND_PHYSX_CFG, TENDON_NAMES, TENDON_POSITION_LIMITS,
)
from isaaclab_arena.assets.register import register_asset
from isaaclab_arena.embodiments.embodiment_base import EmbodimentBase


@configclass
class ShadowSceneCfg:
    robot = SHADOW_HAND_PHYSX_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")


@configclass
class ShadowActionsCfg:
    joints = mdp.JointPositionActionCfg(
        asset_name="robot", joint_names=JOINT_NAMES, scale=0.1, use_default_offset=True,
    )
    tendons = mdp.FixedTendonPositionActionCfg(
        asset_name="robot", tendon_names=TENDON_NAMES, scale=0.1, offset=0.0,
        clip={".*": TENDON_POSITION_LIMITS},
    )


@configclass
class ShadowProprioCfg(ObservationGroupCfg):
    joint_pos = ObservationTermCfg(func=mdp.joint_pos_rel)
    joint_vel = ObservationTermCfg(func=mdp.joint_vel_rel)

    def __post_init__(self):
        self.concatenate_terms = True
        self.enable_corruption = False


@configclass
class ShadowObservationsCfg:
    proprio = ShadowProprioCfg()


@register_asset
class ShadowEmbodiment(EmbodimentBase):
    registry_name = "dexlab_shadow"

    def __init__(self, enable_cameras=False):
        if enable_cameras:
            raise ValueError("Shadow cameras are not implemented")
        super().__init__(enable_cameras=False)
        self.scene_config = ShadowSceneCfg()
        self.action_config = ShadowActionsCfg()
        self.observation_config = ShadowObservationsCfg()

    def get_ee_frame_name(self, arm_mode=None):
        return "rh_palm"

    def get_command_body_name(self):
        return "rh_palm"


def validate_shadow_coordinates(config):
    if config.joint_names != JOINT_NAMES or config.tendon_names != TENDON_NAMES:
        raise ValueError("Shadow control coordinates differ from this Isaac Lab checkout")
    if config.fingertip_names != FINGERTIP_NAMES:
        raise ValueError("Shadow fingertip mapping differs from this Isaac Lab checkout")


def create_hand(configuration, asset_registry):
    validate_shadow_coordinates(configuration)
    return asset_registry.get_asset_by_name(configuration.registry_name)(enable_cameras=False)
