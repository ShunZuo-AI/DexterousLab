"""Build the README overview from real experiment frames and editable SVG."""

import base64
from html import escape
import json
from pathlib import Path
import subprocess
import tempfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs/media'
RUNS = {
    'allegro': '20261106T122416Z-first-grasp-allegro-b8586ceb',
    'shadow': '20261106T122645Z-first-grasp-shadow-863d5980',
}


def build():
    MEDIA.mkdir(parents=True, exist_ok=True)
    sources = {}
    for hand, run in RUNS.items():
        source = ROOT / 'outputs' / run / 'close.png'
        target = MEDIA / f'{hand}-tabletop.jpg'
        with Image.open(source) as frame:
            frame.convert('RGB').save(target, quality=92, optimize=True)
        sources[hand] = {
            'source': str(source.relative_to(ROOT)),
            'published': str(target.relative_to(ROOT)),
            'phase': 'close',
            'grasp_success': False,
        }

    parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1100" viewBox="0 0 1600 1100">
<defs>
 <linearGradient id="bg" x2="1" y2="1"><stop stop-color="#080f1e"/><stop offset="1" stop-color="#142237"/></linearGradient>
 <radialGradient id="glow"><stop stop-color="#156e83" stop-opacity=".23"/><stop offset="1" stop-color="#156e83" stop-opacity="0"/></radialGradient>
 <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#a6c7dd" stroke-opacity=".045"/></pattern>
 <linearGradient id="line"><stop stop-color="#5de4cc"/><stop offset="1" stop-color="#8d9eff"/></linearGradient>
 <clipPath id="left"><rect x="72" y="296" width="716" height="284" rx="16"/></clipPath>
 <clipPath id="right"><rect x="812" y="296" width="716" height="284" rx="16"/></clipPath>
</defs>
<rect width="1600" height="1100" fill="url(#bg)"/>
<rect width="1600" height="1100" fill="url(#grid)"/>
<ellipse cx="1270" cy="140" rx="650" ry="500" fill="url(#glow)"/>
<rect x="72" y="52" width="32" height="4" rx="2" fill="#5de4cc"/>
''']

    def text(x, y, value, size=20, color='#e8f0fa', weight=400, mono=False):
        family = 'DejaVu Sans Mono, monospace' if mono else 'DejaVu Sans, sans-serif'
        parts.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="{family}" font-size="{size}" font-weight="{weight}">{escape(value)}</text>')

    def panel(x, y, w, h, stroke='#30435b', fill='#142236', dashed=False):
        dash = ' stroke-dasharray="7 6"' if dashed else ''
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{fill}" stroke="{stroke}"{dash}/>')

    text(120, 61, 'DEXTEROUS MANIPULATION / RESEARCH INFRASTRUCTURE', 15, '#91a9c4', mono=True)
    text(72, 165, 'DexterousLab', 88, weight=700)
    text(76, 211, 'Configurable hands. Composable scenes. Traceable experiments.', 25, '#aebfd3')
    for x, w, title in [(76, 225, 'MULTI-HAND ASSETS'), (315, 234, 'TABLETOP SIMULATION'), (563, 245, 'EXPERIMENT EVIDENCE')]:
        panel(x, 240, w, 32, '#2b4d61', '#102a36')
        text(x + 15, 261, title, 13, '#8cead9', 600, mono=True)
    text(1112, 263, 'REAL ISAAC SIM FRAMES', 14, '#91a9c4', mono=True)

    for hand, x, clip, label, subtitle in [
        ('allegro', 72, 'left', 'ALLEGRO + KUKA', '23 joints / 23 actions'),
        ('shadow', 812, 'right', 'SHADOW HAND', '24 joints / 20 actions'),
    ]:
        encoded = base64.b64encode((MEDIA / f'{hand}-tabletop.jpg').read_bytes()).decode()
        parts.append(f'<image x="{x}" y="296" width="716" height="284" preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip})" href="data:image/jpeg;base64,{encoded}"/>')
        panel(x, 555, 716, 63, '#30435b', '#142236')
        text(x + 22, 593, label, 19, weight=700)
        text(x + 363, 591, subtitle, 16, '#afc2da', mono=True)

    text(72, 665, 'FROM CONFIGURATION TO MEASURED RESULTS', 15, '#91a9c4', mono=True)
    cards = [
        (72, '01', 'ASSET & CONFIG', '#5de4cc', ['HandRegistry / ObjectRegistry', 'Hands + geometry + physics', 'Cube / Cylinder / Sphere']),
        (568, '02', 'BUILD & SIMULATE', '#91adff', ['SceneBuilder + ArenaEnvBuilder', 'Tabletop + embodiment + task', 'Isaac Lab / PhysX']),
        (1064, '03', 'RECORD & EVALUATE', '#e5bd88', ['Joints / poses / tip contacts', 'JSONL + numeric NPZ + frames', 'Explicit lift-and-hold criteria']),
    ]
    for x, number, title, accent, lines in cards:
        panel(x, 691, 464, 172)
        text(x + 22, 728, number, 16, accent, mono=True)
        text(x + 65, 728, title, 19, weight=700)
        for i, line in enumerate(lines):
            text(x + 22, 767 + i * 30, line, 18, '#aebfd3')
    for x in [544, 1040]:
        parts.append(f'<path d="M{x} 775h16m-6 -6 6 6-6 6" stroke="#7899ba" stroke-width="2" fill="none"/>')

    panel(72, 892, 1456, 105, '#456076', '#101c2d', dashed=True)
    text(95, 927, 'RESEARCH EXTENSIONS', 15, '#91a9c4', mono=True)
    text(95, 965, 'GraspCandidate  /  Generator  /  Validator  /  DatasetWriter', 24)
    text(1112, 927, 'PARTIAL / INTERFACES', 14, '#e5bd88', mono=True)
    text(1112, 963, 'Not an end-to-end generator', 17, '#afc2da')
    parts.append('<path d="M72 1026H1528" stroke="url(#line)" stroke-opacity=".5"/>')
    text(72, 1064, 'NVIDIA ISAAC SIM  /  ISAAC LAB  /  ISAACLAB-ARENA', 16, '#afc2da', mono=True)
    text(1005, 1064, 'Physics rollout ≠ successful grasp', 18, '#e5bd88')
    parts.append('</svg>')
    svg = MEDIA / 'dexterouslab-overview.svg'
    svg.write_text('\n'.join(parts))
    # Headless browser rasterizes the editable diagram; it does not start Isaac Sim.
    with tempfile.TemporaryDirectory(prefix='dexlab-readme-', dir=ROOT / '.cache') as profile:
        subprocess.run([
            '/usr/bin/google-chrome', '--headless', '--no-sandbox', '--disable-gpu',
            '--hide-scrollbars', '--force-device-scale-factor=1',
            f'--user-data-dir={profile}', '--window-size=1600,1100',
            f'--screenshot={MEDIA / "dexterouslab-overview.png"}', svg.as_uri(),
        ], check=True, capture_output=True, timeout=60)
    with Image.open(MEDIA / 'dexterouslab-overview.png') as image:
        image.save(MEDIA / 'dexterouslab-overview.png', optimize=True)
    (MEDIA / 'provenance.json').write_text(json.dumps({
        'generator': 'scripts/build_readme_visuals.py',
        'overview': 'Editable SVG, rasterized with Chrome; no generated simulation imagery.',
        'screenshots': sources,
        'notice': 'Frames show the close phase of failed grasp attempts, not successful lifts.',
    }, indent=2) + '\n')


if __name__ == '__main__':
    build()
