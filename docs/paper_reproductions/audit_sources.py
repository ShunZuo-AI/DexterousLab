"""Record source revisions and function locations without importing paper code."""

import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path("/root/gpufree-data")
DESTINATION = ROOT / "DexterousLab/docs/paper_reproductions/source_manifest.json"
SELECTIONS = {
    "DexGraspNet": ["README.md", "grasp_generation/README.md", "grasp_generation/main.py",
                   "grasp_generation/scripts/generate_grasps.py", "grasp_generation/scripts/validate_grasps.py",
                   "grasp_generation/utils/hand_model.py", "grasp_generation/utils/object_model.py",
                   "grasp_generation/utils/initializations.py", "grasp_generation/utils/energy.py",
                   "grasp_generation/utils/optimizer.py", "grasp_generation/utils/isaac_validator.py",
                   "grasp_generation/mjcf/shadow_hand_wrist_free.xml", "grasp_generation/mjcf/contact_points.json",
                   "grasp_generation/mjcf/penetration_points.json", "asset_process/README.md",
                   "asset_process/normalize.py", "asset_process/decompose.py"],
    "GenDexGrasp": ["README.md", "requirements.yaml", "train_cvae.py", "train_cvae_criterion.py",
                    "inf_cvae.py", "run_grasp_gen.py", "run_grasp_test.py", "utils_model/PointNetCVAE.py",
                    "utils_model/CMapAdam.py", "utils_model/AdamGrasp.py", "utils_model/HandModel.py",
                    "utils/get_models.py", "envs/tasks/grasp_test_force_shadowhand.py",
                    "envs/tasks/grasp_test_force.yaml"],
    "DexGraspNet2": ["README.md", "src/train.py", "src/network/model.py", "src/network/graspness_sample.py",
                     "src/eval/predict_dexterous.py", "src/eval/evaluate_dexterous.py",
                     "src/utils/robot_model.py", "src/utils/collision_checker.py",
                     "src/utils/data_evaluator/simulation_evaluator.py", "src/utils/simulator/isaacgym_simulator.py",
                     "src/preprocess/refine_dataset.py", "src/preprocess/dex_graspness.py"],
    "TorchSDF": ["README.md", "LICENSE", "torchsdf/sdf.py", "torchsdf/csrc/unbatched_triangle_distance.cpp"],
    "IsaacLab-Arena": ["README.md", "isaaclab_arena/environments/arena_env_builder.py",
                       "isaaclab_arena/environments/arena_environment_factory.py",
                       "isaaclab_arena/embodiments/embodiment_base.py",
                       "isaaclab_arena/embodiments/kuka_allegro/kuka_allegro.py"],
    "IsaacLab": ["source/isaaclab_assets/isaaclab_assets/robots/shadow_hand.py",
                 "source/isaaclab/isaaclab/utils/math.py",
                 "source/isaaclab/isaaclab/envs/mdp/actions/tendon_actions.py",
                 "source/isaaclab/isaaclab/assets/articulation/base_articulation.py"],
}


def git(path, *arguments):
    return subprocess.check_output(
        ["git", "-c", "filter.lfs.process=", "-c", "filter.lfs.required=false", "-c", "filter.lfs.clean=",
         "-C", str(path), *arguments], text=True,
    ).strip()


def declarations(nodes, prefix=""):
    result = []
    for node in nodes:
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            name = prefix + node.name
            result.append({"name": name, "line": node.lineno, "end_line": node.end_lineno})
            result.extend(declarations(node.body, name + "."))
    return result


def main():
    report = {"recorded_utc": datetime.now(timezone.utc).isoformat(), "repositories": {}}
    for name, files in SELECTIONS.items():
        path = ROOT / "research-repos" / name
        entry = {"path": str(path.resolve()), "commit": git(path, "rev-parse", "HEAD"),
                 "working_tree_status": git(path, "status", "--porcelain"), "files": {}}
        for relative in files:
            source = path / relative
            data = source.read_bytes()
            details = {"path": str(source.resolve()), "sha256": hashlib.sha256(data).hexdigest()}
            if source.suffix == ".py":
                details["declarations"] = declarations(ast.parse(data).body)
            entry["files"][relative] = details
        report["repositories"][name] = entry
    report["dexgraspnet_allegro_branch_commit"] = git(ROOT / "research-repos/DexGraspNet", "rev-parse", "FETCH_HEAD")
    with DESTINATION.open("x") as stream:
        json.dump(report, stream, indent=2)
    print(DESTINATION)


if __name__ == "__main__":
    main()
