"""Create an editorial README cover using real USD geometry and studio lighting."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from build_hand_gallery import MEDIA, ROOT, meshes


REGULAR = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
BOLD = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
HERO = [0, 1, 2, 5, 11, 17]


def studio_render(entry, target, bright=False):
    """Render the actual geometry with neutral materials onto a transparent film."""
    geometry = meshes(ROOT / entry['source_usd'])
    cloud = np.concatenate([m[1] for m in geometry])
    center = (cloud.min(axis=0) + cloud.max(axis=0)) / 2
    axes = entry['display_axes']
    sign = entry['vertical_sign']
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.94, .93, .91)
    renderer.SetBackgroundAlpha(0)
    renderer.AutomaticLightCreationOff()
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetAlphaBitPlanes(1)
    window.SetMultiSamples(8)
    window.SetSize(1200 if bright else 800, 1200 if bright else 800)
    window.AddRenderer(renderer)
    pale = entry['asset_id'].split('/')[0] in ('shadow_robot', 'wuji', 'psyonic', 'sharpa', 'brainco', 'robotera')
    for index, (name, points, counts, indices) in enumerate(geometry):
        vertices = np.ascontiguousarray((points - center)[:, axes])
        vertices[:, 2] *= sign
        vtk_points = vtk.vtkPoints()
        vtk_points.SetData(numpy_to_vtk(vertices, deep=True))
        cells = vtk.vtkCellArray()
        offsets = np.concatenate([[0], np.cumsum(counts)]).astype(np.int64)
        cells.SetData(numpy_to_vtk(offsets, deep=True, array_type=vtk.VTK_ID_TYPE),
                      numpy_to_vtk(indices, deep=True, array_type=vtk.VTK_ID_TYPE))
        data = vtk.vtkPolyData()
        data.SetPoints(vtk_points)
        data.SetPolys(cells)
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(data)
        normals.SetFeatureAngle(65 if bright else 50)
        normals.ConsistencyOn()
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        tip = any(t in name.lower() for t in ('distal', 'tip', 'link_3', 'link3'))
        if pale:
            color = (.22, .24, .26) if tip else (.74, .73, .70)
        else:
            gray = .23 + (index % 3) * .045
            color = (.43, .46, .49) if tip else (gray * .90, gray * .96, gray)
        if bright:
            joint = any(t in name.lower() for t in ('knuckle', 'joint', 'motor', 'bearing'))
            if tip:
                color = (.24, .35, .49)
            elif joint:
                color = (.39, .49, .61)
            elif pale:
                color = (.78, .84, .91)
            else:
                color = (.47, .60, .75)
            prop.SetColor(*color)
            prop.SetInterpolationToPhong()
            prop.SetAmbient(.32)
            prop.SetDiffuse(.68)
            prop.SetSpecular(.42)
            prop.SetSpecularPower(48)
        else:
            prop.SetColor(*color)
            prop.SetInterpolationToPBR()
            prop.SetMetallic(.30 if pale else .65)
            prop.SetRoughness(.32 if pale else .28)
            prop.SetAmbient(.12)
        renderer.AddActor(actor)
    for position, power, color in [
        ((-1, -2, 2.5), 1.4, (1, .95, .87)),
        ((1.5, -1, .7), .85, (.82, .89, 1)),
        ((.3, 1.5, 2), 1.8, (1, 1, 1)),
    ]:
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(0, 0, 0)
        light.SetIntensity(power * .65 if bright else power)
        light.SetColor(*((.94, .97, 1) if bright else color))
        renderer.AddLight(light)
    camera = renderer.GetActiveCamera()
    camera.SetPosition(*((.85, -1, .25) if entry['asset_id'].startswith('barrett/') else (.27, -1, .12)))
    camera.SetFocalPoint(0, 0, 0)
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    renderer.ResetCamera()
    camera.Zoom(1.04)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.SetInputBufferTypeToRGBA()
    capture.ReadFrontBufferOff()
    capture.Update()
    output = capture.GetOutput()
    w, h, _ = output.GetDimensions()
    pixels = vtk_to_numpy(output.GetPointData().GetScalars()).reshape(h, w, 4)
    frame = Image.fromarray(np.flipud(pixels), 'RGBA')
    angle = entry.get('image_rotation_degrees', 0)
    frame = frame.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    bounds = frame.getchannel('A').getbbox()
    if bounds is None:
        raise RuntimeError(f'Empty image: {entry["asset_id"]}')
    frame.crop(bounds).save(target, optimize=True)
    window.Finalize()


def text(image, xy, value, size, color='#202421', font=REGULAR, anchor=None):
    ImageDraw.Draw(image).text(xy, value, font=ImageFont.truetype(font, size), fill=color, anchor=anchor)


def tracked(image, xy, value, size=19, spacing=4, color='#69736d'):
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(REGULAR, size)
    x, y = xy
    for ch in value:
        draw.text((x, y), ch, font=font, fill=color)
        x += draw.textlength(ch, font=font) + spacing


def background(size):
    w, h = size
    image = Image.new('RGBA', size, '#f5f4ef')
    # Broad, low-contrast pools of light, rather than boxes around each model.
    glow = Image.new('RGBA', size)
    d = ImageDraw.Draw(glow)
    d.ellipse((w*.48, h*.25, w*.98, h*.85), fill=(204, 214, 222, 75))
    d.ellipse((-w*.1, h*.40, w*.50, h*.95), fill=(226, 213, 193, 65))
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(180)))
    return image


def place_hand(image, frame, center_x, bottom, width, height, opacity=255):
    frame = frame.copy()
    frame.thumbnail((width, height), Image.Resampling.LANCZOS)
    x = int(center_x - frame.width/2)
    y = int(bottom - frame.height)
    shadow = Image.new('RGBA', image.size)
    draw = ImageDraw.Draw(shadow)
    sw = min(frame.width*.68, width*.55)
    draw.ellipse((center_x-sw/2, bottom-7, center_x+sw/2, bottom+13), fill=(35, 40, 37, opacity//5))
    image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(15)))
    image.alpha_composite(frame, (x, y))


def main():
    entries = json.loads((MEDIA / 'hand-gallery-provenance.json').read_text())['assets']
    directory = MEDIA / 'studio-hands'
    directory.mkdir(exist_ok=True)
    for entry in entries:
        path = directory / Path(entry['render']).name
        studio_render(entry, path)
        entry['studio_render'] = str(path.relative_to(ROOT))
        print('STUDIO_RENDER', entry['title'], flush=True)

    cover = background((2400, 1370))
    tracked(cover, (102, 66), 'DEXTEROUS SYSTEMS / OPEN RESEARCH', size=20, spacing=4)
    text(cover, (96, 129), 'DexterousLab', 170, font=BOLD)
    text(cover, (106, 328), 'Different hands. Shared possibilities.', 37, '#5c6862')
    text(cover, (1865, 183), 'A workspace for', 29, '#717a74')
    text(cover, (1865, 225), 'dexterous manipulation.', 29, '#202421')
    draw = ImageDraw.Draw(cover)
    draw.line((105, 425, 2295, 425), fill='#cdd1c8', width=2)
    draw.line((105, 425, 265, 425), fill='#637b63', width=4)
    centers = [278, 645, 1012, 1379, 1746, 2113]
    for n, (index, cx) in enumerate(zip(HERO, centers)):
        entry = entries[index]
        frame = Image.open(ROOT / entry['studio_render']).convert('RGBA')
        # Taller lead models establish rhythm without boxing the silhouettes.
        height = [510, 620, 490, 575, 510, 590][n]
        place_hand(cover, frame, cx, 1085, 330, height)
        text(cover, (cx, 1140), entry['title'], 31, font=BOLD, anchor='mt')
        tracked_label = entry['manufacturer'].replace(' ROBOTICS', '')
        text(cover, (cx, 1190), tracked_label, 16, '#7b847d', MONO, anchor='mt')
    draw = ImageDraw.Draw(cover)
    draw.line((105, 1266, 2295, 1266), fill='#cdd1c8', width=1)
    tracked(cover, (106, 1300), 'ASSETS  /  SIMULATION  /  EXPERIMENTS', size=16, spacing=3)
    text(cover, (2295, 1300), 'ISAAC SIM  +  ISAAC LAB  +  ARENA', 19, '#69736d', MONO, anchor='rt')
    cover.convert('RGB').save(MEDIA / 'dexterouslab-cover.png', optimize=True)

    # Secondary, unboxed contact sheet keeps every selected hand discoverable.
    atlas = background((2400, 1760))
    tracked(atlas, (105, 65), 'THE HAND COLLECTION', size=20)
    text(atlas, (100, 110), 'Many forms of dexterity.', 74, font=BOLD)
    text(atlas, (2295, 158), '18 configurations / 17 manufacturers', 25, '#69736d', anchor='rt')
    for n, entry in enumerate(entries):
        row, col = divmod(n, 6)
        cx, bottom = 280+col*368, 600+row*490
        frame = Image.open(ROOT / entry['studio_render']).convert('RGBA')
        place_hand(atlas, frame, cx, bottom, 285, 335)
        text(atlas, (cx, bottom+28), entry['title'], 27, font=BOLD, anchor='mt')
        text(atlas, (cx, bottom+71), entry['manufacturer'], 15, '#7b847d', MONO, anchor='mt')
    text(atlas, (105, 1704), 'Real local USD geometry. Studio materials. Asset previews, not grasp demonstrations.', 22, '#788079')
    atlas.convert('RGB').save(MEDIA / 'dexterouslab-collection.png', optimize=True)
    (MEDIA / 'cover-provenance.json').write_text(json.dumps({
        'generator': 'scripts/build_readme_cover.py',
        'style': 'Warm ivory editorial cover; neutral graphite and ceramic materials; studio key, fill and rim lights.',
        'hero_selection': [entries[i]['asset_id'] for i in HERO],
        'method': 'Actual local USD geometry, authored transforms; VTK PBR studio rendering; Pillow layout.',
        'scope': 'Visual asset presentation only. No new physics validation or successful grasp is implied.',
        'assets': entries,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
