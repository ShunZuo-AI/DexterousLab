"""Verify loaded USD and actual PhysX properties instead of trusting configuration."""

from dexterous_lab.evaluation.smoke import check_physics_values
from dexterous_lab.integrations.isaaclab.state import as_torch


def validate_loaded_scene(env, specification):
    from isaaclab.sim.utils import get_current_stage
    from pxr import Usd, UsdGeom, UsdPhysics

    base = env.unwrapped
    robot = base.scene["robot"]
    object_asset = base.scene["object"]
    if not robot.is_initialized or not object_asset.is_initialized:
        raise RuntimeError("Robot or object failed to initialize")
    stage = get_current_stage()
    object_prim = stage.GetPrimAtPath("/World/envs/env_0/Object")
    robot_prim = stage.GetPrimAtPath("/World/envs/env_0/Robot")
    if not object_prim.IsValid() or not robot_prim.IsValid():
        raise RuntimeError("Robot or object USD prim is missing")
    body = UsdPhysics.RigidBodyAPI(object_prim)
    if not body or not body.GetRigidBodyEnabledAttr().Get() or body.GetKinematicEnabledAttr().Get():
        raise RuntimeError("Manipulation object must be an enabled dynamic rigid body")
    collision_paths = []
    for prim in Usd.PrimRange(object_prim, Usd.TraverseInstanceProxies()):
        collision = UsdPhysics.CollisionAPI(prim)
        if collision and collision.GetCollisionEnabledAttr().Get():
            collision_paths.append(str(prim.GetPath()))
    if not collision_paths:
        raise RuntimeError("Object has no enabled collision shapes")
    masses = as_torch(object_asset.root_view.get_masses()).flatten().cpu().tolist()
    material_tensor = as_torch(object_asset.root_view.get_material_properties())
    materials = material_tensor.reshape(-1, 3).cpu().tolist()
    config = specification["object"]
    check_physics_values(masses, materials, config["mass"], config["friction"])
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render", "proxy"])
    extents = list(bounds.ComputeUntransformedBound(object_prim).ComputeAlignedRange().GetSize())
    if config["kind"] != "usd":
        from math import isclose

        expected = [size * scale for size, scale in zip(config["size"], config["scale"], strict=True)]
        if any(not isclose(actual, target, rel_tol=1e-4, abs_tol=1e-6) for actual, target in zip(extents, expected, strict=True)):
            raise RuntimeError(f"Spawned object bounds {extents} differ from configured dimensions {expected}")
    inertia = as_torch(object_asset.root_view.get_inertias())
    if not inertia.isfinite().all().item() or not (inertia.reshape(-1, 3, 3).diagonal(dim1=-2, dim2=-1) > 0).all().item():
        raise RuntimeError("Object inertia must be finite and positive on its diagonal")
    return {
        "robot_loaded": True, "object_loaded": True, "dynamic_rigid_body": True,
        "collision_paths": collision_paths, "backend_masses_kg": masses,
        "backend_materials_static_dynamic_restitution": materials,
        "backend_inertias_kg_m2": inertia.cpu().tolist(),
        "spawned_local_extents_m": extents,
        "object_kind": config["kind"], "asset_version": config["asset_version"],
        "contact_filter_paths": base.cfg.scene.dexlab_object_contact.filter_prim_paths_expr,
    }
