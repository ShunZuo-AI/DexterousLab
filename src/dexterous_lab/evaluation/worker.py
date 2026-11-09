"""Actual Arena Shadow capture, actuator replay and finite batch physics evaluation.

Independent implementation; design references are documented in
docs/research/dexgarmentlab_analysis.md. No upstream source code is copied.
"""

import json
import importlib.metadata
from pathlib import Path
import sys

from dexterous_lab.assets.catalog import save_json


def tendon_coordinates(joints):
    return {f'rh_{finger}J0': joints[f'rh_{finger}J1'] + joints[f'rh_{finger}J2']
            for finger in ('FF', 'MF', 'RF', 'LF')}


def action_for_candidate(env, candidate, mapping):
    import numpy as np
    import torch
    from dexterous_lab.integrations.isaaclab.state import as_torch

    robot = env.unwrapped.scene['robot']
    if set(candidate.joint_positions) != set(robot.joint_names):
        raise ValueError('Candidate must cover the complete physical joint set')
    positions = np.array([candidate.joint_positions[name] for name in robot.joint_names])
    limits = as_torch(robot.data.joint_pos_limits)[0].cpu().numpy()
    if ((positions < limits[:, 0] - 1e-4) | (positions > limits[:, 1] + 1e-4)).any():
        raise ValueError('Candidate joint position violates the loaded asset limits')
    expected = tendon_coordinates(candidate.joint_positions)
    if set(expected) != set(candidate.tendon_positions):
        raise ValueError('Candidate must include the four Shadow tendon coordinates')
    if any(abs(expected[name] - candidate.tendon_positions[name]) > 0.01 for name in expected):
        raise ValueError('Candidate tendon coordinates disagree with physical joint sums')
    values = []
    default = as_torch(robot.data.default_joint_pos)[0].cpu().numpy()
    for descriptor in mapping['action_terms']:
        term = env.unwrapped.action_manager.get_term(descriptor['name'])
        for name in descriptor['joint_names']:
            # Current shadow.py explicitly uses scale=.1 and default joint offsets.
            values.append((candidate.joint_positions[name] - default[robot.joint_names.index(name)]) / term.cfg.scale)
        for name in descriptor['tendon_names']:
            target = candidate.tendon_positions[name]
            if not 0 <= target <= 3.1415:
                raise ValueError('Candidate tendon target violates source limits')
            values.append((target - term.cfg.offset) / term.cfg.scale)
    action = torch.tensor(values, device=env.unwrapped.device, dtype=torch.float32)
    if len(action) != env.unwrapped.action_manager.total_action_dim:
        raise ValueError('Action mapping dimension mismatch')
    return action


def restore_state(env, state, candidate):
    import numpy as np
    import torch
    from scipy.spatial.transform import Rotation
    from dexterous_lab.integrations.isaaclab.state import as_torch

    if candidate.hand_root_frame != state.configuration['palm_frame']:
        raise ValueError('Candidate palm frame differs from the loaded hand')
    def matrix(pose):
        value = np.eye(4)
        value[:3, :3] = Rotation.from_quat(pose[3:]).as_matrix()
        value[:3, 3] = pose[:3]
        return value
    robot = state.robot
    if np.linalg.norm(np.array(candidate.object_pose[:3]) - np.array(state.env.cfg.scene.object.init_state.pos)) > 0.01:
        raise ValueError('Candidate object pose must start at the configured tabletop position, not an already lifted pose')
    q = torch.tensor([[candidate.joint_positions[name] for name in robot.joint_names]], device=state.env.device)
    robot.write_joint_state_to_sim(q, torch.zeros_like(q))
    robot.update(0.0)
    # Fixed-base wrist/palm has actuated joints: calibrate T_B_H at the written pose.
    palm = state.palm_pose()[0].cpu().numpy()
    base = as_torch(robot.data.root_pose_w)[0].cpu().numpy()
    T_B_H = np.linalg.inv(matrix(base)) @ matrix(palm)
    T_W_B = matrix(candidate.hand_root_pose) @ np.linalg.inv(T_B_H)
    root = np.r_[T_W_B[:3, 3], Rotation.from_matrix(T_W_B[:3, :3]).as_quat()]
    robot.write_root_pose_to_sim(torch.tensor(root[None], device=state.env.device, dtype=torch.float32))
    robot.write_root_velocity_to_sim(torch.zeros((1, 6), device=state.env.device))
    state.object.write_root_pose_to_sim(torch.tensor([candidate.object_pose], device=state.env.device))
    state.object.write_root_velocity_to_sim(torch.zeros((1, 6), device=state.env.device))
    state.env.scene.write_data_to_sim()
    state.env.sim.forward()
    state.env.scene.update(state.env.step_dt)
    error = float(np.max(np.abs(state.joint_state()['positions'][0].cpu().numpy() - q[0].cpu().numpy())))
    palm_error = float(np.linalg.norm(state.palm_pose()[0, :3].cpu().numpy() - np.array(candidate.hand_root_pose[:3])))
    palm_actual = state.palm_pose()[0].cpu().numpy()
    rotation_error = float((Rotation.from_quat(palm_actual[3:]).inv() * Rotation.from_quat(candidate.hand_root_pose[3:])).magnitude())
    object_error = float(np.linalg.norm(state.object_pose()[0, :3].cpu().numpy() - np.array(candidate.object_pose[:3])))
    return {'joint_restore_max_error_rad': error, 'palm_restore_position_error_m': palm_error,
            'palm_restore_rotation_error_rad': rotation_error, 'object_restore_position_error_m': object_error}


def run(request):
    import numpy as np
    import torch
    from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder
    from isaaclab_arena.environments.arena_env_builder_cfg import ArenaEnvBuilderCfg
    from dexterous_lab.config import checked_dataclass, ObjectConfig
    from dexterous_lab.data_collection.collector import DatasetCollector
    from dexterous_lab.evaluation.runner import summarize_trials
    from dexterous_lab.evaluation.criteria import next_hold_count
    from dexterous_lab.grasp_synthesis.candidate import GraspCandidate
    from dexterous_lab.integrations.arena.worker import robot_mapping, validate_research_state
    from dexterous_lab.integrations.isaaclab.state import ResearchState, as_torch
    from dexterous_lab.integrations.isaaclab.validation import validate_loaded_scene
    from dexterous_lab.policies.registry import PolicyRegistry
    from dexterous_lab.scenes.builder import SceneBuilder

    output = Path(request['run_dir'])
    specification = request['specification']
    description = SceneBuilder().build(specification)
    env = ArenaEnvBuilder(description, ArenaEnvBuilderCfg(num_envs=1, seed=request['seed'], solve_relations=False,
                                                         presets='physx', device='cuda:0')).make_registered()
    trials = []
    try:
        env.reset()
        mapping = robot_mapping(env, specification)
        save_json(output / 'robot_mapping.json', mapping)
        loaded_scene = validate_loaded_scene(env, specification)
        for extra in specification.get('additional_objects', []):
            item = env.unwrapped.scene[extra['name']]
            if not torch.isfinite(as_torch(item.data.root_pose_w)).all():
                raise RuntimeError('Additional scene object has nonfinite pose')
        loaded_scene['additional_objects_loaded'] = [item['name'] for item in specification.get('additional_objects', [])]
        save_json(output / 'scene_validation.json', loaded_scene)
        state = ResearchState(env, specification['robot'])
        candidates = request['candidates'] or [None]
        for index, value in enumerate(candidates):
            row = {'index': index, 'loaded': False, 'simulation_completed': False, 'success': None, 'failure_reason': None}
            collector = DatasetCollector(output / f'trial_{index:03d}', {
                'seed': request['seed'] if value is None else value['seed'], 'specification': specification,
                'criteria': request['criteria'], 'source_candidate': value, 'physics': 'physx',
                'robot_mapping': mapping, 'simulation_dt': env.unwrapped.sim.get_physics_dt(),
                'environment_step_dt': env.unwrapped.step_dt,
                'runtime_versions': {name: importlib.metadata.version(name) for name in ('isaacsim', 'isaaclab', 'isaaclab_arena', 'torch')},
                'quaternion_order': 'xyzw', 'frame': 'W', 'length_unit': 'm', 'joint_unit': 'rad',
                'source_design': 'DexGarmentLab:e4e298e:independent-architecture-adaptation'})
            try:
                env.reset(seed=request['seed'] if value is None else value['seed'])
                validate_research_state(state)
                if value is None:
                    action = torch.zeros(env.unwrapped.action_manager.total_action_dim, device=state.env.device)
                    # Explicit small thumb position command: test controllability, not a grasp primitive.
                    for term in mapping['action_terms']:
                        if 'rh_THJ1' in term['joint_names']:
                            action[term['start'] + term['joint_names'].index('rh_THJ1')] = 1.5
                    row['loaded'] = True
                else:
                    candidate = GraspCandidate(**value)
                    if candidate.asset_version != specification['object']['asset_version']:
                        raise ValueError('Candidate asset version differs from selected object')
                    action = action_for_candidate(env, candidate, mapping)
                    row['restoration'] = restore_state(env, state, candidate)
                    if (row['restoration']['joint_restore_max_error_rad'] > 1e-4
                            or row['restoration']['palm_restore_position_error_m'] > 0.005
                            or row['restoration']['palm_restore_rotation_error_rad'] > 0.01
                            or row['restoration']['object_restore_position_error_m'] > 1e-4):
                        raise ValueError('Saved state restoration exceeded tolerance')
                    row['loaded'] = True
                policy = PolicyRegistry().load(request['policy'], target_action=action.cpu().numpy())
                policy.reset()
                initial_z = float(state.object_pose()[0, 2])
                reference_z = (specification['object']['position_xyz'][2]
                               if value is not None else initial_z)
                criteria = request['criteria']
                hold = 0
                best_hold = 0
                max_lift = 0.0
                final_tracking_error = None
                collector.record(state.snapshot(0), action.cpu().numpy())
                initial = state.snapshot(0)
                for step in range(1, request['steps'] + 1):
                    command = torch.tensor(policy.predict(state.snapshot(step - 1)), device=state.env.device).unsqueeze(0)
                    _, _, terminated, truncated, _ = env.step(command)
                    validate_research_state(state)
                    if terminated.any() or truncated.any():
                        raise RuntimeError('Environment auto-reset would invalidate candidate evaluation')
                    snapshot = state.snapshot(step)
                    collector.record(snapshot, command[0].cpu().numpy())
                    lift = snapshot['object_pose'][0][2] - reference_z
                    max_lift = max(max_lift, lift)
                    contacts = state.contacts()
                    force = float(torch.linalg.vector_norm(contacts['normal_forces_W'], dim=-1).max())
                    speed = float(torch.linalg.vector_norm(as_torch(state.object.data.root_vel_w)[0, :3]))
                    hold = next_hold_count(hold, lift, force, speed, criteria)
                    best_hold = max(best_hold, hold)
                    if step == 1 or step % 25 == 0:
                        print(f'DEXLAB_TRIAL {index} STEP {step}/{request["steps"]}', flush=True)
                row.update(simulation_completed=True, steps_completed=request['steps'], max_lift_m=max_lift,
                           max_consecutive_hold_steps=best_hold, final_hold_steps=hold)
                if value is None:
                    joints = dict(zip(snapshot['joint_names'], snapshot['joint_positions'][0], strict=True))
                    collector.save_candidate(snapshot, object_id=specification['object']['kind'], hand_id='shadow',
                        seed=request['seed'], asset_version=specification['object']['asset_version'],
                        tendon_positions=tendon_coordinates(joints))
                    name = 'rh_THJ1'
                    joint_index = snapshot['joint_names'].index(name)
                    row['control_check'] = {'joint': name, 'commanded_position_rad': 0.15,
                        'initial_position_rad': initial['joint_positions'][0][joint_index],
                        'final_position_rad': snapshot['joint_positions'][0][joint_index]}
                    if abs(row['control_check']['final_position_rad'] - row['control_check']['initial_position_rad']) < 0.01:
                        raise RuntimeError('Small thumb control command produced no measurable joint response')
                    row['capture_verified'] = True
                    row['failure_reason'] = None
                else:
                    row['success'] = hold >= criteria['hold_steps']
                    row['failure_reason'] = None if row['success'] else ('no_lift' if max_lift < criteria['lift_height_m'] else 'no_sustained_contact_and_hold')
                    current = state.joint_state()
                    direct = mapping['configured_control_joints']
                    final_tracking_error = max(abs(snapshot['joint_positions'][0][snapshot['joint_names'].index(name)] - candidate.joint_positions[name]) for name in direct)
                    row['direct_joint_tracking_max_error_rad'] = final_tracking_error
                    row['pose_replay_passed'] = final_tracking_error <= 0.03
            except Exception as exc:
                row['success'] = None
                row['failure_reason'] = f'{type(exc).__name__}: {exc}'
            if collector.frames:
                collector.finish(row)
            else:
                collector.stream.close()
                save_json(collector.directory / 'result.json', row)
            trials.append(row)
            save_json(output / 'trials.json', trials)
    finally:
        env.close()
    summary = summarize_trials(trials)
    report = {'completed': True, 'mode': request['mode'], 'summary': summary, 'trials': trials,
              'scope': 'Measured lift/contact/hold baseline; not force-closure or full grasp robustness validation',
              'criteria': request['criteria'], 'scene_validation': loaded_scene}
    if request['mode'] == 'capture' and not trials[0].get('capture_verified'):
        report['completed'] = False
    if request['mode'] == 'replay' and not trials[0].get('pose_replay_passed'):
        report['completed'] = False
    save_json(output / 'report.json', report)


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    sys.argv = [sys.argv[0]]
    from isaaclab_arena.cli.isaaclab_arena_cli import get_isaaclab_arena_cli_parser
    from isaaclab_arena.utils.isaaclab_utils.simulation_app import SimulationAppContext
    from dexterous_lab.storage import DATA_ROOT

    args = get_isaaclab_arena_cli_parser().parse_args([])
    args.device, args.visualizer, args.enable_cameras = 'cuda:0', None, False
    args.kit_args = f'--portable-root {DATA_ROOT / ".cache/kit"}'
    with SimulationAppContext(args):
        run(request)


if __name__ == '__main__':
    main()
