"""Validate and combine two actual simulation recordings without inventing frames."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np


def inspect_run(directory):
    result = json.loads((directory / 'result.json').read_text())
    frames = json.loads((directory / 'video_frames.json').read_text())['frames']
    assert result['simulation_completed'] and result['steps_completed'] == 480
    assert len(frames) == 240 and [f['step'] for f in frames] == list(range(2, 481, 2))
    with np.load(directory / 'trajectory/trajectory.npz', allow_pickle=False) as trajectory:
        positions = trajectory['joint_positions']
        assert positions.shape == (481, result['actual_joint_count'])
        assert np.isfinite(positions).all()
        motion = np.ptp(positions, axis=0)
        moving = [str(name) for name, extent in zip(trajectory['joint_names'], motion, strict=True) if extent > 0.01]
        assert moving, 'No measured joint motion'
        assert np.isfinite(trajectory['object_pose']).all()
    hashes = {hashlib.sha256(path.read_bytes()).hexdigest() for path in (directory / 'video_frames').glob('*.png')}
    assert len(hashes) > 30, 'Recording appears static'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                                               '-of', 'json', str(directory / 'motion.mp4')]))
    stream = probe['streams'][0]
    assert stream['nb_frames'] == '240' and stream['r_frame_rate'] == '15/1'
    assert abs(float(probe['format']['duration']) - 16) < 0.01
    return {'run_directory': str(directory), 'result': result, 'frame_count': len(frames),
            'unique_source_frames': len(hashes), 'moving_joints': moving,
            'max_joint_excursion_rad': float(motion.max()), 'video_probe': probe,
            'video_sha256': hashlib.sha256((directory / 'motion.mp4').read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allegro', type=Path, required=True)
    parser.add_argument('--shadow', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    records = {hand: inspect_run(getattr(args, hand).resolve()) for hand in ('allegro', 'shadow')}
    args.output.mkdir(parents=True, exist_ok=False)
    commands = []
    for hand in records:
        directory = Path(records[hand]['run_directory'])
        shutil.copyfile(directory / 'motion.mp4', args.output / f'{hand}.mp4')
    font = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    graph = (
        '[0:v]pad=960:640:0:60:color=0x11243b,'
        f"drawtext=fontfile={font}:text='ALLEGRO + KUKA':x=24:y=15:fontsize=26:fontcolor=white,"
        f"drawtext=fontfile={font}:text='7 arm + 16 hand joints | DLS arm control':x=24:y=608:fontsize=18:fontcolor=white[left];"
        '[1:v]pad=960:640:0:60:color=0x11243b,'
        f"drawtext=fontfile={font}:text='SHADOW HAND':x=24:y=15:fontsize=26:fontcolor=white,"
        f"drawtext=fontfile={font}:text='24 joints / 20 actions | prescribed base path':x=24:y=608:fontsize=18:fontcolor=white[right];"
        '[left][right]hstack=inputs=2,pad=1920:690:0:0:color=0x11243b,'
        f"drawtext=fontfile={font}:text='Actual PhysX simulation | 1x simulation time | Both trials failed lift-and-hold':x=24:y=653:fontsize=22:fontcolor=0xbad8f5[out]"
    )
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(args.output/'allegro.mp4'),
               '-i', str(args.output/'shadow.mp4'), '-filter_complex', graph, '-map', '[out]',
               '-c:v', 'libx264', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
               str(args.output/'comparison.mp4')]
    assert all(not record['result']['grasp_success'] for record in records.values()), 'Update outcome overlay for changed results'
    subprocess.run(command, check=True, timeout=90)
    commands.append(command)
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(args.output/'comparison.mp4'),
               '-filter_complex', 'fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
               '-loop', '0', str(args.output/'preview.gif')]
    subprocess.run(command, check=True, timeout=90)
    commands.append(command)
    (args.output/'evidence.json').write_text(json.dumps({'runs': records, 'encoding_commands': commands,
        'scope': 'Two actual simulated motion trials, not successful grasps or a fair hardware ranking.',
        'source_timing': 'Every two environment steps at 1/30s, encoded at 15fps; GIF preview subsampled to 10fps.'}, indent=2)+'\n')
    print(args.output/'comparison.mp4')


if __name__ == '__main__':
    main()
