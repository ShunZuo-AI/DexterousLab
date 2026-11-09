import json

import numpy as np
import pytest

from dexterous_lab.data_collection.collector import DatasetCollector
from dexterous_lab.evaluation.runner import read_candidates, summarize_trials
from dexterous_lab.policies.registry import PolicyRegistry
from dexterous_lab.scenes.builder import SceneBuilder


def snapshot():
    return {'step': 0, 'joint_names': ['joint'], 'joint_positions': [[0.1]], 'joint_velocities': [[0]],
            'hand_root_frame': 'palm', 'hand_root_pose': [[0, 0, 1, 0, 0, 0, 1]],
            'robot_base_pose': [[0, 0, 1, 0, 0, 0, 1]], 'object_pose': [[0, 0, 0.1, 0, 0, 0, 1]],
            'contact_points': [[]], 'contact_normal_forces_W': [[[[0, 0, 0]]]]}


def test_collector_writes_numeric_npz_and_roundtrip_candidate(tmp_path):
    collector = DatasetCollector(tmp_path / 'trial', {'seed': 42})
    collector.record(snapshot(), [0])
    candidate = collector.save_candidate(snapshot(), object_id='cube', hand_id='shadow', seed=42,
                                          asset_version='test', tendon_positions={})
    collector.finish({'success': None})
    with np.load(tmp_path / 'trial/trajectory.npz', allow_pickle=False) as data:
        assert data['joint_positions'].shape == (1, 1)
        assert data['contact_points'].shape == (0, 3)
        assert data['contact_offsets'].tolist() == [0, 0]
        assert all(data[name].dtype.kind != 'O' for name in data.files)
    loaded = read_candidates(tmp_path / 'trial/candidate.json')[0]
    assert loaded.to_dict() == candidate.to_dict()
    with pytest.raises(FileExistsError):
        DatasetCollector(tmp_path / 'trial', {})


def test_failures_and_unknowns_are_separate():
    report = summarize_trials([{'loaded': True, 'simulation_completed': True, 'success': False, 'failure_reason': 'no_lift'},
                              {'loaded': False, 'success': None, 'failure_reason': 'invalid_joints'},
                              {'loaded': True, 'simulation_completed': True, 'success': True}])
    assert report['attempted'] == 3
    assert report['simulation_completed'] == 2
    assert report['evaluated'] == 2
    assert report['success_rate_evaluated'] == 0.5
    assert report['failure_reasons'] == {'no_lift': 1, 'invalid_joints': 1}


def test_policy_registry_is_explicit_and_no_algorithm_fallback():
    registry = PolicyRegistry()
    policy = registry.load('hold', target_action=[0.1, 0.2])
    action = policy.predict({})
    action[0] = 9
    np.testing.assert_allclose(policy.predict({}), [0.1, 0.2])
    with pytest.raises(ValueError, match='not implemented'):
        registry.load('HALO')
    with pytest.raises(ValueError):
        registry.register('hold', lambda: None)


def test_scene_builder_adds_distinct_sphere_without_changing_primary():
    specification = SceneBuilder().specification(include_sphere=True)
    assert specification['object']['kind'] == 'cube'
    assert specification['robot']['hand_id'] == 'shadow'
    assert specification['additional_objects'][0]['config']['kind'] == 'sphere'
    assert specification['additional_objects'][0]['name'] == 'secondary_sphere'
    assert 'additional_objects' not in SceneBuilder().specification()


def test_invalid_dataset_cannot_silently_proceed(tmp_path):
    path = tmp_path / 'candidates.json'
    path.write_text('[]')
    with pytest.raises(ValueError, match='between 1 and 10'):
        read_candidates(path)
    path.write_text('[{"success": true}]')
    with pytest.raises(TypeError):
        read_candidates(path)


def test_lift_contact_speed_and_continuous_hold_are_all_required():
    from dexterous_lab.evaluation.criteria import next_hold_count

    criteria = {'lift_height_m': 0.03, 'contact_force_threshold_n': 0.01, 'max_linear_speed_m_s': 0.1}
    assert next_hold_count(19, 0.04, 0.02, 0.01, criteria) == 20
    assert next_hold_count(19, 0.0, 0.02, 0.01, criteria) == 0
    assert next_hold_count(19, 0.04, 0.0, 0.01, criteria) == 0
    assert next_hold_count(19, 0.04, 0.02, 1.0, criteria) == 0
    with pytest.raises(ValueError, match='Nonfinite'):
        next_hold_count(19, float('nan'), 0.02, 0.01, criteria)


def test_asset_registry_uses_catalog_integrity_not_file_presence(tmp_path):
    from dexterous_lab.assets.registry import AssetRegistry
    from dexterous_lab.assets.catalog import save_json, sha256_file

    raw = tmp_path / 'assets/hands/vendor/hand/right/raw'
    raw.mkdir(parents=True)
    source = raw / 'model.usd'
    source.write_text('source')
    save_json(raw.parent / 'checksums.json', [{'path': 'model.usd', 'sha256': sha256_file(source)}])
    save_json(tmp_path / 'manifests/hands.json', {'hands': [{'asset_id': 'vendor/hand/right', 'category': 'hands',
        'local_raw_path': str(source), 'checksum_manifest': str(raw.parent / 'checksums.json')}]})
    save_json(tmp_path / 'manifests/objects.json', {'objects': []})
    registry = AssetRegistry(tmp_path / 'manifests', tmp_path / 'assets')
    assert registry.model_path('vendor/hand/right') == str(source)
    assert registry.verify_integrity('vendor/hand/right')['passed']
    source.write_text('changed')
    assert not registry.verify_integrity('vendor/hand/right')['passed']
