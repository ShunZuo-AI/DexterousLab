"""Asset provenance, source integrity and static model checks without Kit."""

import json
from pathlib import Path
import subprocess

import pytest

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file
from dexterous_lab.assets.checks import inspect_urdf, mesh_path, prepare_import_urdf
from dexterous_lab.assets.manager import AssetManager
from dexterous_lab.config import PROJECT_ROOT


def isolated_catalog(tmp_path):
    manifests = tmp_path / "manifests"
    records = [{"asset_id": "vendor/hand/right", "category": "hands", "fetch_enabled": True,
                "download_status": "fetched"}]
    save_json(manifests / "hands.json", {"hands": records})
    save_json(manifests / "objects.json", {"objects": []})
    return AssetCatalog(manifests, tmp_path / "assets")


def test_catalog_update_and_escape(tmp_path):
    catalog = isolated_catalog(tmp_path)
    record = catalog.get("vendor/hand/right")
    catalog.update(record, simulation_status="not_run")
    assert catalog.get(record["asset_id"])["simulation_status"] == "not_run"
    assert (catalog.directory(record) / "metadata.json").is_file()
    with pytest.raises(ValueError, match="escapes"):
        catalog.directory({"category": "hands", "asset_id": "../../outside"})
    with pytest.raises(ValueError, match="not uniquely"):
        catalog.get("vendor/other/right")


def test_idempotent_fetch_checks_content(tmp_path):
    catalog = isolated_catalog(tmp_path)
    record = catalog.get("vendor/hand/right")
    directory = catalog.directory(record)
    raw = directory / "raw/model.urdf"
    raw.parent.mkdir(parents=True)
    raw.write_text("original")
    save_json(directory / "checksums.json", [{"path": "model.urdf", "sha256": sha256_file(raw)}])
    manager = AssetManager(catalog)
    assert manager.fetch(record["asset_id"])["status"] == "already_present"
    raw.write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        manager.fetch(record["asset_id"])


def test_static_checks_reject_missing_mesh_and_inertia(tmp_path):
    urdf = tmp_path / "model.urdf"
    urdf.write_text('''<robot name="bad"><link name="base"><inertial>
      <mass value="-1"/><inertia ixx="1" iyy="1" izz="1" ixy="0" ixz="0" iyz="0"/>
      </inertial><collision><geometry><mesh filename="missing.stl"/></geometry></collision>
      </link></robot>''')
    report = inspect_urdf(urdf, tmp_path)
    assert not report["passed"]
    assert any("inertia" in failure for failure in report["failures"])
    assert any("Missing mesh" in failure for failure in report["failures"])


def test_manifest_provenance_and_variant_separation():
    catalog = AssetCatalog()
    records = catalog.records("hands") + catalog.records("objects")
    required = {"asset_id", "manufacturer", "model", "variant", "source_repository", "source_commit",
                "source_file_path", "local_raw_path", "local_processed_path", "isaaclab_asset_path",
                "license", "download_status", "conversion_status", "simulation_status"}
    assert len({record['asset_id'] for record in records}) == len(records)
    for record in records:
        assert required <= record.keys()
        catalog.directory(record)
    assert catalog.get("unitree/dex3_1/right")["source_file_path"].endswith("dex3_1_r.urdf")
    assert catalog.get("unitree/dex3_1/left")["source_file_path"].endswith("dex3_1_l.urdf")


def test_cli_lists_manufacturers_and_rejects_unvalidated_preview():
    launcher = PROJECT_ROOT / "scripts/dexlab"
    child = subprocess.run([str(launcher), "assets", "manufacturers"], capture_output=True, text=True)
    assert child.returncode == 0
    assert len(json.loads(child.stdout)) >= 18
    child = subprocess.run([str(launcher), "assets", "preview", "--id", "shadow_robot/dex_ee/0x02000105"], capture_output=True, text=True)
    assert child.returncode != 0
    assert "successful physics validation" in child.stderr or "requires DISPLAY" in child.stderr


def test_preview_records_launch_without_marking_validation_passed(tmp_path, monkeypatch):
    from unittest.mock import patch

    catalog = isolated_catalog(tmp_path)
    record = catalog.get('vendor/hand/right')
    monkeypatch.setenv('DISPLAY', ':20')
    with pytest.raises(ValueError, match='successful physics validation'):
        AssetManager(catalog).preview(record['asset_id'])
    catalog.update(record, simulation_status='passed', isaaclab_asset_path='/model.usd')
    with patch('dexterous_lab.assets.manager.subprocess.Popen') as process:
        process.return_value.pid = 123
        result = AssetManager(catalog).preview(record['asset_id'], seconds=10)
        assert result['status'] == 'starting'
        assert result['pid'] == 123
        request = json.loads((Path(result['run_directory']) / 'request.json').read_text())
        assert request['action'] == 'preview'
        assert request['seconds'] == 10
        assert not (Path(result['run_directory']) / 'ready.json').exists()
    monkeypatch.delenv('DISPLAY')
    with pytest.raises(ValueError, match='requires DISPLAY'):
        AssetManager(catalog).preview(record['asset_id'])


def test_register_preserves_existing_asset(tmp_path):
    catalog = isolated_catalog(tmp_path)
    record = catalog.get('vendor/hand/right')
    with pytest.raises(ValueError, match='already registered'):
        catalog.register(dict(record, simulation_status='passed'))
    assert 'simulation_status' not in catalog.get(record['asset_id'])
    new = dict(record, asset_id='vendor/other/left')
    catalog.register(new)
    assert catalog.get(new['asset_id'])['asset_directory'] == str(catalog.directory(new))


def test_import_derivative_preserves_source_and_mimic(tmp_path):
    import xml.etree.ElementTree as ET

    raw = tmp_path / 'raw'
    raw.mkdir()
    mesh = raw / 'actual.stl'
    mesh.write_text('mesh source bytes')
    source = raw / 'model.urdf'
    text = '''<robot name="test"><link name="base"><visual><geometry>
      <mesh filename="package://vendor/wrong.stl" scale="0.001 0.001 0.001"/>
      </geometry></visual></link><joint name="dependent" type="revolute">
      <mimic joint="driver" multiplier="1.2" offset="0.1"/></joint></robot>'''
    source.write_text(text)
    destination = tmp_path / 'import.urdf'
    mapping = prepare_import_urdf(source, raw, destination, {'package://vendor/wrong.stl': 'actual.stl'})
    assert source.read_text() == text
    converted = ET.parse(destination)
    assert converted.find('.//mimic').attrib == {'joint': 'driver', 'multiplier': '1.2', 'offset': '0.1'}
    assert converted.find('.//mesh').get('scale') == '0.001 0.001 0.001'
    assert mapping[0]['import_path'] == str(mesh)
    with pytest.raises(ValueError, match='outside the preserved'):
        prepare_import_urdf(source, raw, raw / 'import.urdf')
    with pytest.raises(ValueError, match='outside raw'):
        mesh_path('anything', source, raw, {'anything': '../import.urdf'})


def test_root_package_fetch_excludes_git_and_preserves_license(tmp_path, monkeypatch):
    from dexterous_lab.assets import manager as module

    catalog = isolated_catalog(tmp_path)
    record = catalog.get('vendor/hand/right')
    source = tmp_path / 'research-repos/vendor_description'
    (source / '.git').mkdir(parents=True)
    (source / '.git/private').write_text('never copied')
    (source / 'model.urdf').write_text('<robot name="source"/>')
    (source / 'LICENSE').write_text('original license')
    catalog.update(record, download_status='not_downloaded', source_package='.', reference_checkout='vendor_description',
                   raw_prefix='vendor_description', source_commit='abc', source_file_path='model.urdf',
                   license={'status': 'reviewed', 'evidence_paths': ['LICENSE']})
    (catalog.directory(record) / 'raw').mkdir()
    monkeypatch.setattr(module, 'DATA_ROOT', tmp_path)
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *args, **kwargs: 'abc\n')
    fetched = AssetManager(catalog).fetch(record['asset_id'])
    raw = catalog.directory(record) / 'raw'
    assert fetched['status'] == 'fetched'
    assert not (raw / 'vendor_description/.git').exists()
    assert Path(fetched['metadata']['local_raw_path']).read_text() == '<robot name="source"/>'
    assert (raw / 'SOURCE_LICENSE').read_text() == 'original license'


def test_fixed_markers_allowed_but_dynamic_massless_links_rejected(tmp_path):
    source = tmp_path / 'model.urdf'
    inertial = '<inertial><mass value="0"/><inertia ixx="0" iyy="0" izz="0" ixy="0" ixz="0" iyz="0"/></inertial>'
    template = '''<robot name="marker"><link name="base"><collision><geometry><box size="1 1 1"/></geometry></collision></link>
      <link name="tip">%s</link><joint name="marker" type="%s"><parent link="base"/><child link="tip"/>
      <limit lower="0" upper="1"/></joint></robot>'''
    source.write_text(template % (inertial, 'fixed'))
    assert inspect_urdf(source, tmp_path)['passed']
    source.write_text(template % (inertial, 'revolute'))
    assert not inspect_urdf(source, tmp_path)['passed']
