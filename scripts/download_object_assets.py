"""Download selected object datasets using the same options as dexlab assets download.

Run with the existing Arena Python. Examples:
    python scripts/download_object_assets.py dexgraspnet2 --list-files
    python scripts/download_object_assets.py oakink --files shape/metaV2.zip
"""

from pathlib import Path
import sys

# Make this checkout usable without an editable package installation.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dexterous_lab.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["assets", "download", *sys.argv[1:]]))
