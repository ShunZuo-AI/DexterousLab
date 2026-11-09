"""Isolated headless simulation worker with explicit completion evidence."""

import importlib.metadata
import json
from pathlib import Path
import sys

from dexterous_lab.runtime import write_json


def official_environment(name):
    if name == "cube_goal_pose":
        from isaaclab_arena_environments.cube_goal_pose_environment import CubeGoalPoseEnvironment, CubeGoalPoseEnvironmentCfg

        return CubeGoalPoseEnvironment().build(CubeGoalPoseEnvironmentCfg())
    if name == "dexsuite_lift":
        from isaaclab_arena.environments.arena_environment_factory import ArenaEnvironmentCfg
        from isaaclab_arena_environments.dexsuite_lift_environment import DexsuiteLiftEnvironment

        return DexsuiteLiftEnvironment().build(ArenaEnvironmentCfg())
    raise ValueError(f"Unknown official environment: {name}")


def assert_finite(value):
    import torch

    if isinstance(value, torch.Tensor):
        if not torch.isfinite(value).all().item():
            raise RuntimeError("Simulation produced a non-finite observation or state")
    elif isinstance(value, dict):
        for item in value.values():
            assert_finite(item)


def robot_mapping(env, specification):
    robot = env.unwrapped.scene["robot"]
    configuration = specification["robot"]
    if env.unwrapped.action_manager.total_action_dim != configuration["action_dim"]:
        raise RuntimeError("Actual robot action dimension differs from configuration")
    for name in configuration["joint_names"]:
        if name not in robot.joint_names:
            raise RuntimeError(f"Configured joint {name} is absent from the loaded articulation")
    for name in configuration["fingertip_names"]:
        if name not in robot.body_names:
            raise RuntimeError(f"Configured fingertip {name} is absent from the loaded articulation")
    terms = []
    start = 0
    for term_name in env.unwrapped.action_manager.active_terms:
        term = env.unwrapped.action_manager.get_term(term_name)
        descriptor = term.IO_descriptor
        joints = getattr(descriptor, "joint_names", None)
        tendons = getattr(descriptor, "tendon_names", None)
        terms.append({"name": term_name, "start": start, "stop": start + term.action_dim,
                      "joint_names": list(joints) if joints is not None else [],
                      "tendon_names": list(tendons) if tendons is not None else []})
        start += term.action_dim
    direct_joints = []
    tendon_coordinates = []
    for term in terms:
        direct_joints.extend(term["joint_names"])
        tendon_coordinates.extend(term["tendon_names"])
    if sorted(direct_joints) != sorted(configuration["joint_names"]):
        raise RuntimeError("Actual joint action coordinates differ from hand configuration")
    if sorted(tendon_coordinates) != sorted(configuration["tendon_names"]):
        raise RuntimeError("Actual tendon action coordinates differ from hand configuration")
    return {"articulation_joint_names": list(robot.joint_names), "body_names": list(robot.body_names),
            "configured_control_joints": configuration["joint_names"], "tendon_coordinates": configuration["tendon_names"],
            "action_dim": env.unwrapped.action_manager.total_action_dim,
            "action_term_names": list(env.unwrapped.action_manager.active_terms),
            "action_terms": terms,
            "fingertip_body_names": configuration["fingertip_names"],
            "requires_arm": configuration["requires_arm"],
            "robot_usd_path": str(env.unwrapped.cfg.scene.robot.spawn.usd_path)}


def validate_research_state(state):
    joints = state.joint_state()
    assert_finite({"joint_positions": joints["positions"], "joint_velocities": joints["velocities"],
                   "palm_pose": state.palm_pose(), "object_pose": state.object_pose()})
    if joints["positions"].shape != (state.env.num_envs, len(joints["names"])):
        raise RuntimeError("Joint state shape does not match the loaded articulation")
    state.contacts()


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    run_dir = Path(request["run_dir"])
    from isaaclab_arena.cli.isaaclab_arena_cli import get_isaaclab_arena_cli_parser
    from isaaclab_arena.utils.isaaclab_utils.simulation_app import SimulationAppContext

    args = get_isaaclab_arena_cli_parser().parse_args([])
    args.device = "cuda:0"
    args.visualizer = None
    args.enable_cameras = False
    from dexterous_lab.storage import DATA_ROOT

    args.kit_args = f"--portable-root {DATA_ROOT / '.cache/kit'}"
    sys.argv = [sys.argv[0]]
    with SimulationAppContext(args):
        import torch
        from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder
        from isaaclab_arena.environments.arena_env_builder_cfg import ArenaEnvBuilderCfg

        if request["kind"] == "arena":
            description = official_environment(request["environment"])
        else:
            from dexterous_lab.scenes.tabletop import DexterousLabTabletopEnvironment, TabletopEnvironmentCfg

            description = DexterousLabTabletopEnvironment().build(TabletopEnvironmentCfg(specification=request["config"]))
        builder = ArenaEnvBuilder(description, ArenaEnvBuilderCfg(
            num_envs=request["num_envs"], seed=request["seed"], solve_relations=False,
            presets=request["backend"], device="cuda:0",
        ))
        env = builder.make_registered()
        try:
            observations, _ = env.reset()
            assert_finite(observations)
            env.unwrapped.episode_recorder.set_output_path(str(run_dir / "episode_results.jsonl"))
            env.unwrapped.episode_recorder.set_job_name("dexlab_smoke")
            mapping = robot_mapping(env, request["config"]) if request["kind"] == "scene" else None
            research_state = None
            scene_validation = None
            if mapping:
                from dexterous_lab.config import ObjectConfig, checked_dataclass
                from dexterous_lab.integrations.isaaclab.state import ResearchState
                from dexterous_lab.integrations.isaaclab.validation import validate_loaded_scene
                from dexterous_lab.objects.mesh import get_object_mesh

                write_json(run_dir / "robot_mapping.json", mapping)
                scene_validation = validate_loaded_scene(env, request["config"])
                research_state = ResearchState(env, request["config"]["robot"])
                validate_research_state(research_state)
                mesh = get_object_mesh(checked_dataclass(ObjectConfig, request["config"]["object"]))
                mesh.export(run_dir / "object_mesh.obj")
                scene_validation["mesh"] = {
                    "path": "object_mesh.obj", "frame": "O", "length_unit": "m",
                    "vertices": len(mesh.vertices), "faces": len(mesh.faces),
                    "extents_m": mesh.extents.tolist(),
                    "curved_surface_tessellated": request["config"]["object"]["kind"] in ("sphere", "cylinder"),
                }
                write_json(run_dir / "scene_validation.json", scene_validation)
            actions = torch.zeros(env.action_space.shape, device=env.unwrapped.device)
            terminated_count = 0
            truncated_count = 0
            with (run_dir / "states.jsonl").open("x") as states, torch.inference_mode():
                if mapping:
                    states.write(json.dumps(research_state.snapshot(0), allow_nan=False) + "\n")
                for step in range(1, request["steps"] + 1):
                    observations, reward, terminated, truncated, _ = env.step(actions)
                    assert_finite(observations)
                    assert_finite(reward)
                    if research_state:
                        validate_research_state(research_state)
                    terminated_count += int(terminated.sum().item())
                    truncated_count += int(truncated.sum().item())
                    if mapping:
                        states.write(json.dumps(research_state.snapshot(step), allow_nan=False) + "\n")
                    if step == 1 or step % 10 == 0 or step == request["steps"]:
                        print(f"DEXLAB_STEP {step}/{request['steps']}", flush=True)
            evidence = {
                "environment": description.name, "steps_completed": request["steps"],
                "num_envs": env.unwrapped.num_envs, "device": str(env.unwrapped.device),
                "physics_class": type(env.unwrapped.cfg.sim.physics).__name__,
                "simulated_seconds": request["steps"] * env.unwrapped.step_dt,
                "action_dim": env.unwrapped.action_manager.total_action_dim,
                "physics_steps_completed": request["steps"] * env.unwrapped.cfg.decimation,
                "research_state_checks": request["steps"] + 1 if research_state else 0,
                "scene_validation": scene_validation,
                "terminated_count": terminated_count, "truncated_count": truncated_count,
                "finite_observations": True, "grasp_success": None, "policy": "zero_action",
                "python_prefix": sys.prefix,
                "versions": {name: importlib.metadata.version(name) for name in ("isaacsim", "isaaclab", "isaaclab_arena", "torch")},
            }
            if mapping:
                spawner = env.unwrapped.cfg.scene.object.spawn
                evidence["object_spawn"] = {
                    "class": type(spawner).__name__,
                    "size": getattr(spawner, "size", None),
                    "radius": getattr(spawner, "radius", None),
                    "height": getattr(spawner, "height", None),
                    "scale": getattr(spawner, "scale", None),
                    "initial_position_xyz": env.unwrapped.cfg.scene.object.init_state.pos,
                    "initial_rotation_xyzw": env.unwrapped.cfg.scene.object.init_state.rot,
                }
        finally:
            env.close()
        write_json(run_dir / "simulation_result.json", evidence)
        print("DEXLAB_SIMULATION_COMPLETE " + json.dumps(evidence), flush=True)


if __name__ == "__main__":
    main()
