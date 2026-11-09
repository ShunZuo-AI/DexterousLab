"""Reuse the official arm-mounted Allegro without its task-specific observations."""


def create_hand(configuration, asset_registry):
    embodiment = asset_registry.get_asset_by_name(configuration.registry_name)(enable_cameras=False)
    embodiment.event_config.reset_robot_joints.params["position_range"] = [0.0, 0.0]
    return embodiment
