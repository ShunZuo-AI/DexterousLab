"""Build the first source catalog from verified upstream paths; no placeholder models."""

import hashlib
import json
from pathlib import Path
import re

from dexterous_lab.assets.catalog import ASSET_ROOT, MANIFEST_ROOT, AssetCatalog, save_json
from dexterous_lab.config import PROJECT_ROOT


BASE = PROJECT_ROOT
MANUFACTURERS = {
    "wonik": "Wonik Robotics", "shadow_robot": "Shadow Robot", "leap": "LEAP Hand", "unitree": "Unitree Robotics",
    "wuji": "Wuji Technology", "brainco": "BrainCo", "linkerbot": "LinkerBot", "sharpa": "Sharpa",
    "inspire": "Inspire Robotics", "robotera": "RobotEra", "tesollo": "Tesollo", "psyonic": "PSYONIC",
    "schunk": "SCHUNK", "barrett": "Barrett Technology", "robotis": "ROBOTIS", "orca": "ORCA Dexterity",
    "roboparty": "RoboParty", "paxini": "PaXini", "xynova": "Xynova", "agilink": "AGILINK",
    "fourier": "Fourier", "ubtech": "UBTECH", "agibot": "AgiBot", "oymotion": "OYMotion",
    "casiahand": "CasiaHand", "dexrobot": "DexRobot", "ruka": "Ruka", "seed_robotics": "Seed Robotics",
    "qb_robotics": "qb robotics", "clone_robotics": "Clone Robotics",
}


def slug(value):
    return re.sub(r"[^a-z0-9_.-]+", "_", value.lower()).strip("_")


def main():
    catalog = AssetCatalog()
    if (MANIFEST_ROOT / "hands.json").exists():
        raise ValueError("Catalog already exists; refusing to overwrite recorded asset states")
    sources = []
    for filename in ("source_inventory.json", "additional_source_inventory.json"):
        sources.extend(json.loads((MANIFEST_ROOT / filename).read_text())["sources"])
    by_repo = {source["repository"]: source for source in sources}
    hands = []

    def add(manufacturer, model, variant, repository=None, source_file=None, **extra):
        source = by_repo.get(repository, {})
        if source_file and source_file not in {item['path'] for item in source.get('models', [])}:
            raise ValueError(f"Unverified source path: {repository}:{source_file}")
        record = {
            "category": "hands", "asset_id": f"{manufacturer}/{model}/{variant}", "manufacturer": manufacturer,
            "model": model, "variant": variant,
            "source_repository": "https://github.com/" + repository if repository else None,
            "source_commit": source.get("commit"), "source_file_path": source_file,
            "local_raw_path": None, "local_processed_path": None, "isaaclab_asset_path": None,
            "license": {"status": "not_reviewed", "evidence_paths": source.get("licenses", [])},
            "download_status": "not_downloaded" if source_file else "source_unresolved",
            "conversion_status": "not_run", "simulation_status": "not_run", "fetch_enabled": False,
            "notes": [],
        }
        record.update(extra)
        directory = catalog.directory(record)
        record["asset_directory"] = str(directory)
        for folder in ("raw", "processed", "isaaclab"):
            (directory / folder).mkdir(parents=True, exist_ok=True)
        save_json(directory / "metadata.json", record)
        save_json(directory / "validation.json", {"static_status": "not_run", "simulation_status": "not_run"})
        hands.append(record)
        return record

    for model, path in (
        ("dex1_1", "robots/dexterous_hand_description/dex1_1/dex1_1.urdf"),
        ("dex2_5", "robots/dexterous_hand_description/dex2_5/Left_Hand.urdf"),
        ("dex2_5", "robots/dexterous_hand_description/dex2_5/Right_Hand.urdf"),
        ("dex2_5", "robots/dexterous_hand_description/dex2_5/Left_Hand_G1_5010_Wrist.urdf"),
        ("dex2_5", "robots/dexterous_hand_description/dex2_5/Right_Hand_G1_5010_Wrist.urdf"),
        ("dex3_1", "robots/dexterous_hand_description/dex3_1/dex3_1_l.urdf"),
        ("dex3_1", "robots/dexterous_hand_description/dex3_1/dex3_1_r.urdf"),
        ("dex5_1", "robots/dexterous_hand_description/dex5_1/Dex5-URDF-L/Dex5-URDF-L.urdf"),
        ("dex5_1", "robots/dexterous_hand_description/dex5_1/Dex5-URDF-R/Dex5-URDF-R.urdf"),
    ):
        name = Path(path).stem
        side = "left" if "Left" in name or name.endswith(("_l", "-L")) else "right" if "Right" in name or name.endswith(("_r", "-R")) else "unspecified"
        variant = side + ("_g1_5010_wrist" if "Wrist" in name else "")
        add("unitree", model, variant, "unitreerobotics/unitree_ros", path,
            fetch_enabled=model == "dex3_1", source_package=f"robots/dexterous_hand_description/{model}",
            reference_checkout="unitree_ros", license={"status": "reviewed", "expression": "BSD-3-Clause", "evidence_paths": ["LICENSE"]})

    for model, prefix in (("hand_v1", "hand/body"), ("hand_v2", "hand2/hand2_1/body"), ("hand_v2", "hand2/hand2_2/body")):
        for side in ("left", "right"):
            revision = "" if model == "hand_v1" else ("2_1_" if "hand2_1" in prefix else "2_2_")
            usd_name = "wujihand" if model == "hand_v1" else "wujihand2_1" if "hand2_1" in prefix else "wujihand2_2"
            usd_path = f"{prefix}/usd/{side}/{usd_name}.usd"
            add("wuji", model, revision + side, "wuji-technology/wuji-description", usd_path,
                reference_checkout="wuji-description", source_package=prefix, companion_urdf=f"{prefix}/urdf/{side}.urdf",
                fetch_enabled=model == "hand_v1" and side == "right",
                license={"status": "reviewed", "expression": "MIT", "evidence_paths": ["LICENSE"]},
                notes=["Exact upstream revision retained; hand_v2 does not conflate Hand2.1 and Hand2.2"])

    add("leap", "leap_hand_v1", "right", "leap-hand/LEAP_Hand_Sim", "assets/leap_hand/robot.urdf",
        source_package="assets/leap_hand", reference_checkout="LEAP_Hand_Sim", fetch_enabled=True,
        license={"status": "reviewed", "expression": "MIT", "evidence_paths": ["LICENSE.txt"]},
        notes=["Isaac_Lab repository has native USD, but no license found there in scanned tree; choose licensed Sim source"])

    selectors = [
        ("wonik", "allegro", "dexsuite/dex-urdf", "robots/hands/allegro_hand/"),
        ("shadow_robot", "dexterous_hand", "dexsuite/dex-urdf", "robots/hands/shadow_hand/"),
        ("brainco", "revo2", "BrainCoTech/revo2_description", "urdf/"),
        ("robotera", "xhand", "facebookresearch/spider", "spider/assets/robots/xhand/"),
        ("tesollo", "dg5f", "tesollodelto/dg5f_ros2", "dg5f_description/urdf/"),
        ("psyonic", "ability_hand", "psyonicinc/ability-hand-api", "URDF/"),
        ("schunk", "svh", "dexsuite/dex-urdf", "robots/hands/schunk_hand/"),
        ("barrett", "barrett_hand", "dexsuite/dex-urdf", "robots/hands/barrett_hand/"),
        ("robotis", "hx5", "whats-lab/dexterous-hand-urdf", "dexhand_description/robotis_hx5_d20/"),
        ("inspire", "rh56", "haosulab/ManiSkill", "mani_skill/assets/robots/inspire_hand/"),
        ("orca", "orca_hand", "orcahand/orcahand_description", ""),
        ("dexrobot", "dexhand021", "DexRobot/dexrobot_urdf", "urdf/"),
        ("oymotion", "rohand", "oymotion/rohand_urdf_ros1", ""),
        ("ruka", "ruka", "ruka-hand/RUKA", ""),
        ("fourier", "fourier_hand", "FFTAI/Wiki-GRx-Models", ""),
    ]
    for manufacturer, model, repository, prefix in selectors:
        for item in by_repo.get(repository, {}).get("models", []):
            path = item["path"]
            if not path.startswith(prefix) or not path.endswith(".urdf"):
                continue
            if manufacturer == "fourier" and "hand" not in path.lower():
                continue
            add(manufacturer, model, slug(path.removeprefix(prefix).removesuffix(".urdf")), repository, path)

    for repository, manufacturer, model in (("linker-bot/linkerhand-urdf", "linkerbot", "linkerhand"),
                                            ("sharpa-robotics/sharpa-urdf-usd-xml", "sharpa", "sharpa_wave")):
        for item in by_repo[repository]["models"]:
            path = item["path"]
            if not path.endswith(".urdf"):
                continue
            parts = Path(path).parts
            actual_model = model + "_" + slug(parts[1] if parts[0] == "archive" else parts[0])
            if manufacturer == "sharpa" and parts[0] != "wave_01":
                actual_model = "d01_" + slug(parts[1])
            add(manufacturer, actual_model, slug("_".join(parts[1:]).removesuffix(".urdf")), repository, path,
                notes=["Model split follows actual upstream directory; archival variants remain distinct"])

    for item in by_repo["shadow-robot/dx_common"]["models"]:
        if item['path'].startswith("dx_description/robot/") and item['path'].endswith(".urdf.xacro"):
            add("shadow_robot", "dex_ee", Path(item['path']).name.removesuffix('.urdf.xacro'), "shadow-robot/dx_common", item['path'],
                notes=["Upstream device identifier preserved; xacro requires expansion, no ready URDF is claimed"])

    from dexterous_lab.runtime import arena_root
    isaac_root = arena_root() / "submodules/IsaacLab"
    isaac_commit = "e3f7d9ff1f5d7f8280de3ece9000b7117f66bcf4"
    official = [
        ("wonik", "allegro", "isaaclab_standalone", "allegro.py", "ALLEGRO_HAND_CFG", "Robots/WonikRobotics/AllegroHand/allegro_hand_instanceable.usd", None),
        ("wonik", "allegro", "right_kuka", "kuka_allegro.py", "KUKA_ALLEGRO_CFG", "IsaacLab/Robots/KukaAllegro/kuka.usd", "allegro"),
        ("shadow_robot", "dexterous_hand", "right_isaaclab", "shadow_hand.py", "SHADOW_HAND_PHYSX_CFG", "Robots_Multiphysics/ShadowRobot/ShadowHandMultiPhysics_v0/right_hand/right_hand.usda", "shadow"),
    ]
    for manufacturer, model, variant, filename, symbol, asset, scene_hand in official:
        record = add(manufacturer, model, variant,
            source_repository="https://github.com/isaac-sim/IsaacLab", source_commit=isaac_commit,
            source_file_path=f"source/isaaclab_assets/isaaclab_assets/robots/{filename}",
            isaaclab_asset_path=f"isaaclab_assets.robots.{filename[:-3]}:{symbol}",
            official_usd_url="https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/6.2/Isaac/" + asset,
            download_status="official_reference", fetch_enabled=True,
            license={"status": "official_reference_only", "expression": "NVIDIA asset terms; config code BSD-3-Clause", "evidence_paths": [str(isaac_root / "source/isaaclab_assets/isaaclab_assets/robots" / filename)]},
            scene_hand=scene_hand, notes=["Official remote asset reference permitted; no wholesale USD redistribution", "Side/version only asserted when present in upstream path; standalone Allegro revision unspecified"])
        config_path = isaac_root / record['source_file_path']
        record['source_config_sha256'] = hashlib.sha256(config_path.read_bytes()).hexdigest()
        save_json(catalog.directory(record) / "metadata.json", record)

    for manufacturer, model, repository, note in (
        ("roboparty", "rp_hand", "Roboparty/rp_dexhand", "Tree contains no standalone URDF/USD; inspect downloadable release/archive separately"),
        ("paxini", "unresolved", None, "Searched public repositories; no verified manufacturer model path in first pass"),
        ("xynova", "unresolved", None, "No verified public model path in first-pass search"),
        ("agilink", "unresolved", "AgibotTech/agillink_omnihand_sdk", "SDK docs found but API source scan unavailable; do not infer asset files from joint tables"),
        ("agibot", "unresolved", "AgibotTech/agillink_omnihand_sdk", "Manufacturer affiliation/model availability still needs source confirmation"),
        ("ubtech", "hand_unresolved", "UBTECH-Robot/Walker_TienKung_URDF", "Public humanoid descriptions found; no standalone hand variant verified"),
        ("casiahand", "unresolved", None, "No verified public hand model found in first-pass search"),
        ("seed_robotics", "unresolved", "seedrobotics/ros_robothands", "Candidate repository unavailable; not evidence that no public assets exist"),
        ("qb_robotics", "unresolved", "qbrobotics/qbhand-ros", "Candidate GitHub repository unavailable; additional official hosting research needed"),
        ("clone_robotics", "unresolved", "CloneRobotics/Clone", "Candidate repository unavailable; no actual model path verified"),
    ):
        add(manufacturer, model, "unresolved", repository, notes=[note])

    if len({record['asset_id'] for record in hands}) != len(hands):
        raise ValueError("Duplicate asset identifiers")
    manufacturers = []
    for identifier, name in MANUFACTURERS.items():
        manufacturers.append({"manufacturer": identifier, "name": name,
                              "asset_count": sum(record['manufacturer'] == identifier for record in hands),
                              "source_status": "indexed" if any(record['manufacturer'] == identifier and record['source_file_path'] for record in hands) else "unresolved"})
    objects = []
    for collection, url in (("ycb", "https://www.ycbbenchmarks.com/object-models/"),
                            ("dexgraspnet", "https://github.com/PKU-EPIC/DexGraspNet"),
                            ("objaverse", "https://objaverse.allenai.org/"),
                            ("maniskill", "https://github.com/haosulab/ManiSkill")):
        record = {"category": "objects", "asset_id": f"{collection}/collection", "manufacturer": None,
                  "model": collection, "variant": "collection", "source_repository": url,
                  "source_commit": "bd1b13d7248729af117e1d46aaa6266b147a3c7b" if collection == 'dexgraspnet' else by_repo['haosulab/ManiSkill']['commit'] if collection == 'maniskill' else None,
                  "source_file_path": None, "local_raw_path": None, "local_processed_path": None,
                  "isaaclab_asset_path": None, "license": {"status": "per_object_review_required"},
                  "download_status": "not_downloaded", "conversion_status": "not_run", "simulation_status": "not_run",
                  "fetch_enabled": False, "notes": ["Collection metadata only; no per-object mesh or ready-to-use dataset claimed"]}
        directory = catalog.directory(record)
        for folder in ("raw", "processed"):
            (directory / folder).mkdir(parents=True, exist_ok=True)
        save_json(directory / "metadata.json", record)
        save_json(directory / "validation.json", {"static_status": "not_run", "simulation_status": "not_run"})
        objects.append(record)
    for kind in ("cube", "cylinder", "sphere"):
        record = {"category": "objects", "asset_id": f"custom/{kind}", "manufacturer": "dexterouslab",
                  "model": kind, "variant": "procedural_v1", "source_repository": str(PROJECT_ROOT), "source_commit": None,
                  "source_file_path": f"configs/objects/{kind}.toml", "local_raw_path": None, "local_processed_path": None,
                  "isaaclab_asset_path": "dexterous_lab.assets.primitives:" + kind.capitalize(),
                  "license": {"status": "project_generated_geometry"}, "download_status": "procedural",
                  "conversion_status": "not_run", "simulation_status": "not_run", "fetch_enabled": True,
                  "scene_object": kind, "notes": ["Simulation status will only be updated from a new successful validation run"]}
        directory = catalog.directory(record)
        for folder in ("raw", "processed"):
            (directory / folder).mkdir(parents=True, exist_ok=True)
        save_json(directory / "metadata.json", record)
        save_json(directory / "validation.json", {"static_status": "not_run", "simulation_status": "not_run"})
        objects.append(record)
    save_json(MANIFEST_ROOT / "hands.json", {"schema_version": "1.0", "hands": hands})
    save_json(MANIFEST_ROOT / "manufacturers.json", {"schema_version": "1.0", "manufacturers": manufacturers})
    save_json(MANIFEST_ROOT / "objects.json", {"schema_version": "1.0", "objects": objects})
    print(f"Indexed {len(hands)} hand variants, {len(manufacturers)} manufacturers, {len(objects)} object/collection records")


if __name__ == "__main__":
    main()
