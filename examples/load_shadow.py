"""Example A: load the existing official Shadow and run 100 real scene steps."""

import json

from dexterous_lab.assets.manager import AssetManager


if __name__ == '__main__':
    print(json.dumps(AssetManager().validate('shadow_robot/dexterous_hand/right_isaaclab', steps=100), indent=2))
