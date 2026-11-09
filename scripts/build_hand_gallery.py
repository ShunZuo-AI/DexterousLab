"""Render real local USD hand geometry into the README's multi-hand cover."""

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pxr import Usd, UsdGeom
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs/media'
SELECTION = [
    ('wonik/allegro/isaaclab_standalone', 'Allegro Hand', 'WONIK ROBOTICS'),
    ('shadow_robot/dexterous_hand/right_isaaclab', 'Shadow Hand', 'SHADOW ROBOT'),
    ('leap/leap_hand_v1/right', 'LEAP Hand', 'LEAP'),
    ('unitree/dex5_1/right', 'Dex5-1', 'UNITREE'),
    ('wuji/hand_v1/right', 'Wuji Hand V1', 'WUJI'),
    ('wuji/hand_v2/2_2_right', 'Wuji Hand V2.2', 'WUJI'),
    ('brainco/revo2/revo2_right_hand', 'Revo2', 'BRAINCO'),
    ('robotera/xhand/xhand_right', 'XHand', 'ROBOTERA'),
    ('tesollo/dg5f/dg5f_right', 'DG5F', 'TESOLLO'),
    ('psyonic/ability_hand/ability_hand_right_large', 'Ability Hand', 'PSYONIC'),
    ('schunk/svh/schunk_svh_hand_right', 'SVH', 'SCHUNK'),
    ('barrett/barrett_hand/bhand_model', 'Barrett Hand', 'BARRETT'),
    ('robotis/hx5/urdf_hx5_d20_right', 'HX5', 'ROBOTIS'),
    ('orca/orca_hand/v1_models_urdf_orcahand_right', 'ORCA Hand', 'ORCA'),
    ('dexrobot/dexhand021/dexhand021_right', 'DexHand021', 'DEXROBOT'),
    ('oymotion/rohand/urdf_rohand_right', 'ROHand', 'OYMOTION'),
    ('linkerbot/linkerhand_l20/right_linkerhand_l20_right', 'LinkerHand L20', 'LINKERBOT'),
    ('sharpa/sharpa_wave_wave_01/right_sharpa_wave_right_sharpa_wave', 'Sharpa Wave', 'SHARPA'),
]
CACHE = ROOT / 'assets/cache/https/omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.2/Isaac'
OFFICIAL = {
    'wonik/allegro/isaaclab_standalone': CACHE / 'Robots/WonikRobotics/AllegroHand/allegro_hand_instanceable.usd',
    'shadow_robot/dexterous_hand/right_isaaclab': CACHE / 'Robots_Multiphysics/ShadowRobot/ShadowHandMultiPhysics_v0/right_hand/right_hand.usda',
}


def meshes(path):
    """Read visible USD meshes with authored world transforms, excluding colliders."""
    stage = Usd.Stage.Open(str(path))
    if stage is None:
        raise RuntimeError(f'Could not open {path}')
    transforms = UsdGeom.XformCache()
    result = []
    for prim in Usd.PrimRange(stage.GetPseudoRoot(), Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        name = str(prim.GetPath())
        if any(word in name.lower() for word in ('collision', 'collider')):
            continue
        geometry = UsdGeom.Mesh(prim)
        if geometry.ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        points = np.asarray(geometry.GetPointsAttr().Get(), dtype=float)
        if points.size == 0:
            continue
        matrix = np.asarray(transforms.GetLocalToWorldTransform(prim))
        world = np.c_[points, np.ones(len(points))] @ matrix
        counts = np.asarray(geometry.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
        indices = np.asarray(geometry.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
        result.append((name, world[:, :3], counts, indices))
    if not result:
        raise RuntimeError(f'No visible meshes: {path}')
    return result


def render(path, destination, asset_id):
    geometry = meshes(path)
    cloud = np.concatenate([m[1] for m in geometry])
    center = (cloud.min(axis=0) + cloud.max(axis=0)) / 2
    # Coordinate systems differ between vendors. Display the longest axis upright
    # and the thinnest axis in depth; no articulation or dimensions are changed.
    extents = np.ptp(cloud, axis=0)
    order = np.argsort(extents)
    axes = [order[1], order[0], order[2]]
    flip = 1
    tips = [p.mean(axis=0) for name, p, _, _ in geometry if any(s in name.lower() for s in ('distal', 'tip', 'link_3', 'link3'))]
    bases = [p.mean(axis=0) for name, p, _, _ in geometry if any(s in name.lower() for s in ('palm', 'base_link'))]
    if tips and bases and (np.mean(tips, axis=0) - np.mean(bases, axis=0))[axes[2]] < 0:
        flip = -1
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.048, 0.080, 0.125)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(1)
    window.SetSize(500, 490)
    window.SetMultiSamples(4)
    window.AddRenderer(renderer)
    for index, (name, points, counts, indices) in enumerate(geometry):
        vertices = np.ascontiguousarray((points - center)[:, axes])
        vertices[:, 2] *= flip
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
        normals.SetFeatureAngle(45)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(normals.GetOutputPort())
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        if any(token in name.lower() for token in ('distal', 'tip', 'link_3', 'link3')):
            prop.SetColor(0.28, 0.77, 0.74)
        else:
            gray = 0.66 + (index % 3) * 0.075
            prop.SetColor(gray * .9, gray * .96, gray)
        prop.SetInterpolationToPhong()
        prop.SetAmbient(.20)
        prop.SetDiffuse(.75)
        prop.SetSpecular(.45)
        prop.SetSpecularPower(35)
        renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    camera.SetPosition(*((.85, -1, .25) if asset_id.startswith('barrett/') else (.15, -1, .14)))
    camera.SetFocalPoint(0, 0, 0)
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    renderer.ResetCamera()
    camera.Zoom(1.08)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    output = capture.GetOutput()
    w, h, _ = output.GetDimensions()
    pixels = vtk_to_numpy(output.GetPointData().GetScalars()).reshape(h, w, -1)
    frame = Image.fromarray(np.flipud(pixels)).convert('RGB')
    angle = {'leap': 90, 'robotera': -90}.get(asset_id.split('/')[0], 0)
    if asset_id == 'wuji/hand_v2/2_2_right':
        angle = 180
    frame.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=(12, 20, 32)).save(destination, optimize=True)
    window.Finalize()
    return {'mesh_count': len(geometry), 'display_axes': [int(v) for v in axes], 'vertical_sign': flip,
            'image_rotation_degrees': angle}


def main():
    (MEDIA / 'hands').mkdir(parents=True, exist_ok=True)
    records = json.loads((ROOT / 'assets/manifests/hands.json').read_text())['hands']
    inventory = {r['asset_id']: r for r in records}
    provenance = []
    for asset_id, title, manufacturer in SELECTION:
        record = inventory[asset_id]
        source = OFFICIAL.get(asset_id, Path(record.get('isaaclab_asset_path') or 'missing'))
        target = MEDIA / 'hands' / (asset_id.replace('/', '--') + '.png')
        details = render(source, target, asset_id)
        provenance.append({'asset_id': asset_id, 'title': title, 'manufacturer': manufacturer,
            'source_usd': str(source.relative_to(ROOT)), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'render': str(target.relative_to(ROOT)), 'source_repository': record.get('source_repository'),
            'source_commit': record.get('source_commit'), 'license': record.get('license'), **details})
        print('RENDERED', asset_id, details, flush=True)

    # High-resolution editorial contact sheet; all hand pixels come from real USD.
    w, h = 1800, 1420
    image = Image.new('RGB', (w, h))
    draw = ImageDraw.Draw(image)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=(int(8 + 4*t), int(15 + 7*t), int(27 + 11*t)))
    regular = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    bold = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    mono = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    def text(x, y, value, size, color='#e9f1fa', face=regular):
        draw.text((x, y), value, font=ImageFont.truetype(face, size), fill=color)
    draw.rounded_rectangle((66, 52, 105, 57), radius=2, fill='#6ce2ce')
    text(120, 40, 'MULTI-HAND ROBOTICS RESEARCH', 19, '#91abc6', mono)
    text(64, 80, 'DexterousLab', 84, face=bold)
    text(69, 183, 'Many hands. One research workspace.', 30, '#afc1d8')
    text(1275, 93, '18 HAND PREVIEWS', 23, '#6ce2ce', mono)
    text(1275, 134, '17 MANUFACTURERS', 23, '#91abc6', mono)
    text(1275, 180, 'Rendered from local USD assets', 17, '#91abc6')
    for n, entry in enumerate(provenance):
        col, row = n % 6, n // 6
        x, y = 66 + col * 280, 265 + row * 342
        draw.rounded_rectangle((x, y, x+266, y+326), radius=16, fill='#0c1420', outline='#27384e', width=1)
        tile = Image.open(ROOT / entry['render']).resize((250, 245), Image.Resampling.LANCZOS)
        image.paste(tile, (x+8, y+9))
        draw = ImageDraw.Draw(image)
        text(x+17, y+260, entry['title'], 21, face=bold)
        text(x+17, y+294, entry['manufacturer'], 13, '#89a7bd', mono)
    draw.line((66, 1312, 1732, 1312), fill='#345564', width=1)
    text(67, 1337, 'ISAAC SIM  /  ISAAC LAB  /  ISAACLAB-ARENA', 20, '#9bb3cd', mono)
    text(67, 1373, 'Asset previews with unified studio materials; not grasp-success demonstrations.', 17, '#8ca2ba')
    text(1250, 1342, 'CONFIGURE  >  SIMULATE  >  MEASURE', 17, '#6ce2ce', mono)
    image.save(MEDIA / 'dexterouslab-hands.png', optimize=True)
    (MEDIA / 'hand-gallery-provenance.json').write_text(json.dumps({
        'generator': 'scripts/build_hand_gallery.py',
        'method': 'Local USD visual geometry + authored transforms; VTK studio render, no physics simulation.',
        'appearance': 'Unified silver/teal materials; vendor materials are not reproduced.',
        'scope': '18 selected configurations from 17 manufacturers; not all 22 validated configurations.',
        'assets': provenance,
    }, indent=2) + '\n')
    lines = ['# README 灵巧手展示图来源', '',
        '顶部主图使用18个真实本地USD模型，覆盖17个厂商。统一银灰/青绿色材质用于视觉展示，保留模型几何和USD装配变换。',
        '这是一组离线模型渲染，不是Isaac Sim仿真截图、实际关节控制或抓取成功证据；展示姿态来自USD的静态装配。',
        '选取的是已记录通过资产级验证的配置；新的桌面控制器仍需独立适配。', '',
        '源路径、commit、根USD SHA256、显示方向和许可记录见 [完整来源清单](hand-gallery-provenance.json)。', '',
        '| 展示名称 | 资产ID | 原始来源 | 许可记录 |', '|---|---|---|---|']
    for e in provenance:
        source = e.get('source_repository') or 'Isaac Lab / NVIDIA官方资产'
        lines.append(f"| {e['title']} | `{e['asset_id']}` | {source} | {e['license']['expression']} |")
    lines.extend(['', '各模型仍受原始作者及资产提供方的许可约束，项目不对第三方资产重新授权。XHand记录为非商业许可；NVIDIA资产遵循其资产条款。',
        '完整资产提取包中的原始LICENSE/NOTICE保持原样；本目录只保存展示用渲染图，不打包源网格。', '',
        '重新生成（使用当前共享环境已有的pxr、VTK和Pillow，不安装依赖）：', '', '```bash',
        '/root/gpufree-data/IsaacLab-Arena/.venv/bin/python scripts/build_hand_gallery.py', '```', ''])
    (MEDIA / 'README.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
