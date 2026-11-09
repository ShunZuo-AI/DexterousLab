"""Resolve individual contact filter bodies from the actual robot USD hierarchy."""


def fingertip_filter_paths(robot_cfg, fingertip_names):
    from isaaclab_arena.utils.usd.helpers import open_stage
    from pxr import Usd, UsdPhysics

    matches = {name: [] for name in fingertip_names}
    with open_stage(robot_cfg.spawn.usd_path) as stage:
        root = stage.GetDefaultPrim()
        if not root:
            raise ValueError("Robot USD has no default prim")
        for prim in Usd.PrimRange(root, Usd.TraverseInstanceProxies()):
            if prim.GetName() in matches and prim.HasAPI(UsdPhysics.RigidBodyAPI):
                relative = prim.GetPath().MakeRelativePath(root.GetPath())
                matches[prim.GetName()].append(robot_cfg.prim_path + "/" + str(relative))
    result = []
    for name in fingertip_names:
        if len(matches[name]) != 1:
            raise ValueError(f"Expected one rigid fingertip {name!r}, found {matches[name]}")
        result.append(matches[name][0])
    return result
