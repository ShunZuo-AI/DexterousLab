"""Compose all validated hand configurations into a single spatial cover artwork."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_hand_gallery import MEDIA, ROOT, meshes
from build_readme_cover import studio_render


W, H = 2800, 1760
REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'


def label(canvas, xy, value, size, fill, face=REGULAR, anchor='mm'):
    ImageDraw.Draw(canvas).text(xy, value, fill=fill,
        font=ImageFont.truetype(face, size), anchor=anchor)


def sources():
    records = json.loads((ROOT / 'assets/manifests/hands.json').read_text())['hands']
    entries = json.loads((MEDIA / 'cover-provenance.json').read_text())['assets']
    by_id = {e['asset_id']: e for e in entries}
    for record in records:
        if record['simulation_status'] != 'passed' or record['asset_id'] in by_id:
            continue
        source = Path(record['isaaclab_asset_path'])
        geometry = meshes(source)
        cloud = np.concatenate([m[1] for m in geometry])
        order = np.argsort(np.ptp(cloud, axis=0))
        axes = [int(order[1]), int(order[0]), int(order[2])]
        entry = {
            'asset_id': record['asset_id'],
            'title': record['model'] + ' / ' + record['variant'],
            'manufacturer': record['manufacturer'],
            'source_usd': str(source.relative_to(ROOT)),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_repository': record.get('source_repository'),
            'source_commit': record.get('source_commit'),
            'license': record.get('license'),
            'display_axes': axes, 'vertical_sign': 1,
            'image_rotation_degrees': 180 if record['asset_id'].startswith('wuji/') else 0,
        }
        target = MEDIA / 'studio-hands' / (record['asset_id'].replace('/', '--') + '.png')
        if not target.exists():
            studio_render(entry, target)
        entry['studio_render'] = str(target.relative_to(ROOT))
        by_id[record['asset_id']] = entry
        print('RENDERED_EXTRA', entry['asset_id'], flush=True)
    assert len(by_id) == 22
    assert set(by_id) == {r['asset_id'] for r in records if r['simulation_status'] == 'passed'}
    # Interleave mechanical silhouettes, anthropomorphic hands and manufacturers.
    order = [0, 6, 2, 18, 8, 4, 10, 12, 7, 19, 14, 16, 11, 17, 1, 13, 20, 9, 15, 5, 21, 3]
    all_entries = list(by_id.values())
    return [all_entries[i] for i in order]


def glow(canvas, point, radius, rgb, opacity):
    layer = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(layer)
    x, y = point
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=(*rgb, opacity))
    canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius * .55)))


def object_core(canvas):
    """Draw a geometric object motif; decorative, not a simulation result."""
    cx, cy, s = W/2, 620, 100
    glow(canvas, (cx, cy), 170, (67, 104, 253), 110)
    points = [(cx, cy-s), (cx+s, cy-s*.42), (cx+s, cy+s*.62),
              (cx, cy+s*1.18), (cx-s, cy+s*.62), (cx-s, cy-s*.42), (cx, cy+s*.14)]
    glass = Image.new('RGBA', canvas.size)
    d = ImageDraw.Draw(glass)
    d.polygon([points[i] for i in [0,1,6,5]], fill=(136, 177, 255, 70))
    d.polygon([points[i] for i in [1,2,3,6]], fill=(88, 125, 242, 58))
    d.polygon([points[i] for i in [5,6,3,4]], fill=(90, 194, 230, 32))
    for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(5,6),(1,6),(6,3)]:
        d.line([points[a],points[b]], fill=(169, 204, 255, 205), width=2)
    canvas.alpha_composite(glass)


def kinetic_cover(entries, light=False):
    """Use asymmetric depth layers and converging gestures, rather than a catalog."""
    yy, xx = np.mgrid[0:1600, 0:2800]
    field = np.exp(-(((xx-1920)/950)**2+((yy-720)/1000)**2)*1.6)
    color = (np.stack([253-field*24, 254-field*13, 255-field*3],axis=-1) if light else
             np.stack([8+field*12, 11+field*22, 18+field*49],axis=-1)).astype(np.uint8)
    canvas = Image.fromarray(color).convert('RGBA')
    glow(canvas,(1960,760),420,(173,211,250) if light else (55,99,207),45 if light else 75)
    glow(canvas,(2430,1060),480,(209,234,255) if light else (99,80,139),35 if light else 28)
    # A single flowing gesture through the scene establishes a shared space.
    lines = Image.new('RGBA',canvas.size)
    d = ImageDraw.Draw(lines)
    for offset in [0,35,80]:
        curve=[]
        for t in np.linspace(0,1,500):
            x=1080+1480*t
            y=1340-1080*math.sin(t*math.pi*.85)+offset
            curve.append((x,y))
        d.line(curve,fill=(126,171,222,40 if light else 22),width=2)
    canvas.alpha_composite(lines)
    # cx, cy, maximum height, in-plane rotation, depth (0=far, 1=near).
    placements=[
        (1550,240,200,25,.16),(1890,200,190,-10,.12),
        (2240,270,210,-45,.18),(2540,470,230,-65,.24),
        (1280,430,200,45,.18),(1470,615,225,60,.22),
        (2240,570,250,-60,.3),(2530,790,220,-75,.25),
        (1640,450,270,35,.38),(1960,400,260,-20,.4),
        (2380,1010,300,-75,.44),(1280,900,270,70,.4),
        (1440,1115,300,45,.48),(1780,1115,285,20,.42),
        (2110,1210,340,-30,.58),(2600,1240,290,-50,.48),
        (1170,1260,440,48,.95),(1660,1280,470,18,1),
        (2250,1350,390,-25,.96),(2550,1010,400,-80,.9),
        (1090,640,360,65,.78),(2600,230,320,-135,.65),
    ]
    # Put distinctive, readable hands in the foreground; every entry appears once.
    priorities=['wonik/allegro/isaaclab_standalone',
                'shadow_robot/dexterous_hand/right_isaaclab',
                'wuji/hand_v2/2_2_right',
                'orca/orca_hand/v1_models_urdf_orcahand_right',
                'leap/leap_hand_v1/right',
                'sharpa/sharpa_wave_wave_01/right_sharpa_wave_right_sharpa_wave']
    indexed={e['asset_id']:e for e in entries}
    ordered=[e for e in entries if e['asset_id'] not in priorities]+[indexed[k] for k in priorities]
    for entry,(cx,cy,height,rotation,depth) in zip(ordered,placements):
        frame=Image.open(ROOT/entry['studio_render']).convert('RGBA')
        arr=np.asarray(frame).astype(float)
        alpha=arr[:,:,3].copy()
        if not light:
            arr[:,:,:3]=np.clip((arr[:,:,:3]/255)**.78*255*np.array([.88,.96,1.12])+[9,13,20],0,255)
        arr[:,:,3]=alpha*((.85+.15*depth) if light else (.55+.45*depth))
        frame=Image.fromarray(arr.astype(np.uint8))
        frame.thumbnail((int(height*.78),height),Image.Resampling.LANCZOS)
        frame=frame.rotate(rotation,Image.Resampling.BICUBIC,expand=True)
        layer=Image.new('RGBA',canvas.size)
        layer.alpha_composite(frame,(int(cx-frame.width/2),int(cy-frame.height/2)))
        if depth<.3 and not light:
            layer=layer.filter(ImageFilter.GaussianBlur(.6))
        rim=Image.new('RGBA',canvas.size,(66,102,153,0) if light else (79,133,247,0))
        rim.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(14 if light else 17)).point(lambda v:int(v*(.15 if light else .27))))
        canvas.alpha_composite(rim)
        canvas.alpha_composite(layer)
        entry['kinetic_placement']={'center_px':[cx,cy],'max_height_px':height,
                                    'rotation_degrees':rotation,'depth_fraction':depth}
    # A luminous object is the common visual focus of the converging hands.
    cx,cy,s=1890,800,140
    glow(canvas,(cx,cy),170,(155,202,255) if light else (78,121,255),65 if light else 105)
    cube=Image.new('RGBA',canvas.size)
    d=ImageDraw.Draw(cube)
    vertices=[(cx,cy-s),(cx+s,cy-s*.42),(cx+s,cy+s*.62),
              (cx,cy+s*1.18),(cx-s,cy+s*.62),(cx-s,cy-s*.42),(cx,cy+s*.14)]
    faces = ([([0,1,6,5],(228,241,255,220)),([1,2,3,6],(142,192,246,185)),([5,6,3,4],(188,223,255,180))] if light else
             [([0,1,6,5],(147,187,255,96)),([1,2,3,6],(80,125,236,90)),([5,6,3,4],(76,179,242,65))])
    for ids,rgba in faces:
        d.polygon([vertices[i] for i in ids],fill=rgba)
    for a,b in [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(5,6),(1,6),(6,3)]:
        d.line([vertices[a],vertices[b]],fill=(97,156,220,180) if light else (167,204,255,220),width=2)
    canvas.alpha_composite(cube)
    ink = '#17304e' if light else '#f1f2f7'
    muted = '#6883a1' if light else '#8c9dbb'
    label(canvas,(134,112),'DEXTEROUSLAB / RESEARCH',20,muted,MONO,'lm')
    label(canvas,(126,440),'Dexterous',154,ink,BOLD,'lm')
    label(canvas,(126,608),'Lab.',185,ink,BOLD,'lm')
    label(canvas,(138,767),'Many hands.',40,'#597591' if light else '#b8c8e1',REGULAR,'lm')
    label(canvas,(138,824),'One world of interaction.',40,'#597591' if light else '#b8c8e1',REGULAR,'lm')
    d=ImageDraw.Draw(canvas)
    d.line((140,939,228,939),fill='#728db9',width=3)
    label(canvas,(138,1015),'22',82,ink if light else '#e2e9f5',REGULAR,'lm')
    label(canvas,(270,1003),'HAND CONFIGURATIONS',18,muted,MONO,'lm')
    label(canvas,(270,1037),'17 MANUFACTURERS',18,muted,MONO,'lm')
    label(canvas,(138,1443),'ASSETS / SIMULATION / GRASP RESEARCH',17,muted,MONO,'lm')
    label(canvas,(2660,1517),'ISAAC SIM + ISAAC LAB + ARENA',18,muted,MONO,'rm')
    canvas.convert('RGB').save(MEDIA/('dexterouslab-lightblue.png' if light else 'dexterouslab-kinetic.png'),optimize=True)


def main():
    entries = sources()
    yy, xx = np.mgrid[0:H, 0:W]
    # Charcoal / indigo atmosphere, lit in the middle rather than a flat poster.
    field = np.exp(-(((xx-W*.50)/(W*.43))**2 + ((yy-H*.48)/(H*.60))**2)*2)
    rgb = np.stack([8+field*12, 10+field*18, 17+field*40], axis=-1).astype(np.uint8)
    canvas = Image.fromarray(rgb).convert('RGBA')
    glow(canvas, (W*.69, H*.31), 650, (59, 77, 151), 38)
    glow(canvas, (W*.24, H*.68), 550, (100, 75, 122), 26)

    # Broken orbit paths and an inclined plane connect the composition visually.
    paths = Image.new('RGBA', canvas.size)
    d = ImageDraw.Draw(paths)
    center = np.array([W*.5, H*.51])
    for k, (rx, ry) in enumerate([(1080,585),(1115,620),(1000,530)]):
        curve = []
        for angle in np.linspace(-2.3+k*.25, 3.4-k*.2, 550):
            x = rx*math.cos(angle)
            y = ry*math.sin(angle)
            curve.append((center[0]+x, center[1]+y+x*.055))
        d.line(curve, fill=(142,163,219,35-k*7), width=2)
    canvas.alpha_composite(paths)

    layout = []
    for i, entry in enumerate(entries):
        theta = 2*math.pi*i/len(entries) + .10
        front = (math.sin(theta)+1)/2
        radius = 1 + .045*math.sin(i*2.41)
        x = center[0] + 1100*radius*math.cos(theta)
        y = center[1] + 600*radius*math.sin(theta) + 45*math.cos(theta)
        height = 240+front*165 + 28*math.sin(i*1.9)
        width = 195+front*75
        rotation = 90-math.degrees(theta) + 14*math.sin(i*1.7)
        frame = Image.open(ROOT / entry['studio_render']).convert('RGBA')
        # Preserve the rendered shading while giving the scene a cool studio grade.
        arr = np.asarray(frame).astype(float)
        a = arr[:,:,3].copy()
        arr[:,:,:3] = np.clip((arr[:,:,:3]/255)**.8*255*np.array([.92,.98,1.08])+np.array([10,13,19]),0,255)
        arr[:,:,3] = a
        frame = Image.fromarray(arr.astype(np.uint8))
        frame.thumbnail((int(width),int(height)),Image.Resampling.LANCZOS)
        frame = frame.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
        layout.append((front, frame, x, y, entry, rotation))
    for front, frame, x, y, entry, rotation in sorted(layout, key=lambda item:item[0]):
        layer = Image.new('RGBA', canvas.size)
        px, py = int(x-frame.width/2), int(y-frame.height/2)
        layer.alpha_composite(frame, (px,py))
        rim = Image.new('RGBA', canvas.size, (88,135,255,0))
        rim.putalpha(layer.getchannel('A').filter(ImageFilter.GaussianBlur(13)).point(lambda v:int(v*.24)))
        canvas.alpha_composite(rim)
        if front < .16:
            layer = layer.filter(ImageFilter.GaussianBlur(.5))
        canvas.alpha_composite(layer)
        entry['cover_placement'] = {'center_px':[round(x,2),round(y,2)], 'rotation_degrees':round(rotation,2),
                                   'depth_fraction':round(front,3),'projected_size_px':list(frame.size)}

    # Quiet central negative space lets the hand constellation be the illustration.
    object_core(canvas)
    label(canvas, (W/2, 813), 'DexterousLab', 165, '#f0f2fa', BOLD)
    label(canvas, (W/2, 955), 'A universe of hands. A shared world of interaction.', 32, '#a8b4ce')
    label(canvas, (W/2, 1033), 'ASSETS   /   SIMULATION   /   GRASP RESEARCH', 19, '#8799bc', MONO)
    label(canvas, (105, 95), 'DEXTEROUS MANIPULATION', 20, '#8e9db9', MONO, 'lm')
    label(canvas, (W-105,95), 'RESEARCH PLATFORM  /  01', 19, '#8e9db9', MONO, 'rm')
    label(canvas, (105,H-90), '22 HAND CONFIGURATIONS', 24, '#b7c6e1', MONO, 'lm')
    label(canvas, (W-105,H-90), 'ISAAC SIM  /  ISAAC LAB  /  ARENA', 19, '#8e9db9', MONO, 'rm')
    target = MEDIA / 'dexterouslab-universe.png'
    canvas.convert('RGB').save(target, optimize=True)
    kinetic_cover(entries)
    (MEDIA / 'universe-provenance.json').write_text(json.dumps({
        'generator':'scripts/build_constellation_cover.py',
        'active_cover':'docs/media/dexterouslab-kinetic.png',
        'alternate_composition':'docs/media/dexterouslab-universe.png',
        'design':'22 actual hand configurations in an asymmetric, depth-graded composition converging on a conceptual object.',
        'scope':'Artwork from real USD geometry. Separate visual layout, neutral display materials and decorative cube; no simulated grasp is depicted.',
        'hand_configurations':len(entries),
        'manufacturers':len({e['asset_id'].split('/')[0] for e in entries}),
        'assets':entries,
    },indent=2)+'\n')
    print('COVER_CREATED',target,flush=True)


if __name__ == '__main__':
    main()
