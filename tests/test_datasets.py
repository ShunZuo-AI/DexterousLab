from dataclasses import replace
import json

import pytest

from dexterous_lab.datasets.writer import GraspDatasetWriter
from dexterous_lab.evaluation.grasp import GraspEvaluator
from dexterous_lab.grasp_execution.base import GraspValidator
from dexterous_lab.grasp_generation.base import GraspGenerator
from dexterous_lab.grasp_synthesis.candidate import GraspCandidate


@pytest.fixture
def candidate():
    return GraspCandidate(object_id="cube", hand_id="allegro", hand_root_pose=(0, 0, 0, 0, 0, 0, 1),
                          joint_positions={"index_joint_0": 0.1}, object_pose=(0, 0, 0, 0, 0, 0, 1),
                          seed=42, algorithm="test-only", asset_version="v1")


def test_dataset_roundtrip_without_overwrite(candidate, tmp_path):
    path = tmp_path / "data.jsonl"
    with GraspDatasetWriter(path) as writer:
        writer.write(candidate)
    loaded = GraspCandidate(**json.loads(path.read_text()))
    assert loaded == candidate
    with pytest.raises(FileExistsError):
        GraspDatasetWriter(path)


def test_unknown_outcomes_excluded_from_denominator(candidate):
    report = GraspEvaluator().evaluate([candidate, replace(candidate, success=False),
                                       replace(candidate, success=True, stability=0.95, collision=False)])
    assert report == dict(total=3, evaluated=2, unevaluated=1, successful=1, success_rate=0.5)
    assert GraspEvaluator().evaluate([candidate])["success_rate"] is None
    assert GraspEvaluator().evaluate([])["success_rate"] is None


@pytest.mark.parametrize("updates", [{"quaternion_order": "wxyz"}, {"frame": "O"}, {"length_unit": "cm"},
                                       {"success": True}, {"stability": float("nan")}, {"success": "true"},
                                       {"hand_root_pose": (0, 0, 0, 0, 0, 0, 0)},
                                       {"joint_positions": {"joint": float("inf")}}])
def test_invalid_record_rejected(candidate, updates):
    with pytest.raises(ValueError):
        replace(candidate, **updates)


def test_interfaces_cannot_fake_implementation():
    with pytest.raises(TypeError):
        GraspGenerator()
    with pytest.raises(TypeError):
        GraspValidator()
