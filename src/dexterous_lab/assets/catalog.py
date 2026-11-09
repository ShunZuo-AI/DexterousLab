"""Provenance-aware catalog of indexed, fetched, converted and simulated assets."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
from pathlib import Path
import uuid

from dexterous_lab.config import PROJECT_ROOT


MANIFEST_ROOT = PROJECT_ROOT / "assets/manifests"
ASSET_ROOT = PROJECT_ROOT / "assets"


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


class AssetCatalog:
    def __init__(self, manifest_root=MANIFEST_ROOT, asset_root=ASSET_ROOT):
        self.manifest_root = Path(manifest_root)
        self.asset_root = Path(asset_root).resolve()

    def records(self, category="hands"):
        if category not in ("hands", "objects", "manufacturers"):
            raise ValueError(f"Unsupported catalog category: {category}")
        return json.loads((self.manifest_root / f"{category}.json").read_text())[category]

    def get(self, asset_id):
        matches = []
        for category in ("hands", "objects"):
            matches.extend(record for record in self.records(category) if record["asset_id"] == asset_id)
        if len(matches) != 1:
            raise ValueError(f"Asset ID {asset_id!r} is not uniquely registered")
        return matches[0]

    def manufacturers(self):
        hands = self.records('hands')
        result = []
        for manufacturer in self.records('manufacturers'):
            current = dict(manufacturer)
            variants = [record for record in hands if record['manufacturer'] == current['manufacturer']]
            current['source_status'] = 'indexed' if any(record.get('source_file_path') for record in variants) else 'unresolved'
            current['asset_count'] = len(variants)
            current['fetched_variants'] = sum(record['download_status'] in ('fetched', 'reference_recorded') for record in variants)
            current['validated_variants'] = sum(record['simulation_status'] == 'passed' for record in variants)
            current['failed_variants'] = sum(record['simulation_status'] == 'failed' for record in variants)
            current['blocked_variants'] = sum(bool(record.get('blocking_reason')) for record in variants)
            result.append(current)
        return result

    def directory(self, record):
        category = record["category"]
        if category not in ("hands", "objects"):
            raise ValueError("Asset category must be hands or objects")
        destination = (self.asset_root / category / record["asset_id"]).resolve()
        if not destination.is_relative_to(self.asset_root / category):
            raise ValueError("Asset ID escapes the managed storage directory")
        return destination

    @contextmanager
    def lock(self):
        self.manifest_root.mkdir(parents=True, exist_ok=True)
        with (self.manifest_root / ".catalog.lock").open("a") as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield
            fcntl.flock(stream, fcntl.LOCK_UN)

    def register(self, record):
        directory = self.directory(record)
        with self.lock():
            category = record['category']
            path = self.manifest_root / f'{category}.json'
            data = json.loads(path.read_text())
            if any(current['asset_id'] == record['asset_id'] for current in data[category]):
                raise ValueError(f"Asset already registered: {record['asset_id']}")
            record = dict(record, asset_directory=str(directory))
            for folder in ('raw', 'processed', 'isaaclab'):
                (directory / folder).mkdir(parents=True, exist_ok=True)
            save_json(directory / 'metadata.json', record)
            save_json(directory / 'validation.json', {'static_status': 'not_run', 'simulation_status': 'not_run'})
            data[category].append(record)
            save_json(path, data)
            return record

    def update(self, record, **changes):
        with self.lock():
            category = record["category"]
            path = self.manifest_root / f"{category}.json"
            data = json.loads(path.read_text())
            for current in data[category]:
                if current["asset_id"] == record["asset_id"]:
                    current.update(changes)
                    current["updated_utc"] = datetime.now(timezone.utc).isoformat()
                    directory = self.directory(current)
                    save_json(directory / "metadata.json", current)
                    save_json(path, data)
                    return current
        raise ValueError("Asset disappeared from catalog")
