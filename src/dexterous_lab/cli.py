"""Public command line entry point; no simulator imports in the parent process."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

from dexterous_lab.config import CONFIG_ROOT, load_scene, named_config
from dexterous_lab.runtime import arena_root, run_worker, runtime_environment, shared_python
from dexterous_lab.storage import storage_environment


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return result


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


def build_parser():
    parser = argparse.ArgumentParser(prog="dexlab", description="DexterousLab: bounded simulation and grasp research")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    experiments = commands.add_parser('experiment').add_subparsers(dest='action', required=True)
    for mode in ('capture', 'replay', 'batch'):
        experiment = experiments.add_parser(mode)
        experiment.add_argument('--object', dest='object_id', choices=('cube', 'sphere', 'cylinder'), default='cube')
        experiment.add_argument('--include-sphere', action='store_true')
        experiment.add_argument('--steps', type=positive_int, default=100)
        experiment.add_argument('--seed', type=int, default=42)
        if mode != 'capture':
            experiment.add_argument('--input', type=Path, required=True)
    assets = commands.add_parser("assets").add_subparsers(dest="action", required=True)
    assets.add_parser("list")
    assets.add_parser("manufacturers")
    hands = assets.add_parser("hands")
    hands.add_argument("--manufacturer")
    for action in ("inspect", "fetch", "convert", "validate", "preview"):
        entry = assets.add_parser(action)
        entry.add_argument("--id", required=True)
        if action == "convert":
            entry.add_argument("--format", default="usd")
        if action == "validate":
            entry.add_argument("--steps", type=positive_int, default=100)
        if action == "preview":
            entry.add_argument("--seconds", type=positive_int, default=600,
                               help="Keep the desktop preview open for this many seconds, at most 3600")
    scenes = commands.add_parser("scene").add_subparsers(dest="action", required=True)
    scenes.add_parser("list")
    run = scenes.add_parser("run")
    run.add_argument("--hand")
    run.add_argument("--object", dest="object_id")
    run.add_argument("--scene")
    run.add_argument("--config", type=Path)
    run.add_argument("--physics", "--backend", dest="backend")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--headless", action="store_true", help="Explicit acknowledgement; headless is already the default")
    official = commands.add_parser("arena").add_subparsers(dest="action", required=True)
    official_run = official.add_parser("run")
    official_run.add_argument("environment", choices=("cube_goal_pose", "dexsuite_lift"))
    official_run.add_argument("--physics", "--backend", dest="backend", choices=("physx",), default="physx")
    official_run.add_argument("--headless", action="store_true")
    for entry in (run, official_run):
        entry.add_argument("--steps", type=positive_int, default=20)
        entry.add_argument("--num-envs", type=positive_int, default=1)
        entry.add_argument("--seed", type=int, default=42)
        entry.add_argument("--timeout", type=positive_int, default=300)
        entry.add_argument("--output-dir", type=Path)
    run.set_defaults(steps=100)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == 'experiment':
            from dexterous_lab.evaluation.runner import EvaluationRunner

            result = EvaluationRunner().run(args.action, input_path=getattr(args, 'input', None),
                object_id=args.object_id, include_sphere=args.include_sphere, steps=args.steps, seed=args.seed)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "assets":
            if args.action != "list":
                from dexterous_lab.assets.catalog import AssetCatalog
                from dexterous_lab.assets.manager import AssetManager

                catalog = AssetCatalog()
                manager = AssetManager(catalog)
                if args.action == "manufacturers":
                    result = catalog.manufacturers()
                elif args.action == "hands":
                    result = [record for record in catalog.records("hands")
                              if not args.manufacturer or record["manufacturer"] == args.manufacturer]
                elif args.action == "inspect":
                    result = catalog.get(args.id)
                elif args.action == "fetch":
                    result = manager.fetch(args.id)
                elif args.action == "convert":
                    result = manager.convert(args.id, args.format)
                elif args.action == "validate":
                    result = manager.validate(args.id, args.steps)
                else:
                    result = manager.preview(args.id, args.seconds)
                print(json.dumps(result, indent=2))
                return 0
            result = {"robots": {}, "objects": {}, "reserved": ["cup", "imported-hand tabletop controllers", "learned grasp generation"]}
            for category in ("robots", "objects"):
                for path in sorted((CONFIG_ROOT / category).glob("*.toml")):
                    result[category][path.stem] = named_config(category, path.stem)
            result["notice"] = "Configuration inventory, not evidence of asset availability or successful simulation"
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "scene" and args.action == "list":
            print(json.dumps({"scenes": [path.stem for path in sorted((CONFIG_ROOT / "scenes").glob("*.toml"))],
                              "backends": ["physx"], "policy": "zero_action", "grasp_validation": False}, indent=2))
            return 0
        if args.num_envs > 4 or args.steps > 1000:
            raise ValueError("First-version smoke runs are limited to 4 environments and 1000 steps")
        request = {"kind": args.command, "steps": args.steps, "num_envs": args.num_envs, "seed": args.seed,
                   "backend": args.backend or "physx", "policy": "zero_action"}
        if args.command == "scene":
            request["config"] = load_scene(args.config, args.hand, args.object_id, args.scene, args.backend)
            if args.dry_run:
                print(json.dumps(request, indent=2))
                return 0
        else:
            request["environment"] = args.environment
        return run_worker(request, args.output_dir, args.timeout)
    except (ValueError, FileNotFoundError, KeyError, TypeError) as exc:
        parser.error(str(exc))
