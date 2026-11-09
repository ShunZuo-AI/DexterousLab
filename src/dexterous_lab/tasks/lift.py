"""Reuse Arena's fixed-goal lift task without claiming a grasp validator."""


def make_lift_task(object_asset, table, config):
    from isaaclab_arena.tasks.lift_object_task import LiftObjectTask

    return LiftObjectTask(
        lift_object=object_asset, background_scene=table,
        episode_length_s=config.episode_length_s,
        goal_position_delta_xyz=config.goal_delta_xyz,
        goal_position_tolerance=config.position_tolerance,
    )
