"""A configuration facade over the existing Arena tabletop factory.

Independent implementation informed by DexGarmentLab Env_StandAlone/BaseEnv.py
and Hang_Coat_Env.py; no garment simulation or source implementation copied.
"""

from dexterous_lab.config import load_scene, named_config


class SceneBuilder:
    def specification(self, hand='shadow', object_id='cube', include_sphere=False):
        result = load_scene(hand=hand, object_id=object_id, backend='physx')
        if include_sphere:
            if object_id == 'sphere':
                raise ValueError('The extra sphere is intended for the cube tabletop experiment')
            sphere = named_config('objects', 'sphere')
            sphere['position_xyz'] = [-0.35, 0.0, 0.285]
            result['additional_objects'] = [{'name': 'secondary_sphere', 'config': sphere}]
        return result

    def build(self, specification):
        """Build the existing Arena description after SimulationApp startup."""
        from dexterous_lab.scenes.tabletop import DexterousLabTabletopEnvironment, TabletopEnvironmentCfg

        return DexterousLabTabletopEnvironment().build(TabletopEnvironmentCfg(specification=specification))
