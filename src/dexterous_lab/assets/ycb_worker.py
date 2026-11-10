"""Convert official YCB OBJ files using Isaac Lab's installed MeshConverter."""

import json
from pathlib import Path
import sys

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file
from dexterous_lab.assets.ycb import OBJECTS, prepare_converter_input, verify_download
from dexterous_lab.config import CONFIG_ROOT, PROJECT_ROOT


PREPARATION_VERSION = "ycb-google16k-centered-v1"


def prepare_object(name, run_name):
    """Preserve raw metric geometry and author a centered dynamic USD object."""
    import numpy as np
    import trimesh
    import isaaclab.sim as sim_utils
    from isaaclab.sim.converters import MeshConverter, MeshConverterCfg
    from isaaclab_arena.utils.usd.helpers import extract_trimesh_from_usd_path
    from pxr import Usd, UsdGeom

    catalog = AssetCatalog()
    record = catalog.get(f"ycb/{OBJECTS[name]}")
    directory = catalog.directory(record)
    verify_download(directory)
    previous = directory / "preparation.json"
    if previous.is_file():
        report = json.loads(previous.read_text())
        for entry in report["processed_checksums"]:
            path = directory / entry["path"]
            if not path.is_file() or sha256_file(path) != entry["sha256"]:
                raise ValueError(f"Prepared asset changed: {path}")
        config = CONFIG_ROOT / "objects" / f"ycb_{name}.toml"
        if not config.is_file() or sha256_file(config) != report["config_sha256"]:
            raise ValueError(f"YCB configuration missing or changed: {config}")
        return dict(report, status="already_prepared")

    source = Path(record["local_raw_path"])
    mesh = trimesh.load(source, force="mesh", process=False)
    if len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
        raise ValueError(f"Invalid source mesh: {source}")
    extents = mesh.extents
    if not (0.005 < min(extents) and max(extents) < 0.5):
        raise ValueError(f"Unexpected metric YCB dimensions: {extents}")
    center = mesh.bounds.mean(axis=0)
    processed = directory / "processed" / run_name
    processed.mkdir(parents=True, exist_ok=False)
    converter_input, repair = prepare_converter_input(source, processed / "source_mesh")
    approximation = "convexDecomposition" if name == "mug" else "convexHull"
    mesh_collision = (
        sim_utils.ConvexDecompositionPropertiesCfg()
        if name == "mug" else sim_utils.ConvexHullPropertiesCfg()
    )
    converter = MeshConverter(MeshConverterCfg(
        asset_path=str(converter_input), usd_dir=str(processed), usd_file_name="object.usd",
        make_instanceable=False,
        translation=tuple(float(value) for value in -center),
        mass_props=sim_utils.MassPropertiesCfg(mass=0.1),
        rigid_props=sim_utils.RigidBodyPropertiesCfg(disable_gravity=False),
        collision_props=sim_utils.CollisionPropertiesCfg(contact_offset=0.002),
        mesh_collision_props=mesh_collision,
    ))
    usd_path = Path(converter.usd_path)
    converted_mesh = extract_trimesh_from_usd_path(str(usd_path))
    if not np.allclose(converted_mesh.extents, extents, rtol=1e-3, atol=1e-5):
        raise ValueError(f"Conversion changed metric extents: {extents} -> {converted_mesh.extents}")
    if not np.allclose(converted_mesh.bounds.mean(axis=0), 0, atol=1e-4):
        raise ValueError("Converted object is not centered in its root frame")
    stage = Usd.Stage.Open(str(usd_path))
    material_count = sum(prim.GetTypeName() == "Material" for prim in stage.Traverse())
    texture_paths = []
    for prim in stage.Traverse():
        for attribute in prim.GetAttributes():
            if str(attribute.GetTypeName()) != "asset":
                continue
            value = attribute.Get()
            if not value or Path(value.path).suffix.lower() not in (".png", ".jpg", ".jpeg", ".exr"):
                continue
            resolved = value.resolvedPath or str(usd_path.parent / value.path)
            if not Path(resolved).is_file():
                raise ValueError(f"Converted texture is missing: {value.path}")
            texture_paths.append(resolved)
    if not material_count or not texture_paths:
        raise ValueError("Converted YCB asset lost its texture material")
    config = CONFIG_ROOT / "objects" / f"ycb_{name}.toml"
    config_text = (
        'kind = "usd"\n'
        f'registry_name = "ycb_{name}"\n'
        f'usd_path = "{usd_path.relative_to(PROJECT_ROOT).as_posix()}"\n'
        f'size = {extents.tolist()}\n'
        f'position_xyz = [-0.55, 0.0, {0.255 + extents[2] / 2 + 0.003}]\n'
        'rotation_xyzw = [0.0, 0.0, 0.0, 1.0]\n'
        'scale = [1.0, 1.0, 1.0]\n'
        'mass = 0.1\nfriction = 0.7\n'
        f'asset_version = "{PREPARATION_VERSION}:{sha256_file(source)[:16]}"\n'
    )
    if config.exists():
        raise FileExistsError(f"Preserving existing object configuration: {config}")
    with config.open("x") as stream:
        stream.write(config_text)
    checksums = [
        {"path": str(path.relative_to(directory)), "sha256": sha256_file(path)}
        for path in sorted(processed.rglob("*")) if path.is_file()
    ]
    report = {
        "asset_id": record["asset_id"], "object_id": f"ycb_{name}", "status": "prepared",
        "preparation_version": PREPARATION_VERSION, "raw_mesh": str(source),
        "source_sha256": sha256_file(source), "usd_path": str(usd_path),
        "converter_input": str(converter_input), "repair": repair,
        "config_path": str(config), "config_sha256": sha256_file(config),
        "vertices": len(mesh.vertices), "faces": len(mesh.faces),
        "source_extents_m": extents.tolist(), "converted_extents_m": converted_mesh.extents.tolist(),
        "source_center_in_source_frame_m": center.tolist(), "length_unit": "m",
        "stage_meters_per_unit": UsdGeom.GetStageMetersPerUnit(stage),
        "collision_approximation": approximation,
        "material_count": material_count, "texture_paths": texture_paths,
        "processed_checksums": checksums,
        "physics_parameters": {"mass_kg": 0.1, "friction": 0.7,
                               "scope": "Assumed smoke-test values, not measured YCB mass/friction"},
        "simulation_status": "not_run", "grasp_success": None,
    }
    save_json(previous, report)
    catalog.update(
        record, conversion_status="converted", local_processed_path=str(usd_path),
        isaaclab_asset_path=str(usd_path), scene_object=f"ycb_{name}",
        processed_sha256=sha256_file(usd_path), preparation_report=str(previous),
    )
    return report


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    from isaaclab_arena.cli.isaaclab_arena_cli import get_isaaclab_arena_cli_parser
    from isaaclab_arena.utils.isaaclab_utils.simulation_app import SimulationAppContext

    args = get_isaaclab_arena_cli_parser().parse_args([])
    args.device = "cuda:0"
    args.visualizer = None
    args.enable_cameras = False
    args.kit_args = f"--portable-root {PROJECT_ROOT / '.cache/kit'}"
    sys.argv = [sys.argv[0]]
    with SimulationAppContext(args):
        results = [prepare_object(name, Path(request["run_dir"]).name) for name in request["objects"]]
        save_json(Path(request["run_dir"]) / "result.json", results)


if __name__ == "__main__":
    main()
