"""Read real first-grasp artifacts and export a comparison figure and phase storyboard."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from dexterous_lab.assets.catalog import save_json, sha256_file


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image, ImageDraw

    directory = ROOT / 'docs/experiments'
    entries = {}
    fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
    for hand in ('allegro', 'shadow'):
        log = directory / f'{hand}_final_command.log'
        match = re.search(r'^RUN_DIRECTORY=(.+)$', log.read_text(), re.M)
        if not match:
            raise ValueError(f'Missing run directory in {log}')
        run = Path(match.group(1))
        result = json.loads((run / 'result.json').read_text())
        request = json.loads((run / 'request.json').read_text())
        mapping = json.loads((run / 'robot_mapping.json').read_text())
        metrics = json.loads((run / 'phase_metrics.json').read_text())
        assert result['simulation_completed'] and len(metrics) == result['steps_completed']
        with np.load(run / 'trajectory/trajectory.npz', allow_pickle=False) as data:
            assert len(data['step']) == result['steps_completed'] + 1
            for key in ('joint_positions', 'joint_velocities', 'object_pose', 'hand_root_pose', 'action',
                        'contact_points', 'contact_normal_forces_W'):
                assert np.isfinite(data[key]).all(), (hand, key)
            assert len(data['joint_names']) == result['actual_joint_count']
            final_joints = dict(zip(data['joint_names'].tolist(), data['joint_positions'][-1].tolist(), strict=True))
        commanded = request['configuration'][hand]['close_joints']
        direct_errors = {name: abs(final_joints[name] - target) for name, target in commanded.items()
                         if name in mapping['configured_control_joints']}
        tendon_errors = {}
        for name in mapping['tendon_coordinates']:
            prefix = name[:-1]
            tendon_errors[name] = abs(final_joints[prefix + '1'] + final_joints[prefix + '2']
                                      - commanded[prefix + '1'] - commanded[prefix + '2'])
        phases = ('settle', 'approach', 'descend', 'close', 'lift', 'hold')
        frames = []
        for phase in phases:
            path = run / f'{phase}.png'
            frame = Image.open(path).convert('RGB')
            frame.thumbnail((960, 540))
            draw = ImageDraw.Draw(frame)
            draw.rectangle((0, 0, frame.width, 28), fill='black')
            draw.text((10, 7), f'{hand.upper()} | {phase} | phase snapshots, NOT continuous video', fill='white')
            frames.append(frame)
        gif = run / 'phase_storyboard.gif'
        frames[0].save(gif, save_all=True, append_images=frames[1:], duration=1200, loop=0)
        images = {phase: str(run / f'{phase}.png') for phase in phases}
        entries[hand] = {'run_directory': str(run), 'result': result,
            'physics_steps': result['steps_completed'] * request['specification']['scene']['decimation'],
            'trajectory_verified': True, 'frames_verified': result['steps_completed'] + 1,
            'images': images, 'phase_storyboard': str(gif), 'request': str(run / 'request.json'),
            'script_sha256': sha256_file(run / 'script_snapshot.py') if (run / 'script_snapshot.py').exists() else None}
        loaded_root = Path(result['robot_usd_path'])
        entries[hand]['loaded_root_usd'] = {'path': str(loaded_root), 'exists': loaded_root.is_file(),
            'sha256': sha256_file(loaded_root), 'scope': 'root USD only, not the complete dependency tree'}
        entries[hand]['final_tracking'] = {'direct_joint_error_rad': direct_errors, 'tendon_sum_error_rad': tendon_errors,
            'max_direct_joint_error_rad': max(direct_errors.values()),
            'max_tendon_sum_error_rad': max(tendon_errors.values()) if tendon_errors else None,
            'note': 'Shadow J1/J2 pairs are tendon-driven; do not claim their individual angles are independently controlled'}
        t = np.array([row['step'] for row in metrics]) / 30
        axes[0].plot(t, np.array([row['object_lift_m'] for row in metrics]) * 1000, label=hand)
        axes[1].plot(t, [row['max_tip_normal_force_n'] for row in metrics], label=hand)
        axes[2].plot(t, [row['active_tip_count'] for row in metrics], label=hand)
    axes[0].axhline(30, linestyle='--', color='black', label='lift threshold: 30 mm')
    axes[0].set_ylabel('Cube rise from\ninitial pose [mm]')
    axes[1].set_ylabel('Peak tip normal\nforce per sample [N]')
    axes[2].set_ylabel('Active tip filters')
    axes[2].set_xlabel('Simulated time [s]')
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(loc='upper right')
    bounds = [15, 165, 255, 345, 435, 480]
    start = 0
    for phase, end in zip(phases, bounds):
        axes[0].text((start + end) / 60, 25, phase, ha='center', fontsize=8)
        for ax in axes:
            ax.axvline(end / 30, color='gray', alpha=0.3, linewidth=0.6)
        start = end
    fig.suptitle('Real scripted tabletop attempts: Allegro + KUKA vs prescribed-base Shadow\nBoth failed the final lift-and-hold criterion; not a success-rate benchmark')
    fig.tight_layout()
    fig.savefig(directory / 'first_grasp_metrics.png', dpi=160)
    plt.close(fig)
    attempts = []
    for path in sorted((ROOT / 'outputs').glob('*first-grasp-*/request.json')):
        run = path.parent
        request = json.loads(path.read_text())
        result_path = run / 'result.json'
        result = json.loads(result_path.read_text()) if result_path.exists() else None
        attempts.append({'run_directory': str(run), 'hand': request['hand'], 'probe': request['probe'],
                         'simulation_completed': result.get('simulation_completed') if result else False,
                         'grasp_success': result.get('grasp_success') if result else None,
                         'steps': result.get('steps_completed') if result else None,
                         'error': result.get('error') if result else 'No completion evidence; see launch result/log'})
    save_json(directory / 'first_grasp_results.json', {'final_comparison': entries, 'all_runs_including_debug': attempts,
             'scope': 'One final trial per hand with prior debug attempts retained; do not infer population success rates'})
    print(json.dumps({hand: {k: row['result'][k] for k in ('grasp_success', 'max_lift_m', 'max_tip_force_n',
                 'peak_active_tip_count', 'collision_penetration')} for hand, row in entries.items()}, indent=2))


if __name__ == '__main__':
    main()
