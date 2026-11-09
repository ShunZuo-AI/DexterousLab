"""Small-batch asset retrieval, conversion and validation with explicit status."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

from dexterous_lab.assets.catalog import AssetCatalog, save_json, sha256_file
from dexterous_lab.assets.checks import inspect_urdf
from dexterous_lab.config import CONFIG_ROOT, checked_dataclass, named_config, ObjectConfig
from dexterous_lab.runtime import arena_root, run_worker, runtime_environment, shared_python
from dexterous_lab.storage import DATA_ROOT


def check_space(destination, requested_bytes=0):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(destination).free
    if free < requested_bytes + 2 * 1024 ** 3:
        raise ValueError("Insufficient disk space: keep at least 2 GiB free beyond the requested package")
    return free


def package_fingerprints(root):
    result = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            result.append({"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return result


class AssetManager:
    def __init__(self, catalog=None):
        self.catalog = catalog or AssetCatalog()

    def preview(self, asset_id, seconds=600):
        """Launch a bounded desktop viewer and return its PID and log directory."""
        record = self.catalog.get(asset_id)
        if seconds < 1 or seconds > 3600:
            raise ValueError('Preview duration must be between 1 and 3600 seconds')
        if not os.environ.get('DISPLAY'):
            raise ValueError('Desktop preview requires DISPLAY; run from the server cloud desktop terminal')
        if record.get('simulation_status') != 'passed':
            raise ValueError('Preview is currently enabled only for assets with successful physics validation')
        if not record.get('isaaclab_asset_path'):
            raise ValueError('No simulation-ready asset reference is registered')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        run_dir = self.catalog.directory(record) / 'runs' / f'{stamp}-preview-{uuid.uuid4().hex[:8]}'
        run_dir.mkdir(parents=True, exist_ok=False)
        request = {'asset': record, 'action': 'preview', 'seconds': seconds, 'steps': 0, 'run_dir': str(run_dir)}
        save_json(run_dir / 'request.json', request)
        command = [shared_python(), '-m', 'dexterous_lab.assets.worker', str(run_dir / 'request.json')]
        with (run_dir / 'simulation.log').open('x') as stream:
            child = subprocess.Popen(command, env=runtime_environment(), cwd=run_dir,
                                     stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        result = {'status': 'starting', 'pid': child.pid, 'asset_id': asset_id, 'display': os.environ['DISPLAY'],
                  'seconds': seconds, 'run_directory': str(run_dir), 'command': command,
                  'notice': 'Window appears on the server cloud desktop; ready.json confirms initialization, not grasp success'}
        save_json(run_dir / 'launch.json', result)
        return result

    def fetch(self, asset_id):
        record = self.catalog.get(asset_id)
        if not record.get("fetch_enabled"):
            raise ValueError(f"Fetch not enabled for {asset_id}: source package/license/dependencies are not approved in this first batch")
        directory = self.catalog.directory(record)
        check_space(self.catalog.asset_root)
        if record.get("download_status") in ("fetched", "generated", "reference_recorded"):
            manifest = directory / "checksums.json"
            if not manifest.is_file():
                raise ValueError("Previously fetched asset has no checksum manifest")
            for entry in json.loads(manifest.read_text()):
                if sha256_file(directory / "raw" / entry["path"]) != entry["sha256"]:
                    raise ValueError(f"Raw asset changed since fetch: {entry['path']}")
            return {"asset_id": asset_id, "status": "already_present", "metadata": record}
        raw = directory / "raw"
        if any(raw.iterdir()) and (record.get("official_usd_url") or not record.get("source_package")):
            raise ValueError("Raw directory is nonempty but has no completed fetch record; preserve it and inspect before retrying")
        if record.get("official_usd_url"):
            reference = {"source": record['official_usd_url'], "isaaclab_config": record['isaaclab_asset_path'],
                         "source_commit": record['source_commit'], "policy": "Official remote reference; not a downloaded USD"}
            save_json(raw / "official_reference.json", reference)
            config_path = arena_root() / "submodules/IsaacLab" / record['source_file_path']
            shutil.copy2(config_path, raw / config_path.name)
            status, model_path = "reference_recorded", None
        elif record["category"] == "objects" and record.get("scene_object"):
            from dexterous_lab.objects.mesh import get_object_mesh

            configuration = checked_dataclass(ObjectConfig, named_config("objects", record['scene_object']))
            shutil.copy2(CONFIG_ROOT / "objects" / f"{record['scene_object']}.toml", raw / "source.toml")
            get_object_mesh(configuration).export(raw / "mesh.obj")
            status, model_path = "generated", str(raw / "mesh.obj")
        else:
            if record["license"].get("status") != "reviewed":
                raise ValueError("Source license has not been reviewed")
            checkout = DATA_ROOT / "research-repos" / record["reference_checkout"]
            if not (checkout / ".git").is_dir():
                raise ValueError(f"Reference checkout missing: {checkout}; no implicit downloads")
            revision = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
            if revision != record["source_commit"]:
                raise ValueError("Reference checkout revision differs from indexed asset")
            package = checkout / record["source_package"]
            if not package.is_dir():
                raise ValueError(f"Source package is not present in sparse checkout: {package}")
            total = sum(path.stat().st_size for path in package.rglob("*") if path.is_file() and '.git' not in path.relative_to(package).parts)
            check_space(raw, total)
            prefix = record.get('raw_prefix', '')
            destination = raw / prefix / record["source_package"]
            for existing in raw.rglob("*"):
                if existing.is_file():
                    relative = existing.relative_to(raw)
                    if existing.name.startswith('SOURCE_'):
                        originals = [checkout / p for p in record['license']['evidence_paths'] if 'SOURCE_' + '__'.join(Path(p).parts) == existing.name]
                        original = originals[0] if len(originals) == 1 else Path('/nonexistent')
                    else:
                        original = checkout / relative.relative_to(prefix) if prefix else checkout / relative
                    if not original.is_file() or sha256_file(existing) != sha256_file(original):
                        raise ValueError(f"Incomplete fetch contains unknown/changed file: {existing}")
            shutil.copytree(package, destination, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.git'))
            for license_path in record['license']['evidence_paths']:
                source = checkout / license_path
                if not source.is_file():
                    raise ValueError(f"Missing license evidence: {source}")
                shutil.copy2(source, raw / ("SOURCE_" + '__'.join(Path(license_path).parts)))
            model_path = str(raw / prefix / record["source_file_path"])
            if not Path(model_path).is_file():
                raise ValueError(f"Source model missing after fetch: {model_path}")
            status = "fetched"
        fingerprints = package_fingerprints(raw)
        save_json(directory / "checksums.json", fingerprints)
        record = self.catalog.update(record, download_status=status, local_raw_path=model_path,
                                     checksum_manifest=str(directory / "checksums.json"))
        return {"asset_id": asset_id, "status": status, "file_count": len(fingerprints), "metadata": record}

    def run_job(self, record, action, steps=100, timeout=300):
        directory = self.catalog.directory(record)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_dir = directory / "runs" / f"{stamp}-{action}-{uuid.uuid4().hex[:8]}"
        run_dir.mkdir(parents=True, exist_ok=False)
        request = {"asset": record, "action": action, "steps": steps, "run_dir": str(run_dir),
                   "processed_directory": str(directory / "processed" / run_dir.name)}
        save_json(run_dir / "request.json", request)
        command = [shared_python(), "-m", "dexterous_lab.assets.worker", str(run_dir / "request.json")]
        with (run_dir / "simulation.log").open("x") as stream:
            child = subprocess.Popen(command, env=runtime_environment(), cwd=run_dir, stdout=stream, stderr=subprocess.STDOUT)
            try:
                code = child.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                code = -1
        evidence = run_dir / "evidence.json"
        result = json.loads(evidence.read_text()) if evidence.is_file() else {}
        passed = code == 0 and result.get("completed") is True
        if action == "validate":
            passed = passed and result.get("steps_completed") == steps
        save_json(run_dir / "result.json", {"passed": passed, "return_code": code, "command": command, "evidence": result})
        if not passed:
            self.catalog.update(record, **{("conversion_status" if action == 'convert' else 'simulation_status'): "failed"}, last_run=str(run_dir))
            if action == 'validate':
                save_json(directory / 'validation.json', {"simulation_status": "failed", "run_directory": str(run_dir),
                                                         "return_code": code, "evidence": result})
            raise ValueError(f"Asset {action} failed; see {run_dir / 'simulation.log'}")
        return run_dir, result

    def convert(self, asset_id, output_format="usd"):
        record = self.catalog.get(asset_id)
        if output_format != "usd":
            raise ValueError("Only USD conversion is implemented")
        if record.get("official_usd_url"):
            raise ValueError("Official USD is referenced directly; conversion is not required or performed")
        if record['download_status'] != "fetched" or not record.get('local_raw_path'):
            raise ValueError("Fetch the approved source asset before conversion")
        source = Path(record['local_raw_path'])
        if record.get('local_processed_path') and Path(record['local_processed_path']).is_file():
            return {"status": "already_converted", "path": record['local_processed_path']}
        if source.suffix.lower() in ('.usd', '.usda', '.usdc'):
            self.catalog.update(record, conversion_status="native_usd_no_conversion", local_processed_path=None,
                                isaaclab_asset_path=str(source))
            return {"status": "native_usd_no_conversion", "source_path": str(source), "processed_path": None}
        if source.suffix.lower() != '.urdf':
            raise ValueError("Conversion for this source format is not implemented; xacro expansion is not implicit")
        report = inspect_urdf(source, self.catalog.directory(record) / 'raw', record.get('mesh_aliases'))
        save_json(self.catalog.directory(record) / 'static_validation.json', report)
        if not report['passed']:
            self.catalog.update(record, conversion_status='blocked_static_checks', blocking_reason='; '.join(report['failures']))
            raise ValueError("Static source checks failed; refusing conversion")
        run_dir, result = self.run_job(record, 'convert')
        converted = Path(result['usd_path'])
        converted_checksums = self.catalog.directory(record) / 'processed' / run_dir.name / 'checksums.json'
        save_json(converted_checksums, package_fingerprints(converted_checksums.parent))
        self.catalog.update(record, conversion_status="converted", local_processed_path=str(converted),
                            isaaclab_asset_path=str(converted), processed_sha256=sha256_file(converted),
                            processed_checksum_manifest=str(converted_checksums), last_run=str(run_dir))
        save_json(self.catalog.directory(record) / 'isaaclab/config.json', {
            "usd_path": str(converted), "adapter": "dexterous_lab.assets.worker:validate",
            "parameters": result['parameters'], "scope": "asset smoke configuration; not a calibrated hand controller"})
        return {"status": "converted", "usd_path": str(converted), "run_dir": str(run_dir)}

    def validate(self, asset_id, steps=100):
        if steps < 1 or steps > 1000:
            raise ValueError("Asset validation requires 1 to 1000 steps")
        record = self.catalog.get(asset_id)
        directory = self.catalog.directory(record)
        if record.get('scene_hand') or record.get('scene_object'):
            from dexterous_lab.config import load_scene

            specification = load_scene(hand=record.get('scene_hand') or 'allegro', object_id=record.get('scene_object') or 'cube')
            request = {"kind": "scene", "config": specification, "backend": "physx", "steps": steps,
                       "num_envs": 1, "seed": 42, "policy": "zero_action"}
            status = run_worker(request, directory / 'runs')
            if status:
                self.catalog.update(record, simulation_status="failed", last_run=request['run_dir'])
                raise ValueError(f"Simulation failed: {request['run_dir']}")
            evidence = json.loads((Path(request['run_dir']) / 'simulation_result.json').read_text())
            save_json(directory / 'validation.json', {"simulation_status": "passed", "scope": "zero-action smoke only; not grasp success",
                      "run_directory": request['run_dir'], "evidence": evidence})
            self.catalog.update(record, simulation_status="passed", last_run=request['run_dir'])
            return {"status": "passed", "run_directory": request['run_dir']}
        if record.get('local_raw_path') and Path(record['local_raw_path']).suffix == '.urdf':
            static = inspect_urdf(record['local_raw_path'], directory / 'raw', record.get('mesh_aliases'))
            save_json(directory / 'static_validation.json', static)
            if not static['passed']:
                raise ValueError("Static checks failed; see static_validation.json")
        if not record.get('official_usd_url') and not record.get('isaaclab_asset_path'):
            raise ValueError("No simulation-ready USD/config is registered; fetch/convert first")
        run_dir, result = self.run_job(record, 'validate', steps)
        save_json(directory / 'isaaclab/validation_config.json', {
            "asset_reference": record['isaaclab_asset_path'], "adapter": "dexterous_lab.assets.worker:validate",
            "initial_joint_positions": result['initial_joint_positions'], "joint_names": result['joint_names'],
            "control": "source configuration defaults for official assets; otherwise zero projected into USD limits",
            "physics": "physx", "scope": "smoke configuration; not calibrated task control"})
        save_json(directory / 'validation.json', {"simulation_status": "passed", "run_directory": str(run_dir), "evidence": result})
        self.catalog.update(record, simulation_status="passed", last_run=str(run_dir), blocking_reason=None)
        return {"status": "passed", "run_directory": str(run_dir)}
