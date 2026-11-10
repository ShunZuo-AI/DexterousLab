"""Bounded, configuration-driven first grasp attempt; reuse the existing Arena scene.

The Allegro uses its actual KUKA arm; the standalone Shadow uses an explicitly
labelled prescribed base trajectory. No object attachment or object state edits
are performed after env.reset(). This is an experimental baseline, not a paper algorithm.
"""

import argparse
import hashlib
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'src'))

from dexterous_lab.assets.catalog import save_json
from dexterous_lab.runtime import runtime_environment, shared_python


def outcome(lift, hold, criteria):
    """Judge this declared single trial, never convert a completed rollout to success."""
    if lift >= criteria['lift_height_m'] and hold >= criteria['hold_steps']:
        return True, None
    return False, 'no_lift' if lift < criteria['lift_height_m'] else 'no_sustained_multifinger_hold'


def launch(args):
    from dexterous_lab.config import read_toml
    from dexterous_lab.scenes.builder import SceneBuilder

    configuration = read_toml(args.config)
    specification = SceneBuilder().specification(args.hand, 'cube')
    if configuration[args.hand].get('robot_base_position_xyz'):
        specification['robot']['position_xyz'] = configuration[args.hand]['robot_base_position_xyz']
    specification['task']['episode_length_s'] = 30.0
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    directory = PROJECT / 'outputs' / f'{stamp}-first-grasp-{args.hand}-{uuid.uuid4().hex[:8]}'
    directory.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (directory / 'script_snapshot.py').write_bytes(source)
    local_asset_root = PROJECT / 'assets/cache/https/omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.2'
    if not local_asset_root.is_dir():
        raise ValueError('Previously downloaded official cache is missing; this experiment does not download assets')
    request = {'hand': args.hand, 'probe': args.probe, 'render': args.render,
               'record_video': args.record_video, 'seed': 42,
               'isaacsim_asset_root': str(local_asset_root), 'script_sha256': hashlib.sha256(source).hexdigest(),
               'configuration': configuration, 'specification': specification, 'run_dir': str(directory)}
    save_json(directory / 'request.json', request)
    command = [shared_python(), str(Path(__file__).resolve()), '--request', str(directory / 'request.json')]
    print(f'RUN_DIRECTORY={directory}', flush=True)
    with (directory / 'simulation.log').open('x') as stream:
        environment = runtime_environment()
        environment['ISAACSIM_ASSET_ROOT'] = str(local_asset_root)
        child = subprocess.Popen(command, cwd=directory, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        try:
            code = child.wait(timeout=600 if args.render else 240)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
            code = -1
    path = directory / 'result.json'
    result = json.loads(path.read_text()) if path.exists() else None
    save_json(directory / 'launch_result.json', {'command': command, 'exit_code': code, 'result': result})
    print(json.dumps({'run_directory': str(directory), 'exit_code': code, 'result': result}, indent=2), flush=True)
    return int(code != 0 or not result or not result.get('simulation_completed'))


def run(request):
    import numpy as np
    import torch
    from scipy.spatial.transform import Rotation
    from isaaclab_arena.environments.arena_env_builder import ArenaEnvBuilder
    from isaaclab_arena.environments.arena_env_builder_cfg import ArenaEnvBuilderCfg
    from dexterous_lab.scenes.builder import SceneBuilder
    from dexterous_lab.data_collection.collector import DatasetCollector
    from dexterous_lab.integrations.isaaclab.state import ResearchState, as_torch
    from dexterous_lab.integrations.isaaclab.validation import validate_loaded_scene
    from dexterous_lab.integrations.arena.worker import robot_mapping, validate_research_state
    from dexterous_lab.evaluation.criteria import next_hold_count

    output = Path(request['run_dir'])
    spec = request['specification']
    config = request['configuration']
    hand_cfg = config[request['hand']]
    description = SceneBuilder().build(spec)
    original_callback = description.env_cfg_callback
    def configure_experiment(env_cfg):
        env_cfg = original_callback(env_cfg)
        # Keep the trial continuous through the hold phase; record our criteria
        # without a task-success auto-reset erasing the measured state.
        env_cfg.terminations.success = None
        if config.get('robot_gravity_compensation', False):
            env_cfg.scene.robot.spawn.rigid_props.disable_gravity = True
        if request.get('record_video'):
            from isaaclab_visualizers.kit import KitVisualizerCfg

            env_cfg.sim.default_visualizer_cfg = KitVisualizerCfg(
                headless=True, window_width=960, window_height=540,
                eye=(-1.15, -0.8, 0.9), lookat=(-0.55, 0, 0.36))
        return env_cfg
    description.env_cfg_callback = configure_experiment
    env = ArenaEnvBuilder(description, ArenaEnvBuilderCfg(
        num_envs=1, seed=42, solve_relations=False, presets='physx', device='cuda:0')).make_registered()
    collector = None
    result = {'simulation_completed': False, 'grasp_success': None, 'hand': request['hand']}
    try:
        env.reset()
        state = ResearchState(env, spec['robot'])
        robot = state.robot
        mapping = robot_mapping(env, spec)
        save_json(output / 'robot_mapping.json', mapping)
        save_json(output / 'scene_validation.json', validate_loaded_scene(env, spec))
        validate_research_state(state)
        palm_id = robot.body_names.index(spec['robot']['palm_frame'])
        palm = state.palm_pose()[0].cpu().numpy()
        all_poses = as_torch(robot.data.body_pose_w)[0].cpu().numpy()
        R_W_H = Rotation.from_quat(palm[3:]).as_matrix()
        geometry = {'palm_pose_W': palm.tolist(), 'object_pose_W': state.object_pose()[0].cpu().tolist(),
                    'body_names': list(robot.body_names), 'body_poses_W': all_poses.tolist(),
                    'tip_origins_H': {name: (R_W_H.T @ (all_poses[robot.body_names.index(name), :3] - palm[:3])).tolist()
                                      for name in spec['robot']['fingertip_names']},
                    'joint_names': list(robot.joint_names), 'default_joint_positions': as_torch(robot.data.default_joint_pos)[0].cpu().tolist(),
                    'joint_limits': as_torch(robot.data.joint_pos_limits)[0].cpu().tolist(),
                    'action_terms': [{**row, 'class': type(env.unwrapped.action_manager.get_term(row['name'])).__name__}
                                     for row in mapping['action_terms']]}
        save_json(output / 'geometry_probe.json', geometry)
        if request['probe']:
            for _ in range(5):
                env.step(torch.zeros(env.action_space.shape, device=state.env.device))
            result.update(simulation_completed=True, steps_completed=5, scope='geometry inspection only')
            return
        limits = as_torch(robot.data.joint_pos_limits)[0]
        default = as_torch(robot.data.default_joint_pos)[0].clone()
        device = state.env.device
        q_open = default.clone()
        q_close = default.clone()
        for name, target in hand_cfg['open_joints'].items():
            q_open[robot.joint_names.index(name)] = target
        for name, target in hand_cfg['close_joints'].items():
            q_close[robot.joint_names.index(name)] = target
        if ((q_open < limits[:, 0]) | (q_open > limits[:, 1]) | (q_close < limits[:, 0]) | (q_close > limits[:, 1])).any():
            raise ValueError('Configured grasp joints exceed actual asset limits')
        arm_ids = [i for i, name in enumerate(robot.joint_names) if name.startswith('iiwa7_joint_')]
        R_target = Rotation.from_euler('xyz', hand_cfg['palm_euler_xyz_rad']).as_matrix()
        object_center = np.array(spec['object']['position_xyz'])
        grasp_xyz = object_center + np.array(hand_cfg['palm_offset_from_object_m'])
        pregrasp_xyz = grasp_xyz + np.array([0, 0, config['pregrasp_height_m']])
        lift_xyz = grasp_xyz + np.array([0, 0, config['lift_height_m']])
        start_xyz = palm[:3].copy()
        start_R = R_W_H.copy()
        root_start = as_torch(robot.data.root_pose_w)[0].cpu().numpy()
        T_B_H = np.eye(4)
        T_B_H[:3, :3] = Rotation.from_quat(root_start[3:]).as_matrix().T @ R_W_H
        T_B_H[:3, 3] = Rotation.from_quat(root_start[3:]).as_matrix().T @ (palm[:3] - root_start[:3])
        if request['render']:
            state.env.sim.set_camera_view(eye=(-1.15, -0.8, 0.9), target=(-0.55, 0, 0.36))
        video_frames = []
        if request.get('record_video'):
            (output / 'video_frames').mkdir(exist_ok=False)
            video_visualizer = next(visualizer for visualizer in state.env.sim.visualizers
                                    if hasattr(visualizer, 'render_rgb_array'))
        collector = DatasetCollector(output / 'trajectory', {'request': request, 'robot_mapping': mapping,
            'scope': 'One scripted, untrained grasp-and-lift attempt',
            'object_manipulation': 'dynamic only; no attachment or object pose writes after reset',
            'shadow_base_control': 'prescribed kinematic base path, not an actuated arm' if not arm_ids else None})
        criteria = config['criteria']
        hold = 0
        max_hold = 0
        max_lift = 0.0
        max_force = 0.0
        min_contact_separation = None
        min_cube_bottom_above_table = None
        separation_error = None
        import inspect
        contact_view = state.env.scene.sensors['dexlab_object_contact'].contact_view
        detail_method = (contact_view.get_normal_contact_data if hasattr(contact_view, 'get_normal_contact_data')
                         else contact_view.get_contact_data)
        save_json(output / 'contact_api.json', {'method': detail_method.__name__, 'doc': inspect.getdoc(detail_method)})
        peak_active_tips = 0
        phases = []
        all_metrics = []
        step = 0
        previous_xyz = start_xyz.copy()
        previous_R = start_R.copy()
        close_fraction = 0.0
        current_ik_target = default.clone()

        def encode_action(target):
            values = []
            current = as_torch(robot.data.joint_pos)[0]
            for row in mapping['action_terms']:
                term = state.env.action_manager.get_term(row['name'])
                for name in row['joint_names']:
                    idx = robot.joint_names.index(name)
                    if type(term).__name__ == 'RelativeJointPositionAction':
                        bound = config['max_joint_step_rad'] if idx in arm_ids else 0.04
                        values.append(torch.clamp(target[idx] - current[idx], -bound, bound) / term.cfg.scale)
                    elif type(term).__name__ == 'JointPositionAction':
                        offset = default[idx] if term.cfg.use_default_offset else term.cfg.offset
                        values.append((target[idx] - offset) / term.cfg.scale)
                    else:
                        raise ValueError(f'Unsupported actual action term: {type(term).__name__}')
                for name in row['tendon_names']:
                    finger = name[3:5]
                    total = target[robot.joint_names.index(f'rh_{finger}J1')] + target[robot.joint_names.index(f'rh_{finger}J2')]
                    values.append((total - term.cfg.offset) / term.cfg.scale)
            return torch.stack([torch.as_tensor(v, device=device) for v in values]).unsqueeze(0)

        initial_snapshot = state.snapshot(0)
        initial_z = initial_snapshot['object_pose'][0][2]
        collector.record(initial_snapshot, np.zeros(mapping['action_dim']))
        for phase, count, target_xyz, target_R, target_close in [
            ('settle', config['settle_steps'], start_xyz, start_R, 0.0),
            ('approach', config['approach_steps'], pregrasp_xyz, R_target, 0.0),
            ('descend', config['descend_steps'], grasp_xyz, R_target, 0.0),
            ('close', config['close_steps'], grasp_xyz, R_target, 1.0),
            ('lift', config['lift_steps'], lift_xyz, R_target, 1.0),
            ('hold', config['hold_steps'], lift_xyz, R_target, 1.0),
        ]:
            phase_start = step
            fraction_start = close_fraction
            delta_R = Rotation.from_matrix(target_R @ previous_R.T).as_rotvec()
            for local in range(1, count + 1):
                alpha = local / count
                desired_xyz = previous_xyz + alpha * (target_xyz - previous_xyz)
                desired_R = Rotation.from_rotvec(alpha * delta_R).as_matrix() @ previous_R
                close_fraction = fraction_start + alpha * (target_close - fraction_start)
                target_joints = (1 - close_fraction) * q_open + close_fraction * q_close
                if arm_ids:
                    actual_pose = state.palm_pose()[0].cpu().numpy()
                    error = np.r_[desired_xyz - actual_pose[:3],
                                  Rotation.from_matrix(desired_R @ Rotation.from_quat(actual_pose[3:]).as_matrix().T).as_rotvec()]
                    # PhysX excludes the fixed root from the Jacobian body axis.
                    jacobian_body_id = palm_id - 1 if robot.is_fixed_base else palm_id
                    jacobian_joint_ids = [idx + robot.num_base_dofs for idx in arm_ids]
                    jac = as_torch(robot.data.body_link_jacobian_w)[0, jacobian_body_id, :, :][:, jacobian_joint_ids]
                    error_t = torch.tensor(error, dtype=torch.float32, device=device)
                    # Bounded damped least-squares using the real current world-frame Jacobian.
                    delta = jac.T @ torch.linalg.solve(jac @ jac.T + config['ik_damping'] ** 2 * torch.eye(6, device=device), error_t)
                    delta = torch.clamp(delta, -config['max_joint_step_rad'], config['max_joint_step_rad'])
                    target_joints[arm_ids] = as_torch(robot.data.joint_pos)[0, arm_ids] + delta
                else:
                    # Shadow has no arm. Only its base follows the declared path; object stays fully dynamic.
                    T_W_H = np.eye(4)
                    T_W_H[:3, :3], T_W_H[:3, 3] = desired_R, desired_xyz
                    T_W_B = T_W_H @ np.linalg.inv(T_B_H)
                    pose = np.r_[T_W_B[:3, 3], Rotation.from_matrix(T_W_B[:3, :3]).as_quat()]
                    robot.write_root_pose_to_sim(torch.tensor(pose[None], dtype=torch.float32, device=device))
                target_joints = torch.clamp(target_joints, limits[:, 0], limits[:, 1])
                actions = encode_action(target_joints)
                _, _, terminated, truncated, _ = env.step(actions)
                step += 1
                if terminated.any() or truncated.any():
                    raise RuntimeError(f'Unexpected task reset at step {step}; stop rather than falsify trajectory')
                validate_research_state(state)
                snapshot = state.snapshot(step)
                collector.record(snapshot, actions[0].cpu().numpy())
                forces = torch.linalg.vector_norm(state.contacts()['normal_forces_W'], dim=-1)
                force = float(forces.max())
                active = int((forces > criteria['contact_force_threshold_n']).sum())
                lift = snapshot['object_pose'][0][2] - initial_z
                speed = float(torch.linalg.vector_norm(as_torch(state.object.data.root_vel_w)[0, :3]))
                hold = next_hold_count(hold, lift, force if active >= 2 else 0.0, speed, criteria) if phase in ('lift', 'hold') else 0
                max_hold, max_lift, max_force, peak_active_tips = max(max_hold, hold), max(max_lift, lift), max(max_force, force), max(peak_active_tips, active)
                metric = {'step': step, 'phase': phase, 'object_lift_m': lift, 'object_speed_m_s': speed,
                          'max_tip_normal_force_n': force, 'active_tip_count': active,
                          'palm_target_xyz': desired_xyz.tolist(), 'palm_actual_xyz': snapshot['hand_root_pose'][0][:3]}
                if separation_error is None:
                    try:
                        _, _, _, distances, counts, offsets = detail_method(dt=state.env.sim.get_physics_dt())
                        distances = as_torch(distances).flatten()
                        counts, offsets = as_torch(counts).flatten(), as_torch(offsets).flatten()
                        pair_min = []
                        for n, offset in zip(counts.cpu().tolist(), offsets.cpu().tolist(), strict=True):
                            if n:
                                pair_min.append(float(distances[int(offset):int(offset + n)].min()))
                        if pair_min:
                            metric['min_tip_object_separation_m'] = min(pair_min)
                            min_contact_separation = min(pair_min + ([] if min_contact_separation is None else [min_contact_separation]))
                    except Exception as exc:
                        separation_error = f'{type(exc).__name__}: {exc}'
                object_pose = snapshot['object_pose'][0]
                cube_rotation = Rotation.from_quat(object_pose[3:]).as_matrix()
                cube_half_extent_z = float(np.abs(cube_rotation[2]) @ (np.array(spec['object']['size']) / 2))
                table_top = spec['scene']['table_position_xyz'][2] + spec['scene']['table_size'][2] / 2
                gap = object_pose[2] - cube_half_extent_z - table_top
                metric['cube_bottom_to_table_top_m'] = gap
                min_cube_bottom_above_table = min(gap, gap if min_cube_bottom_above_table is None else min_cube_bottom_above_table)
                all_metrics.append(metric)
                if request['render']:
                    state.env.sim.render()
                if request.get('record_video') and step % 2 == 0:
                    from PIL import Image

                    frame_path = output / 'video_frames' / f'{len(video_frames):06d}.png'
                    deadline = time.monotonic() + 60
                    while True:
                        state.env.sim.render()
                        frame = video_visualizer.render_rgb_array()
                        if frame.size and np.any(frame):
                            Image.fromarray(frame).save(frame_path)
                            break
                        if time.monotonic() >= deadline:
                            raise RuntimeError(f'Offscreen frame capture timed out: {frame_path}')
                        time.sleep(0.002)
                    video_frames.append({'frame': len(video_frames), 'step': step,
                                         'simulation_time_s': step * float(state.env.step_dt), 'phase': phase})
                if local == count:
                    print(json.dumps(metric), flush=True)
            phases.append({'phase': phase, 'first_step': phase_start + 1, 'last_step': step,
                           'end_metrics': all_metrics[-1]})
            if request.get('record_video'):
                Image.fromarray(frame).save(output / f'{phase}.png')
            elif request['render']:
                try:
                    from omni.kit.viewport.utility import capture_viewport_to_file, get_active_viewport
                    capture = capture_viewport_to_file(get_active_viewport(), str(output / f'{phase}.png'))
                    for _ in range(8):
                        state.env.sim.render()
                        if (output / f'{phase}.png').exists():
                            break
                except Exception as exc:
                    print('SCREENSHOT_UNAVAILABLE', str(exc), flush=True)
            previous_xyz, previous_R = target_xyz.copy(), target_R.copy()
        success, failure_reason = outcome(max_lift, hold, criteria)
        result.update(simulation_completed=True, steps_completed=step, grasp_success=success,
            failure_reason=failure_reason,
            max_lift_m=max_lift, max_tip_force_n=max_force, peak_active_tip_count=peak_active_tips,
            final_hold_steps=hold, max_hold_steps=max_hold, phases=phases,
            actual_joint_count=len(robot.joint_names), action_dim=mapping['action_dim'],
            robot_usd_path=mapping['robot_usd_path'], object_asset='dexterous_lab.assets.primitives:Cube',
            collision_penetration={'min_tip_object_separation_m': min_contact_separation,
                'contact_api_error': separation_error,
                'max_tip_object_penetration_m': max(0, -min_contact_separation) if min_contact_separation is not None else None,
                'min_cube_bottom_to_table_top_m': min_cube_bottom_above_table,
                'scope': 'Detailed PhysX contacts for configured fingertips only plus analytic cube/table vertical gap; all-link self-collision is not audited'},
            shadow_base_control='prescribed kinematic support trajectory' if not arm_ids else None)
        save_json(output / 'phase_metrics.json', all_metrics)
        if request.get('record_video'):
            frame_rate = 1.0 / (2 * float(state.env.step_dt))
            command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-framerate', str(frame_rate),
                       '-i', str(output / 'video_frames/%06d.png'), '-vf',
                       'scale=960:540:force_original_aspect_ratio=decrease,pad=960:540:(ow-iw)/2:(oh-ih)/2',
                       '-c:v', 'libx264', '-crf', '19', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                       str(output / 'motion.mp4')]
            subprocess.run(command, check=True, timeout=90, capture_output=True)
            result['video'] = {'path': str(output / 'motion.mp4'), 'frames': len(video_frames),
                               'fps': frame_rate, 'duration_s': len(video_frames) / frame_rate,
                               'scope': 'Actual viewport frames every two environment steps; no interpolated motion'}
            save_json(output / 'video_frames.json', {'frames': video_frames, 'encoding_command': command})
        collector.finish(result)
        collector = None
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        if collector is not None:
            if collector.frames:
                collector.finish(result)
            else:
                collector.stream.close()
        save_json(output / 'result.json', result)
        env.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--hand', choices=('allegro', 'shadow'), default='allegro')
    parser.add_argument('--config', type=Path, default=PROJECT / 'configs/experiments/first_grasp.toml')
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--render', action='store_true')
    parser.add_argument('--record-video', action='store_true', help='Capture real viewport motion as MP4; enables render')
    parser.add_argument('--request', type=Path)
    args = parser.parse_args()
    if args.record_video:
        args.render = True
        if args.probe:
            parser.error('--record-video cannot be combined with --probe')
        if shutil.which('ffmpeg') is None:
            parser.error('--record-video requires ffmpeg on PATH')
    if not args.request:
        return launch(args)
    request = json.loads(args.request.read_text())
    sys.argv = [sys.argv[0]]
    from isaaclab_arena.cli.isaaclab_arena_cli import get_isaaclab_arena_cli_parser
    from isaaclab_arena.utils.isaaclab_utils.simulation_app import SimulationAppContext
    from dexterous_lab.storage import DATA_ROOT

    sim_args = get_isaaclab_arena_cli_parser().parse_args([])
    sim_args.device, sim_args.visualizer, sim_args.enable_cameras = 'cuda:0', ['kit'] if request['render'] else None, bool(request.get('record_video'))
    if request['render']:
        sim_args.headless = bool(request.get('record_video'))
    sim_args.kit_args = f'--portable-root {DATA_ROOT / ".cache/kit"}'
    if request.get('record_video'):
        sim_args.kit_args += ' --no-window --enable omni.kit.viewport.window --enable omni.kit.viewport.utility'
    with SimulationAppContext(sim_args):
        run(request)
    return 0


if __name__ == '__main__':
    sys.exit(main())
