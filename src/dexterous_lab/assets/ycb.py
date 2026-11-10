"""Download a small, explicit set of YCB mesh packages without extra dependencies."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
import shutil
import sys
import tarfile
from urllib.request import Request, urlopen
import uuid

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file


OBJECTS = {
    "cracker_box": "003_cracker_box",
    "mustard_bottle": "006_mustard_bottle",
    "mug": "025_mug",
}
SOURCE = "https://registry.opendata.aws/ycb-benchmarks/"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 1024 * 1024 * 1024


def download_archive(url, archive):
    """Fetch bounded HTTP ranges and verify their offsets and lengths before writing."""
    with urlopen(Request(url, method="HEAD"), timeout=30) as response:
        length = int(response.headers["Content-Length"])
    if not 0 < length <= MAX_ARCHIVE_BYTES:
        raise ValueError("YCB archive exceeds the small-download size limit")
    chunk_size = 128 * 1024

    def fetch_chunk(start):
        end = min(start + chunk_size, length) - 1
        request = Request(url, headers={"Range": f"bytes={start}-{end}"})
        with urlopen(request, timeout=30) as response:
            expected_range = f"bytes {start}-{end}/{length}"
            if response.status != 206 or response.headers.get("Content-Range") != expected_range:
                raise ValueError("YCB server did not honor the requested byte range")
            data = response.read(end - start + 2)
        if len(data) != end - start + 1:
            raise ValueError("Incomplete YCB download chunk")
        return data

    print(f"Downloading {url.rsplit('/', 1)[-1]} ({length:,} bytes)", file=sys.stderr, flush=True)
    with archive.open("xb") as stream, ThreadPoolExecutor(max_workers=4) as pool:
        for data in pool.map(fetch_chunk, range(0, length, chunk_size)):
            stream.write(data)
    if archive.stat().st_size != length:
        raise ValueError("Incomplete YCB download")
    return length


def prepare_converter_input(source, destination):
    """Repair invalid OBJ normals in a copy, preserving positions and UV indices."""
    source = Path(source)
    lines = source.read_text().splitlines()
    invalid_normals = 0
    for line in lines:
        fields = line.split()
        if not fields or fields[0] not in ("v", "vt", "vn"):
            continue
        finite = all(isfinite(float(value)) for value in fields[1:])
        if not finite and fields[0] != "vn":
            raise ValueError("YCB source has non-finite positions or texture coordinates")
        invalid_normals += int(not finite)
    if not invalid_normals:
        return source, {"modified": False, "invalid_normals": 0}

    destination = Path(destination)
    shutil.copytree(source.parent, destination)
    repaired = []
    for line in lines:
        content, marker, comment = line.partition("#")
        fields = content.split()
        if fields and fields[0] == "vn":
            continue
        if fields and fields[0] == "f":
            vertices = []
            for field in fields[1:]:
                indices = field.split("/")
                vertex = indices[0]
                if len(indices) > 1 and indices[1]:
                    vertex += "/" + indices[1]
                vertices.append(vertex)
            line = "f " + " ".join(vertices)
            if marker:
                line += " #" + comment
        repaired.append(line)
    output = destination / source.name
    output.write_text("\n".join(repaired) + "\n")
    return output, {
        "modified": True, "invalid_normals": invalid_normals,
        "operation": "Drop all imported normals and normal indices; importer recomputes normals",
        "preserved": "Raw files unchanged; vertex positions, face vertex indices and UV indices preserved",
    }


def extract_mesh_package(archive, destination):
    """Extract regular files and directories, rejecting links and unsafe paths."""
    destination = Path(destination).resolve()
    with tarfile.open(archive, "r:gz") as package:
        members = package.getmembers()
        if len(members) > 1000 or sum(member.size for member in members) > MAX_EXTRACTED_BYTES:
            raise ValueError("YCB package exceeds the small-download extraction limit")
        for member in members:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination) or not (member.isfile() or member.isdir()):
                raise ValueError(f"Unsafe archive entry: {member.name}")
        package.extractall(destination, members=members, filter="data")


def verify_download(directory):
    """Verify local bytes against the checksums recorded at download time."""
    directory = Path(directory)
    provenance = json.loads((directory / "provenance.json").read_text())
    if sha256_file(directory / "source.tgz") != provenance["archive_sha256"]:
        raise ValueError(f"Downloaded archive changed: {directory}")
    entries = json.loads((directory / "checksums.json").read_text())
    if not entries:
        raise ValueError("Empty YCB checksum manifest")
    raw = (directory / "raw").resolve()
    for entry in entries:
        path = (raw / entry["path"]).resolve()
        if not path.is_relative_to(raw) or not path.is_file() or sha256_file(path) != entry["sha256"]:
            raise ValueError(f"Downloaded YCB file missing or changed: {entry['path']}")
    return provenance


def download_object(name, catalog=None):
    """Fetch one official google_16k package, preserving existing directories."""
    if name not in OBJECTS:
        raise ValueError(f"Unknown YCB sample {name!r}; choose from {list(OBJECTS)}")
    catalog = catalog or AssetCatalog()
    object_name = OBJECTS[name]
    asset_id = f"ycb/{object_name}"
    directory = catalog.asset_root / "objects" / asset_id
    if directory.exists():
        verify_download(directory)
        catalog.get(asset_id)
        return {"asset_id": asset_id, "status": "already_present", "directory": str(directory)}

    directory.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(directory.parent).free < 2 * 1024**3:
        raise ValueError("YCB download requires at least 2 GiB free disk space")
    staging = directory.with_name(f".{object_name}-{uuid.uuid4().hex}.tmp")
    staging.mkdir()
    url = f"https://ycb-benchmarks.s3.amazonaws.com/data/google/{object_name}_google_16k.tgz"
    try:
        archive = staging / "source.tgz"
        count = download_archive(url, archive)
        raw = staging / "raw"
        raw.mkdir()
        extract_mesh_package(archive, raw)
        mesh = raw / object_name / "google_16k/textured.obj"
        if not mesh.is_file():
            raise ValueError("YCB package does not contain the expected textured.obj")
        provenance = {
            "asset_id": asset_id, "url": url, "source": SOURCE,
            "license": "CC-BY-4.0", "license_url": LICENSE,
            "attribution": "Yale-CMU-Berkeley (YCB) Object and Model Set; Yale University and Berkeley",
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            "archive_bytes": count, "archive_sha256": sha256_file(archive),
            "checksum_scope": "Locally measured SHA-256; no publisher checksum was provided",
            "resolution": "google_16k", "length_unit": "m",
        }
        save_json(staging / "provenance.json", provenance)
        checksums = [
            {"path": str(path.relative_to(raw)), "sha256": sha256_file(path)}
            for path in sorted(raw.rglob("*")) if path.is_file()
        ]
        save_json(staging / "checksums.json", checksums)
        staging.rename(directory)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    record = {
        "asset_id": asset_id, "category": "objects", "manufacturer": None,
        "model": "ycb", "variant": object_name, "source_repository": SOURCE,
        "source_commit": None, "source_file_path": f"{object_name}/google_16k/textured.obj",
        "local_raw_path": str(directory / "raw" / object_name / "google_16k/textured.obj"),
        "local_processed_path": None, "isaaclab_asset_path": None,
        "license": {"status": "reviewed", "spdx": "CC-BY-4.0", "url": LICENSE, "source": SOURCE},
        "download_status": "fetched", "conversion_status": "not_run",
        "simulation_status": "not_run", "fetch_enabled": False,
        "checksum_manifest": str(directory / "checksums.json"),
        "notes": ["Downloaded mesh only; prepare-ycb and physics validation are separate steps"],
    }
    existing = [row for row in catalog.records("objects") if row["asset_id"] == asset_id]
    if existing:
        # A Git clone can contain catalog records without the ignored model files.
        catalog.update(existing[0], **record)
    else:
        catalog.register(record)
    return {"asset_id": asset_id, "status": "fetched", "archive_bytes": count, "directory": str(directory)}


def download_objects(names):
    return [download_object(name) for name in names]
