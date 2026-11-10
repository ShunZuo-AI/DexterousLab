"""Author dynamic single-body USD assets from DexGraspNet convex pieces."""

import json
from pathlib import Path
import sys

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file
from dexterous_lab.assets.dexgraspnet_samples import SAMPLES, load_scaled_pieces
from dexterous_lab.config import CONFIG_ROOT, PROJECT_ROOT


def prepare_object(name, longest_side_m, run_name):
    """Keep the source decomposition and use each piece as one convex collider."""
    import numpy as np
    import trimesh
    from pxr import Gf, Usd, UsdGeom, UsdPhysics
    from isaaclab_arena.utils.usd.helpers import extract_trimesh_from_usd_path

    catalog = AssetCatalog()
    record = catalog.get(f"dexgraspnet/{SAMPLES[name]}")
    directory = catalog.directory(record)
    report_path = directory / "preparation.json"
    config = CONFIG_ROOT / "objects" / f"{name}.toml"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        if report["geometry"]["longest_side_m"] != longest_side_m:
            raise ValueError("Existing sample uses another size; preserving its configuration")
        for path, expected in [(Path(report["usd_path"]), report["usd_sha256"]), (config, report["config_sha256"])]:
            if not path.is_file() or sha256_file(path) != expected:
                raise ValueError(f"Prepared file changed: {path}")
        return dict(report, status="already_prepared")
    if config.exists():
        raise FileExistsError(f"Preserving existing configuration: {config}")
    pieces, geometry = load_scaled_pieces(Path(record["local_raw_path"]).parent, longest_side_m)
    processed = directory / "processed" / run_name
    processed.mkdir(parents=True, exist_ok=False)
    usd_path = processed / "object.usda"
    stage = Usd.Stage.CreateNew(str(usd_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/Object").GetPrim()
    stage.SetDefaultPrim(root)
    UsdPhysics.RigidBodyAPI.Apply(root).CreateRigidBodyEnabledAttr(True)
    UsdPhysics.MassAPI.Apply(root).CreateMassAttr(0.1)
    for index, piece in enumerate(pieces):
        mesh = UsdGeom.Mesh.Define(stage, f"/Object/piece_{index}")
        mesh.CreatePointsAttr([Gf.Vec3f(*vertex) for vertex in piece.vertices])
        mesh.CreateFaceVertexCountsAttr([3] * len(piece.faces))
        mesh.CreateFaceVertexIndicesAttr(piece.faces.flatten().tolist())
        mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
        mesh.CreateDisplayColorAttr([(0.18, 0.52, 0.8)])
        mesh.CreateExtentAttr(UsdGeom.PointBased(mesh).ComputeExtent(mesh.GetPointsAttr().Get()))
        UsdPhysics.CollisionAPI.Apply(mesh.GetPrim()).CreateCollisionEnabledAttr(True)
        UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr("convexHull")
    stage.GetRootLayer().Save()
    extracted = extract_trimesh_from_usd_path(str(usd_path))
    combined = trimesh.util.concatenate(pieces)
    if not np.allclose(extracted.bounds, combined.bounds, atol=1e-6):
        raise ValueError("USD geometry differs from scaled source pieces")
    expected = geometry["extents_m"]
    config_text = (
        'kind = "usd"\n'
        f'registry_name = "{name}"\n'
        f'usd_path = "{usd_path.relative_to(PROJECT_ROOT).as_posix()}"\n'
        f'size = {expected}\n'
        f'position_xyz = [-0.55, 0.0, {0.255 + expected[2] / 2 + 0.003}]\n'
        'rotation_xyzw = [0.0, 0.0, 0.0, 1.0]\nscale = [1.0, 1.0, 1.0]\n'
        'mass = 0.1\nfriction = 0.7\n'
        f'asset_version = "dgn-convex-v1:{sha256_file(Path(record["local_raw_path"]))[:16]}"\n'
    )
    with config.open("x") as stream:
        stream.write(config_text)
    report = {
        "status": "prepared", "asset_id": record["asset_id"], "object_id": name,
        "raw_mesh": record["local_raw_path"], "source_sha256": sha256_file(record["local_raw_path"]),
        "usd_path": str(usd_path), "usd_sha256": sha256_file(usd_path),
        "config_path": str(config), "config_sha256": sha256_file(config),
        "geometry": geometry, "convex_piece_count": len(pieces),
        "vertices": len(extracted.vertices), "faces": len(extracted.faces),
        "collision": "Single dynamic rigid body; one convexHull collider for each upstream CoACD piece",
        "appearance": "Uniform blue display color; original photo textures not included in this package",
        "mass_kg": 0.1, "friction": 0.7, "physics_scope": "Assumed experimental values",
        "grasp_success": None, "simulation_status": "not_run",
    }
    save_json(report_path, report)
    catalog.update(record, conversion_status="converted", local_processed_path=str(usd_path),
                   isaaclab_asset_path=str(usd_path), processed_sha256=sha256_file(usd_path),
                   preparation_report=str(report_path))
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
        results = [prepare_object(name, request["longest_side_m"], Path(request["run_dir"]).name)
                   for name in request["names"]]
        save_json(Path(request["run_dir"]) / "result.json", results)


if __name__ == "__main__":
    main()
