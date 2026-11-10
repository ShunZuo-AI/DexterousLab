"""Parse commands and dispatch work without importing the simulator."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from dexterous_lab.config import CONFIG_ROOT, load_scene, named_config
from dexterous_lab.runtime import arena_root, run_worker, runtime_environment, shared_python
from dexterous_lab.storage import storage_environment


def positive_int(value):
    """Parse a strictly positive integer command argument."""
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return result


def print_json(value):
    """Print the JSON representation used by CLI commands."""
    print(json.dumps(value, indent=2))


def doctor():
    probe = """import importlib.metadata as m, json, sys, torch
versions = {}
for name in ('torch', 'isaacsim', 'isaaclab', 'isaaclab_arena', 'pytest'):
    try: versions[name] = m.version(name)
    except m.PackageNotFoundError: versions[name] = None
cuda = torch.cuda.is_available()
inverse = False
if cuda:
    torch.linalg.inv(torch.eye(3, device='cuda'))
    torch.cuda.synchronize()
    inverse = True
print(json.dumps(dict(executable=sys.executable, prefix=sys.prefix, versions=versions,
                     cuda=cuda, gpu=torch.cuda.get_device_name(0) if cuda else None,
                     cuda_matrix_inverse=inverse)))
"""
    child = subprocess.run([shared_python(), "-c", probe], env=runtime_environment(), capture_output=True, text=True)
    if child.returncode:
        print(child.stderr, file=sys.stderr)
        return 1
    report = json.loads(child.stdout)
    report["arena_root"] = str(arena_root())
    report["ld_library_path"] = runtime_environment()["LD_LIBRARY_PATH"]
    report["storage"] = storage_environment()
    report["same_environment"] = Path(report["prefix"]).absolute() == (arena_root() / ".venv").absolute()
    report["ready"] = report["same_environment"] and report["cuda_matrix_inverse"] and all(report["versions"].values())
    print(json.dumps(report, indent=2))
    return 0 if report["ready"] else 1


def _add_experiment_commands(commands):
    experiments = commands.add_parser("experiment").add_subparsers(
        dest="action", required=True
    )
    for mode in ("capture", "replay", "batch"):
        parser = experiments.add_parser(mode)
        parser.add_argument(
            "--object", dest="object_id",
            choices=("cube", "sphere", "cylinder"), default="cube",
        )
        parser.add_argument("--include-sphere", action="store_true")
        parser.add_argument("--steps", type=positive_int, default=100)
        parser.add_argument("--seed", type=int, default=42)
        if mode != "capture":
            parser.add_argument("--input", type=Path, required=True)


def _add_asset_commands(commands):
    assets = commands.add_parser("assets").add_subparsers(dest="action", required=True)
    assets.add_parser("list")
    download = assets.add_parser("download")
    download.add_argument("source", choices=(
        "ycb", "dexgraspnet", "gendexgrasp", "dexgraspnet2", "oakink", "objaverse-xl"
    ))
    download.add_argument("--files", nargs="+")
    download.add_argument("--manifest", type=Path)
    download.add_argument("--hf-endpoint", help="Explicit Hugging Face mirror; default: HF_ENDPOINT or official host")
    download.add_argument("--url", help="Official direct link override for DexGraspNet/GenDexGrasp")
    download.add_argument("--list-files", action="store_true")
    download.add_argument("--dry-run", action="store_true")
    download.add_argument("--output-dir", type=Path)
    download.add_argument("--max-gb", type=positive_int, default=8)
    prepare = assets.add_parser("prepare-dexgraspnet")
    prepare.add_argument("--objects", nargs="+", choices=("dgn_can", "dgn_banana", "dgn_apple"),
                         default=["dgn_can", "dgn_banana", "dgn_apple"])
    prepare.add_argument("--longest-side", type=float, default=0.1)
    for action in ("download-ycb", "prepare-ycb"):
        parser = assets.add_parser(action)
        parser.add_argument(
            "--objects", nargs="+", choices=("cracker_box", "mustard_bottle", "mug"),
            default=["cracker_box", "mustard_bottle", "mug"],
        )
    assets.add_parser("manufacturers")
    assets.add_parser("hands").add_argument("--manufacturer")
    for action in ("inspect", "fetch", "convert", "validate", "preview"):
        parser = assets.add_parser(action)
        parser.add_argument("--id", required=True)
        if action == "convert":
            parser.add_argument("--format", default="usd")
        elif action == "validate":
            parser.add_argument("--steps", type=positive_int, default=100)
        elif action == "preview":
            parser.add_argument(
                "--seconds", type=positive_int, default=600,
                help="Keep the desktop preview open for this many seconds, at most 3600",
            )


def _add_run_options(parser, default_steps):
    """Add the options shared by custom and official scene runs."""
    parser.add_argument("--steps", type=positive_int, default=default_steps)
    parser.add_argument("--num-envs", type=positive_int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=positive_int, default=300)
    parser.add_argument("--output-dir", type=Path)


def _add_scene_commands(commands):
    scenes = commands.add_parser("scene").add_subparsers(dest="action", required=True)
    scenes.add_parser("list")
    parser = scenes.add_parser("run")
    parser.add_argument("--hand")
    parser.add_argument("--object", dest="object_id")
    parser.add_argument("--scene")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--physics", "--backend", dest="backend")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--screenshot", action="store_true", help="Save a real offscreen screenshot after stepping")
    parser.add_argument(
        "--headless", action="store_true",
        help="Explicit acknowledgement; headless is already the default",
    )
    _add_run_options(parser, default_steps=100)


def _add_arena_commands(commands):
    arena = commands.add_parser("arena").add_subparsers(dest="action", required=True)
    parser = arena.add_parser("run")
    parser.add_argument("environment", choices=("cube_goal_pose", "dexsuite_lift"))
    parser.add_argument(
        "--physics", "--backend", dest="backend", choices=("physx",), default="physx"
    )
    parser.add_argument("--headless", action="store_true")
    _add_run_options(parser, default_steps=20)


def build_parser():
    """Build the public CLI without loading Isaac Sim or USD."""
    parser = argparse.ArgumentParser(
        prog="dexlab", description="DexterousLab: bounded simulation and grasp research"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    _add_experiment_commands(commands)
    _add_asset_commands(commands)
    _add_scene_commands(commands)
    _add_arena_commands(commands)
    return parser


def _asset_inventory():
    result = {
        "robots": {},
        "objects": {},
        "reserved": ["cup", "imported-hand tabletop controllers", "learned grasp generation"],
    }
    for category in ("robots", "objects"):
        for path in sorted((CONFIG_ROOT / category).glob("*.toml")):
            result[category][path.stem] = named_config(category, path.stem)
    result["notice"] = (
        "Configuration inventory, not evidence of asset availability or successful simulation"
    )
    return result


def _asset_result(args):
    if args.action == "download":
        from dexterous_lab.assets.downloads import run_download

        return run_download(args)
    if args.action == "prepare-dexgraspnet":
        from dexterous_lab.assets.dexgraspnet_samples import prepare_samples

        return prepare_samples(args.objects, args.longest_side)
    if args.action == "download-ycb":
        from dexterous_lab.assets.ycb import download_objects

        return download_objects(args.objects)
    if args.action == "prepare-ycb":
        from dexterous_lab.assets.ycb_prepare import prepare_objects

        return prepare_objects(args.objects)
    if args.action == "list":
        return _asset_inventory()

    from dexterous_lab.assets.catalog import AssetCatalog
    from dexterous_lab.assets.manager import AssetManager

    catalog = AssetCatalog()
    if args.action == "manufacturers":
        return catalog.manufacturers()
    if args.action == "hands":
        return [
            record for record in catalog.records("hands")
            if not args.manufacturer or record["manufacturer"] == args.manufacturer
        ]
    if args.action == "inspect":
        return catalog.get(args.id)

    manager = AssetManager(catalog)
    if args.action == "fetch":
        return manager.fetch(args.id)
    if args.action == "convert":
        return manager.convert(args.id, args.format)
    if args.action == "validate":
        return manager.validate(args.id, args.steps)
    if args.action == "preview":
        return manager.preview(args.id, args.seconds)
    raise ValueError(f"Unsupported asset action: {args.action}")


def _experiment_result(args):
    from dexterous_lab.evaluation.runner import EvaluationRunner

    return EvaluationRunner().run(
        args.action,
        input_path=getattr(args, "input", None),
        object_id=args.object_id,
        include_sphere=args.include_sphere,
        steps=args.steps,
        seed=args.seed,
    )


def _scene_inventory():
    return {
        "scenes": [path.stem for path in sorted((CONFIG_ROOT / "scenes").glob("*.toml"))],
        "backends": ["physx"],
        "policy": "zero_action",
        "grasp_validation": False,
    }


def _run_simulation(args):
    if args.num_envs > 4 or args.steps > 1000:
        raise ValueError("First-version smoke runs are limited to 4 environments and 1000 steps")
    request = {
        "kind": args.command,
        "steps": args.steps,
        "num_envs": args.num_envs,
        "seed": args.seed,
        "backend": args.backend or "physx",
        "policy": "zero_action",
    }
    if args.command == "scene":
        if args.screenshot:
            request["screenshot"] = True
        request["config"] = load_scene(
            args.config, args.hand, args.object_id, args.scene, args.backend
        )
        if args.dry_run:
            print_json(request)
            return 0
    else:
        request["environment"] = args.environment
    return run_worker(request, args.output_dir, args.timeout)


def main(argv=None):
    """Dispatch one command and report configuration errors through argparse."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "assets":
            print_json(_asset_result(args))
            return 0
        if args.command == "experiment":
            print_json(_experiment_result(args))
            return 0
        if args.command == "scene" and args.action == "list":
            print_json(_scene_inventory())
            return 0
        return _run_simulation(args)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
