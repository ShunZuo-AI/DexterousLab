"""Export auditable per-vendor coverage from actual asset evidence."""

from collections import Counter
import json
from pathlib import Path

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file


def main():
    catalog = AssetCatalog()
    root = Path('/root/gpufree-data/DexterousLab/docs/asset_aggregation')
    hands = catalog.records()
    vendors = catalog.manufacturers()
    validations = []
    integrity = []
    for record in hands:
        if record['download_status'] in ('fetched', 'reference_recorded'):
            checksum_path = catalog.directory(record) / 'checksums.json'
            fingerprints = json.loads(checksum_path.read_text())
            failures = []
            for entry in fingerprints:
                path = catalog.directory(record) / 'raw' / entry['path']
                if not path.is_file() or sha256_file(path) != entry['sha256']:
                    failures.append(entry['path'])
            integrity.append({'asset_id': record['asset_id'], 'files_checked': len(fingerprints), 'passed': not failures,
                              'failures': failures, 'checksum_manifest': str(checksum_path)})
        if record['simulation_status'] != 'passed':
            continue
        run = Path(record['last_run'])
        evidence_path = run / 'evidence.json'
        if not evidence_path.exists():
            evidence_path = run / 'simulation_result.json'
        evidence = json.loads(evidence_path.read_text())
        names = evidence.get('joint_names', [])
        if (run / 'robot_mapping.json').exists():
            names = json.loads((run / 'robot_mapping.json').read_text())['articulation_joint_names']
        assert evidence['steps_completed'] >= 100, 'Do not count shorter runs in the 100-step coverage report'
        validations.append({'asset_id': record['asset_id'], 'manufacturer': record['manufacturer'],
                            'joint_count': len(names), 'steps_completed': evidence['steps_completed'],
                            'physics_dt': evidence.get('physics_dt'), 'evidence': str(evidence_path),
                            'source_repository': record['source_repository'], 'source_commit': record['source_commit'],
                            'local_raw_path': record['local_raw_path'], 'local_processed_path': record['local_processed_path'],
                            'validation_settings': record.get('validation_settings', {})})
    save_json(root / 'expanded-validation-summary.json', validations)
    save_json(root / 'expanded-integrity.json', integrity)
    save_json(root / 'expanded-coverage.json', {'manufacturers': vendors, 'hand_records': len(hands),
              'download_statuses': dict(Counter(record['download_status'] for record in hands)),
              'validated_configurations': len(validations), 'validated_manufacturers': len({row['manufacturer'] for row in validations})})
    lines = ['# 当前资产覆盖表', '',
             '计数单位为具体资产配置，包含左右手或不同修订；不能等同于厂商数或完全可用的抓取控制器数。', '',
             '| 厂商 | 登记 | 已提取/官方引用留档 | 100 步通过 | 仿真失败 | 有明确阻塞说明 |',
             '|---|---:|---:|---:|---:|---:|']
    for row in vendors:
        lines.append(f"| {row['name']} | {row['asset_count']} | {row['fetched_variants']} | {row['validated_variants']} | {row['failed_variants']} | {row['blocked_variants']} |")
    lines += ['', '## 已通过的具体配置', '', '| 资产 ID | 物理关节数 | 步数 | 证据 |', '|---|---:|---:|---|']
    for row in validations:
        lines.append(f"| `{row['asset_id']}` | {row['joint_count']} | {row['steps_completed']} | `{row['evidence']}` |")
    lines += ['', '## 逐项阻塞', '']
    for record in hands:
        if record.get('blocking_reason'):
            lines.append(f"- `{record['asset_id']}`：{record['blocking_reason']}")
    (root / 'coverage.md').write_text('\n'.join(lines) + '\n')
    print(f"{len(validations)} validated configurations, {len(integrity)} original packages checked")
    if any(not row['passed'] for row in integrity):
        raise ValueError('Original package integrity failed; see expanded-integrity.json')


if __name__ == '__main__':
    main()
