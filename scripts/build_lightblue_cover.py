"""Render the white / pale-blue cover with bright, detailed hand materials."""

import json
from pathlib import Path

from build_constellation_cover import kinetic_cover
from build_hand_gallery import MEDIA, ROOT
from build_readme_cover import studio_render


def main():
    previous = json.loads((MEDIA / 'universe-provenance.json').read_text())
    entries = previous['assets']
    directory = MEDIA / 'lightblue-hands'
    directory.mkdir(exist_ok=True)
    for entry in entries:
        target = directory / Path(entry['studio_render']).name
        studio_render(entry, target, bright=True)
        entry['studio_render'] = str(target.relative_to(ROOT))
        print('BRIGHT_RENDER', entry['asset_id'], flush=True)
    kinetic_cover(entries, light=True)
    (MEDIA / 'lightblue-provenance.json').write_text(json.dumps({
        'generator': 'scripts/build_lightblue_cover.py',
        'active_cover': 'docs/media/dexterouslab-lightblue.png',
        'design': 'White with pale-blue atmosphere; 22 real USD configurations in a spatial composition.',
        'materials': 'Pearl-blue ceramic shells, satin blue alloy mechanical parts and graphite fingertip pads; display materials only.',
        'rendering': '1200px source renders, consistent mesh normals, Phong soft studio shading, transparent alpha; no washed-out blue post-tint.',
        'scope': 'Decorative model illustration, not a physics run or grasp result. Original meshes and assets are unchanged.',
        'hand_configurations': len(entries),
        'manufacturers': len({e['asset_id'].split('/')[0] for e in entries}),
        'assets': entries,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
