"""Shared provenance catalog facade; reuse the existing storage and registrations."""

import json
from pathlib import Path

from dexterous_lab.assets.catalog import AssetCatalog, sha256_file


class AssetRegistry(AssetCatalog):
    def model_path(self, asset_id):
        record = self.get(asset_id)
        reference = record.get('isaaclab_asset_path') or record.get('local_raw_path')
        if not reference:
            raise ValueError(f'No model path available for {asset_id}')
        return reference

    def verify_integrity(self, asset_id):
        record = self.get(asset_id)
        manifest = record.get('checksum_manifest')
        if not manifest:
            raise ValueError('Asset has no fetched content/checksum manifest')
        entries = json.loads(Path(manifest).read_text())
        failures = []
        raw = self.directory(record) / 'raw'
        for entry in entries:
            path = (raw / entry['path']).resolve()
            if not path.is_relative_to(raw.resolve()) or not path.is_file() or sha256_file(path) != entry['sha256']:
                failures.append(entry['path'])
        return {'asset_id': asset_id, 'passed': not failures, 'files_checked': len(entries), 'failures': failures}
