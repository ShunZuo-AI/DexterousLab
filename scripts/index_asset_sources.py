"""Inspect public source trees without downloading model payloads or running installers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES = [
    "pal-robotics/allegro_hand", "dexsuite/dex-urdf", "shadow-robot/sr_common", "shadow-robot/dx_common",
    "leap-hand/LEAP_Hand_Isaac_Lab", "leap-hand/LEAP_Hand_Sim", "unitreerobotics/unitree_ros",
    "wuji-technology/wuji-description", "BrainCoTech/revo2_description", "BrainCoTech/brainco_hand_ros2",
    "linker-bot/linkerhand-urdf", "linker-bot/linkerhand-ros2-sdk", "sharpa-robotics/sharpa-urdf-usd-xml",
    "renesas-rdk/inspire_rh56_hand_description", "facebookresearch/spider", "tesollodelto/dg5f_ros2",
    "tesollodelto/tesollo_ros2", "psyonicinc/ability-hand-api", "whats-lab/dexterous-hand-urdf",
    "orcahand/orcahand_description", "Roboparty/rp_dexhand", "haosulab/ManiSkill",
]


def request_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "DexterousLab-source-inventory", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def inspect(repository):
    result = {"repository": repository, "url": "https://github.com/" + repository}
    try:
        revision = request_json(f"https://api.github.com/repos/{repository}/commits/HEAD")
        result["commit"] = revision["sha"]
        tree = request_json(f"https://api.github.com/repos/{repository}/git/trees/{revision['commit']['tree']['sha']}?recursive=1")
        result["tree_truncated"] = tree.get("truncated", False)
        result["models"] = []
        result["licenses"] = []
        result["readmes"] = []
        for item in tree.get("tree", []):
            path = item["path"]
            if item["type"] != "blob":
                continue
            if Path(path).suffix.lower() in (".urdf", ".xacro", ".usd", ".usda", ".usdc", ".xml", ".mjcf"):
                result["models"].append({"path": path, "git_blob_sha": item["sha"], "size": item.get("size")})
            basename = Path(path).name.lower()
            if any(token in basename for token in ("license", "copying", "notice")):
                result["licenses"].append(path)
            if basename.startswith("readme"):
                result["readmes"].append(path)
        result["status"] = "tree_inspected" if not result["tree_truncated"] else "partial_tree"
    except (urllib.error.URLError, ValueError, KeyError) as exc:
        result["status"] = "unavailable"
        result["error"] = str(exc)
    return result


def main():
    destination = ROOT / "assets/manifests"
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        for record in executor.map(inspect, REPOSITORIES):
            records.append(record)
            print(record["repository"], record["status"], len(record.get("models", [])), flush=True)
    path = destination / "source_inventory.json"
    with path.open("x") as stream:
        json.dump({"inspected_utc": datetime.now(timezone.utc).isoformat(), "sources": records}, stream, indent=2)


if __name__ == "__main__":
    main()
