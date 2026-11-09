"""State-only observations independent of official lift command generators."""

import isaaclab.envs.mdp as mdp
from isaaclab.managers import ObservationGroupCfg, ObservationTermCfg, SceneEntityCfg
from isaaclab.utils.configclass import configclass


@configclass
class StateGroupCfg(ObservationGroupCfg):
    joint_pos = ObservationTermCfg(func=mdp.joint_pos_rel)
    joint_vel = ObservationTermCfg(func=mdp.joint_vel_rel)
    object_pos = ObservationTermCfg(func=mdp.root_pos_w, params={"asset_cfg": SceneEntityCfg("object")})
    object_quat = ObservationTermCfg(func=mdp.root_quat_w, params={"asset_cfg": SceneEntityCfg("object")})

    def __post_init__(self):
        self.concatenate_terms = True
        self.enable_corruption = False


@configclass
class StateObservationsCfg:
    policy = StateGroupCfg()
