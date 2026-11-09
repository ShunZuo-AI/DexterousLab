"""Actual Isaac Lab conversion and bounded asset-only PhysX smoke verification."""

import json
import math
from pathlib import Path
import sys
import time

from dexterous_lab.assets.catalog import save_json


def convert(request):
    from isaaclab.sim.converters import UrdfConverter, UrdfConverterCfg
    from dexterous_lab.assets.checks import prepare_import_urdf

    record = request['asset']
    source = Path(record['local_raw_path'])
    raw_root = source
    while raw_root.name != 'raw':
        if raw_root.parent == raw_root:
            raise ValueError('Source is outside an asset raw directory')
        raw_root = raw_root.parent
    prepared = Path(request['run_dir']) / 'import.urdf'
    mesh_mapping = prepare_import_urdf(source, raw_root, prepared, record.get('mesh_aliases'))
    merge_fixed = record.get('conversion_settings', {}).get('merge_fixed_joints', False)

    config = UrdfConverterCfg(
        asset_path=str(prepared), usd_dir=request['processed_directory'],
        usd_file_name="model.usd", fix_base=True, merge_fixed_joints=merge_fixed, make_instanceable=False,
        joint_drive=UrdfConverterCfg.JointDriveCfg(gains=UrdfConverterCfg.JointDriveCfg.PDGainsCfg(stiffness=3.0, damping=0.1)),
        force_usd_conversion=True,
    )
    result = UrdfConverter(config)
    if not Path(result.usd_path).is_file():
        raise RuntimeError("URDF importer did not produce USD")
    return {"completed": True, "usd_path": result.usd_path, "mesh_mapping": mesh_mapping,
            "adaptation": "Mesh references expanded to verified absolute raw paths in a separate import URDF; original untouched",
            "parameters": {"fix_base": True, "merge_fixed_joints": merge_fixed, "collision_type": config.collision_type,
                           "joint_stiffness": 3.0, "joint_damping": 0.1},
            "scope": "Converted with Isaac Lab URDF importer; simulation not implied"}


def validate(request):
    import importlib
    import torch
    import warp as wp
    from pxr import Usd, UsdGeom, UsdPhysics
    import isaaclab.sim as sim_utils
    from isaaclab.actuators import ImplicitActuatorCfg
    from isaaclab.assets import Articulation, ArticulationCfg
    from isaaclab_physx.physics import PhysxCfg
    from isaaclab_physx.sim.schemas import PhysxArticulationCfg

    record = request['asset']
    settings = record.get('validation_settings', {})
    preview = request['action'] == 'preview'
    dt = settings.get('dt', 1 / 120)
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(device="cuda:0", dt=dt, physics=PhysxCfg()))
    ground = sim_utils.GroundPlaneCfg()
    ground.func("/World/ground", ground)
    if preview:
        light = sim_utils.DomeLightCfg(intensity=1800.0)
        light.func('/World/Light', light)
    if record.get('official_usd_url'):
        module_name, symbol = record['isaaclab_asset_path'].split(':')
        config = getattr(importlib.import_module(module_name), symbol).replace(prim_path="/World/Hand")
    else:
        source_stage = Usd.Stage.Open(record['isaaclab_asset_path'])
        initial_joints = {}
        for prim in source_stage.Traverse():
            if prim.IsA(UsdPhysics.RevoluteJoint):
                joint = UsdPhysics.RevoluteJoint(prim)
                lower = math.radians(joint.GetLowerLimitAttr().Get())
                upper = math.radians(joint.GetUpperLimitAttr().Get())
                initial_joints[prim.GetName()] = min(max(0.0, lower), upper)
        articulation_props = [PhysxArticulationCfg(**settings['articulation'])] if settings.get('articulation') else None
        config = ArticulationCfg(
            prim_path="/World/Hand", spawn=sim_utils.UsdFileCfg(usd_path=record['isaaclab_asset_path'], fix_root_link=True,
                                                            articulation_props=articulation_props),
            init_state=ArticulationCfg.InitialStateCfg(pos=(0, 0, 0.5), joint_pos=initial_joints),
            actuators={"all_joints": ImplicitActuatorCfg(joint_names_expr=[".*"], stiffness=settings.get('stiffness', 3.0),
                                                       damping=settings.get('damping', 0.1))},
        )
    robot = Articulation(config)
    sim.reset()
    if not robot.is_initialized or not robot.joint_names:
        raise RuntimeError("Articulation was not initialized with joints")
    positions = robot.data.default_joint_pos.clone()
    robot.write_joint_state_to_sim(positions, torch.zeros_like(positions))
    robot.set_joint_position_target(positions)
    masses = wp.to_torch(robot.root_view.get_masses())
    if not torch.isfinite(masses).all() or (masses <= 0).any():
        raise RuntimeError("Invalid loaded link masses")
    inertias = wp.to_torch(robot.root_view.get_inertias()).reshape(-1, 3, 3)
    if not torch.isfinite(inertias).all() or (torch.linalg.eigvalsh(inertias) <= 0).any():
        raise RuntimeError("Invalid loaded link inertia tensors")
    stage = sim_utils.get_current_stage()
    collisions, hinges = [], []
    for prim in Usd.PrimRange(stage.GetPrimAtPath('/World/Hand'), Usd.TraverseInstanceProxies()):
        api = UsdPhysics.CollisionAPI(prim)
        if api and api.GetCollisionEnabledAttr().Get():
            collisions.append(str(prim.GetPath()))
        if prim.IsA(UsdPhysics.RevoluteJoint):
            hinges.append(str(prim.GetPath()))
    if not collisions:
        raise RuntimeError("No enabled collision geometry")
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]).ComputeWorldBound(
        stage.GetPrimAtPath('/World/Hand')).ComputeAlignedRange()
    extents = list(bounds.GetSize())
    if not all(math.isfinite(value) and value > 0 for value in extents) or max(extents) > 2:
        raise RuntimeError(f"Unexpected hand metric dimensions: {extents}")
    if preview:
        center = list(bounds.GetMidpoint())
        distance = max(max(extents) * 1.8, 0.3)
        sim.set_camera_view(eye=(center[0] + distance, center[1] - distance, center[2] + distance * 0.65),
                            target=tuple(center))
        sim.render()
        save_json(Path(request['run_dir']) / 'ready.json', {
            'asset_id': record['asset_id'], 'display_ready': True, 'joint_names': list(robot.joint_names),
            'duration_seconds': request['seconds'], 'scope': 'Desktop asset inspection; fixed-base joint position hold'})
        print('DEXLAB_PREVIEW_READY ' + record['asset_id'], flush=True)
        start = time.monotonic()
        steps = 0
        while time.monotonic() - start < request['seconds'] and sim.is_running():
            tick = time.monotonic()
            robot.write_data_to_sim()
            sim.step(render=True)
            robot.update(sim.get_physics_dt())
            if not torch.isfinite(robot.data.joint_pos).all():
                raise RuntimeError('Nonfinite joint state during preview')
            steps += 1
            time.sleep(max(0, dt - (time.monotonic() - tick)))
        return {'completed': True, 'preview': True, 'steps_completed': steps, 'grasp_success': None}
    for step in range(1, request['steps'] + 1):
        robot.write_data_to_sim()
        sim.step(render=False)
        robot.update(sim.get_physics_dt())
        if not torch.isfinite(robot.data.joint_pos).all() or not torch.isfinite(robot.data.joint_vel).all():
            raise RuntimeError("Nonfinite joint state during asset validation")
        if not torch.isfinite(robot.data.root_pose_w).all():
            raise RuntimeError("Nonfinite root pose")
        if step == 1 or step % 20 == 0:
            print(f"DEXLAB_ASSET_STEP {step}/{request['steps']}", flush=True)
    return {"completed": True, "steps_completed": request['steps'], "device": "cuda:0", "physics": "PhysX",
            "physics_dt": dt, "validation_settings": settings,
            "joint_names": list(robot.joint_names), "body_names": list(robot.body_names),
            "joint_positions": robot.data.joint_pos.cpu().tolist(), "joint_velocities": robot.data.joint_vel.cpu().tolist(),
            "backend_link_masses_kg": masses.cpu().tolist(), "collision_paths": collisions,
            "backend_link_inertias_kg_m2": inertias.cpu().tolist(), "world_bounds_extents_m": extents,
            "initial_joint_positions": positions.cpu().tolist(), "root_pose_w": robot.data.root_pose_w.cpu().tolist(),
            "revolute_joint_paths": hinges, "source_usd": config.spawn.usd_path,
            "grasp_success": None, "scope": "Asset-only fixed-base position hold, not dexterous control/grasp validation"}


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    sys.argv = [sys.argv[0]]
    from isaaclab_arena.cli.isaaclab_arena_cli import get_isaaclab_arena_cli_parser
    from isaaclab_arena.utils.isaaclab_utils.simulation_app import SimulationAppContext
    from dexterous_lab.storage import DATA_ROOT

    args = get_isaaclab_arena_cli_parser().parse_args([])
    preview = request['action'] == 'preview'
    args.device, args.visualizer, args.enable_cameras = "cuda:0", ['kit'] if preview else None, False
    if preview:
        args.headless = False
    args.kit_args = f"--portable-root {DATA_ROOT / '.cache/kit'}"
    with SimulationAppContext(args):
        evidence = convert(request) if request['action'] == 'convert' else validate(request)
        save_json(Path(request['run_dir']) / 'evidence.json', evidence)
        print("DEXLAB_ASSET_COMPLETE " + json.dumps(evidence), flush=True)


if __name__ == '__main__':
    main()
