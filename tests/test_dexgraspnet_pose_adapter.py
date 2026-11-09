import numpy as np
import pytest

from dexterous_lab.grasp_execution.dexgraspnet_adapter import source_qpos_to_candidate


@pytest.fixture
def arguments():
    T_W_O = np.eye(4)
    T_W_O[:3, 3] = [1, 2, 3]
    alignment = np.eye(4)
    alignment[0, 3] = 0.05
    return dict(
        qpos=dict(WRJTx=0.1, WRJTy=0.2, WRJTz=0.3, WRJRx=0.0, WRJRy=0.0, WRJRz=np.pi / 2, source_joint=0.2),
        joint_map={"source_joint": "target_joint"}, fixed_joint_positions={"wrist": 0.0},
        target_joint_limits={"target_joint": (-1, 1), "wrist": (-1, 1)},
        T_W_O=T_W_O, T_Hsource_Htarget=alignment, object_id="cube", hand_id="test-only",
        palm_frame="actual_palm", seed=42, asset_version="test-v1",
    )


def test_source_object_and_calibrated_palm_frames(arguments):
    candidate = source_qpos_to_candidate(**arguments)
    assert candidate.hand_root_pose[:3] == pytest.approx((1.1, 2.25, 3.3))
    assert candidate.object_pose[:3] == (1, 2, 3)
    assert candidate.hand_root_pose[3:] == pytest.approx((0, 0, np.sqrt(0.5), np.sqrt(0.5)))
    assert candidate.joint_positions == {"target_joint": 0.2, "wrist": 0.0}
    assert candidate.success is None and candidate.contact_points is None


@pytest.mark.parametrize("updates", [{"joint_map": {}}, {"fixed_joint_positions": {"target_joint": 0}},
                                       {"target_joint_limits": {}}, {"T_Hsource_Htarget": None},
                                       {"T_W_O": np.zeros((4, 4))}])
def test_missing_calibration_or_joint_mapping_never_silently_falls_back(arguments, updates):
    arguments.update(updates)
    with pytest.raises(ValueError):
        source_qpos_to_candidate(**arguments)
