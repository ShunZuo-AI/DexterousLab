"""Static URDF checks that never execute source scripts or change original models."""

from math import isfinite
from pathlib import Path
import xml.etree.ElementTree as ET

from dexterous_lab.assets.catalog import sha256_file


def prepare_import_urdf(source, raw_root, destination, mesh_aliases=None):
    """Expand verified mesh references in a derivative, preserving source bytes and joint semantics."""
    source, raw_root, destination = Path(source), Path(raw_root), Path(destination)
    if destination.resolve().is_relative_to(raw_root.resolve()):
        raise ValueError('Import derivatives must be outside the preserved raw package')
    tree = ET.parse(source)
    mapping = []
    for element in tree.findall('.//mesh'):
        original = element.get('filename', '')
        absolute = str(mesh_path(original, source, raw_root, mesh_aliases))
        element.set('filename', absolute)
        mapping.append({'source': original, 'import_path': absolute})
    tree.write(destination, encoding='utf-8', xml_declaration=True)
    return mapping


def mesh_path(filename, model_path, raw_root, aliases=None):
    if filename in (aliases or {}):
        resolved = (raw_root / aliases[filename]).resolve()
    elif filename.startswith("package://"):
        package, _, relative = filename[len("package://"):].partition("/")
        directories = [raw_root] + [path for path in raw_root.rglob(package) if path.is_dir()]
        candidates = [path / relative for path in directories if path.name == package]
        existing = [path.resolve() for path in candidates if path.is_file()]
        if len(set(existing)) != 1:
            raise ValueError(f"Unresolved package mesh: {filename}")
        resolved = existing[0]
    elif "://" in filename:
        raise ValueError(f"Remote mesh dependencies are not auto-fetched: {filename}")
    else:
        resolved = (model_path.parent / filename).resolve()
    if not resolved.is_relative_to(raw_root.resolve()) or not resolved.is_file():
        raise ValueError(f"Missing mesh or path outside raw package: {filename}")
    return resolved


def inspect_urdf(model_path, raw_root, mesh_aliases=None):
    import numpy as np
    import trimesh

    model_path, raw_root = Path(model_path), Path(raw_root)
    tree = ET.parse(model_path)
    if tree.getroot().tag != "robot":
        raise ValueError("Expected a complete URDF <robot>, not an xacro template")
    failures, warnings, meshes, joints = [], [], [], []
    links = tree.findall("link")
    link_names = [link.get("name") for link in links]
    if len(set(link_names)) != len(link_names) or not links:
        failures.append("Empty or duplicate link names")
    for joint in tree.findall("joint"):
        joint_type = joint.get("type")
        entry = {"name": joint.get("name"), "type": joint_type}
        for element in ("parent", "child"):
            node = joint.find(element)
            if node is None or node.get("link") not in link_names:
                failures.append(f"Invalid {element} for joint {entry['name']}")
        if joint_type not in ("fixed", "floating"):
            axis = joint.find("axis")
            values = [float(value) for value in (axis.get("xyz", "1 0 0") if axis is not None else "1 0 0").split()]
            if len(values) != 3 or not all(isfinite(value) for value in values) or np.linalg.norm(values) < 1e-8:
                failures.append(f"Invalid axis: {entry['name']}")
            limit = joint.find("limit")
            if joint_type != "continuous":
                if limit is None or "lower" not in limit.attrib or "upper" not in limit.attrib:
                    failures.append(f"Missing joint limits: {entry['name']}")
                else:
                    lower, upper = float(limit.get("lower")), float(limit.get("upper"))
                    entry.update(lower=lower, upper=upper)
                    if not isfinite(lower) or not isfinite(upper) or lower > upper:
                        failures.append(f"Invalid joint limits: {entry['name']}")
        mimic = joint.find("mimic")
        entry["mimic"] = dict(mimic.attrib) if mimic is not None else None
        joints.append(entry)
    for link in links:
        name = link.get("name")
        mass, inertia = link.find("inertial/mass"), link.find("inertial/inertia")
        if mass is None or inertia is None:
            warnings.append(f"Missing inertial data for {name}; fixed/marker links may be intentional")
        else:
            value = float(mass.get("value", "nan"))
            values = {key: float(inertia.get(key, "nan")) for key in ("ixx", "iyy", "izz", "ixy", "ixz", "iyz")}
            matrix = np.array([[values['ixx'], values['ixy'], values['ixz']],
                               [values['ixy'], values['iyy'], values['iyz']],
                               [values['ixz'], values['iyz'], values['izz']]])
            incoming = [joint for joint in tree.findall('joint')
                        if joint.find('child') is not None and joint.find('child').get('link') == name]
            fixed_marker = (value == 0 and np.all(matrix == 0) and not link.findall('collision')
                            and not link.findall('visual') and all(joint.get('type') == 'fixed' for joint in incoming))
            if fixed_marker:
                warnings.append(f"Massless fixed reference frame: {name}; merge fixed joints when importing")
            elif not isfinite(value) or value <= 0 or not np.isfinite(matrix).all() or np.linalg.eigvalsh(matrix).min() <= 0:
                failures.append(f"Nonpositive/nonfinite mass or inertia: {name}")
        if not link.findall("collision"):
            warnings.append(f"No collision geometry for {name}")
    for element in tree.findall(".//mesh"):
        filename = element.get("filename", "")
        try:
            path = mesh_path(filename, model_path, raw_root, mesh_aliases)
            scale = np.array([float(value) for value in element.get("scale", "1 1 1").split()])
            if scale.shape != (3,) or not np.isfinite(scale).all() or (scale <= 0).any():
                raise ValueError("Invalid mesh scale")
            mesh = trimesh.load(path, force="mesh", process=False)
            if len(mesh.vertices) == 0 or len(mesh.faces) == 0 or not np.isfinite(mesh.vertices).all():
                raise ValueError("Empty or nonfinite mesh")
            extents = (mesh.extents * scale).tolist()
            if max(extents) > 2 or max(extents) < 1e-5:
                warnings.append(f"Check metric scale for {filename}: extents={extents}")
            meshes.append({"reference": filename, "path": str(path), "sha256": sha256_file(path),
                           "scale": scale.tolist(), "extents_m": extents, "watertight": bool(mesh.is_watertight)})
        except (ValueError, OSError, ImportError) as exc:
            failures.append(f"Mesh {filename}: {exc}")
    collision_count = len(tree.findall(".//collision/geometry"))
    if collision_count == 0:
        failures.append("No collision geometry in model")
    names = [joint['name'] for joint in joints]
    if len(set(names)) != len(names):
        failures.append("Duplicate joint names")
    return {"passed": not failures, "model_path": str(model_path), "sha256": sha256_file(model_path),
            "links": link_names, "joints": joints, "meshes": meshes,
            "collision_geometry_count": collision_count, "failures": failures, "warnings": warnings,
            "simulation_status": "not_run", "scope": "static source checks; not physics validation"}
