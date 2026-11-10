"""Prepare a selected DexGraspNet object subset without extracting the whole dataset."""

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import uuid

from dexterous_lab.assets.catalog import AssetCatalog, sha256_file
from dexterous_lab.config import CONFIG_ROOT, PROJECT_ROOT
from dexterous_lab.runtime import runtime_environment, shared_python, wait_for_process, write_json


SAMPLES = json.loads((CONFIG_ROOT / "downloads/dexgraspnet_samples.json").read_text())


def extract_samples(archive, destination, selected):
    """Extract only selected regular object files, rejecting unsafe package entries."""
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=False)
    total = 0
    found = set()
    with tarfile.open(archive, "r|gz") as package:
        for member in package:
            parts = Path(member.name).parts
            if len(parts) < 3 or parts[:1] != ("meshdata",) or parts[1] not in selected:
                continue
            path = destination / member.name
            if not path.resolve().is_relative_to(destination) or not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe DexGraspNet archive member: {member.name}")
            total += member.size
            if total > 100 * 1024 * 1024:
                raise ValueError("Selected subset exceeds 100 MiB")
            package.extract(member, destination, filter="data")
            if member.name.endswith("/coacd/decomposed.obj"):
                found.add(parts[1])
    if found != set(selected):
        raise ValueError(f"Object geometry missing from package: {sorted(set(selected) - found)}")


def load_scaled_pieces(directory, longest_side_m):
    """Return centered convex pieces with an explicit common metric scale."""
    import numpy as np
    import trimesh

    if not 0.02 <= longest_side_m <= 0.2:
        raise ValueError("Sample longest side must be between 0.02 and 0.2 meters")
    paths = sorted(Path(directory).glob("coacd_convex_piece_*.obj"))
    if not paths or len(paths) > 128:
        raise ValueError("Expected between 1 and 128 precomputed convex pieces")
    pieces = []
    repairs = []
    for path in paths:
        mesh = trimesh.load(path, force="mesh", process=True)
        if not len(mesh.faces) or not np.isfinite(mesh.vertices).all() or not mesh.is_watertight:
            raise ValueError(f"Invalid or non-watertight source piece: {path}")
        if not mesh.is_convex:
            hull = mesh.convex_hull
            relative_difference = abs(hull.volume - mesh.volume) / hull.volume
            if relative_difference > 1e-5:
                raise ValueError(f"Source piece is materially non-convex: {path}")
            repairs.append({"piece": path.name, "operation": "Recompute hull for near-convex numerical geometry",
                            "relative_volume_difference": float(relative_difference)})
            mesh = hull
        pieces.append(mesh)
    combined = trimesh.util.concatenate(pieces)
    extents = combined.extents
    if min(extents) <= 0:
        raise ValueError("Object has degenerate bounds")
    center = combined.bounds.mean(axis=0)
    scale = longest_side_m / max(extents)
    for mesh in pieces:
        mesh.vertices = (mesh.vertices - center) * scale
    return pieces, {
        "source_extents": extents.tolist(), "source_center": center.tolist(),
        "meters_per_source_unit": float(scale), "extents_m": (extents * scale).tolist(),
        "longest_side_m": longest_side_m, "numerical_hull_repairs": repairs,
        "scale_scope": "Explicit experimental size; not claimed as original physical dimensions or dataset grasp scale",
    }


def prepare_samples(names, longest_side_m=0.1):
    """Verify the downloaded package, extract a small subset and launch USD authoring."""
    if not names or any(name not in SAMPLES for name in names):
        raise ValueError(f"Choose samples from {list(SAMPLES)}")
    if not 0.02 <= longest_side_m <= 0.2:
        raise ValueError("Sample longest side must be between 0.02 and 0.2 meters")
    bundle = PROJECT_ROOT / "assets/objects/dexgraspnet/downloads/meshdata.tar.gz.download"
    provenance = json.loads((bundle / "provenance.json").read_text())
    if sha256_file(bundle / "payload") != provenance["sha256"]:
        raise ValueError("DexGraspNet archive no longer matches its recorded checksum")
    catalog = AssetCatalog()
    missing = []
    for name in names:
        asset_id = f"dexgraspnet/{SAMPLES[name]}"
        directory = catalog.asset_root / "objects" / asset_id
        if directory.exists():
            record = catalog.get(asset_id)
            for entry in json.loads((directory / "checksums.json").read_text()):
                path = directory / "raw" / entry["path"]
                if not path.resolve().is_relative_to((directory / "raw").resolve()) or sha256_file(path) != entry["sha256"]:
                    raise ValueError(f"Changed source file: {path}")
        else:
            missing.append(name)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = PROJECT_ROOT / "outputs" / f"{stamp}-dgn-prepare-{uuid.uuid4().hex[:8]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    if missing:
        extraction = run_dir / "selected_raw"
        extract_samples(bundle / "payload", extraction, [SAMPLES[name] for name in missing])
        for name in missing:
            code = SAMPLES[name]
            directory = catalog.asset_root / "objects/dexgraspnet" / code
            raw = directory / "raw"
            raw.mkdir(parents=True, exist_ok=False)
            shutil.copytree(extraction / "meshdata" / code, raw / code)
            entries = [{"path": str(p.relative_to(raw)), "sha256": sha256_file(p)}
                       for p in sorted(raw.rglob("*")) if p.is_file()]
            write_json(directory / "checksums.json", entries)
            write_json(directory / "source.json", dict(provenance, object_code=code))
            record = {
                "asset_id": f"dexgraspnet/{code}", "category": "objects", "manufacturer": None,
                "model": "dexgraspnet", "variant": code, "source_commit": None,
                "source_repository": "https://pku-epic.github.io/DexGraspNet/",
                "source_file_path": f"meshdata/{code}/coacd/decomposed.obj",
                "local_raw_path": str(raw / code / "coacd/decomposed.obj"),
                "local_processed_path": None, "isaaclab_asset_path": None,
                "license": {"status": "reviewed", "spdx": "CC-BY-NC-4.0",
                            "upstream": "YCB-derived object; preserve YCB attribution (CC-BY-4.0)"},
                "download_status": "fetched", "conversion_status": "not_run",
                "simulation_status": "not_run", "fetch_enabled": False,
                "checksum_manifest": str(directory / "checksums.json"), "scene_object": name,
                "notes": ["Selected precomputed convex geometry; no original texture; not yet simulation validated"],
            }
            existing = [r for r in catalog.records("objects") if r["asset_id"] == record["asset_id"]]
            if existing:
                catalog.update(existing[0], **record)
            else:
                catalog.register(record)
    request = {"names": names, "longest_side_m": longest_side_m, "run_dir": str(run_dir)}
    write_json(run_dir / "request.json", request)
    command = [shared_python(), "-m", "dexterous_lab.assets.dexgraspnet_worker", str(run_dir / "request.json")]
    print(f"Preparation log: {run_dir / 'conversion.log'}", file=sys.stderr, flush=True)
    with (run_dir / "conversion.log").open("x") as stream:
        child = subprocess.Popen(command, cwd=run_dir, env=runtime_environment(), stdout=stream, stderr=subprocess.STDOUT)
        code, error = wait_for_process(child, 300)
    if code != 0 or not (run_dir / "result.json").is_file():
        raise ValueError(f"Sample preparation failed ({error or code}); see {run_dir / 'conversion.log'}")
    return json.loads((run_dir / "result.json").read_text())
