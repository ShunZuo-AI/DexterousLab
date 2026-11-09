import pytest

from dexterous_lab.config import ObjectConfig
from dexterous_lab.evaluation.smoke import check_physics_values
from dexterous_lab.objects.mesh import get_object_mesh


def test_measured_physics_match():
    check_physics_values([0.100000001], [[0.7, 0.7, 0.0]], 0.1, 0.7)


@pytest.mark.parametrize("masses,materials", [([], [[0.7, 0.7, 0]]), ([0.2], [[0.7, 0.7, 0]]),
                                           ([0.1], []), ([0.1], [[0.5, 0.7, 0]]),
                                           ([float("nan")], [[0.7, 0.7, 0]]), ([0.1], [[0.7, float("nan"), 0]])])
def test_wrong_backend_physics_fails(masses, materials):
    with pytest.raises(RuntimeError):
        check_physics_values(masses, materials, 0.1, 0.7)


@pytest.mark.parametrize("kind", ["cube", "cylinder", "sphere"])
def test_algorithm_mesh_has_metric_scaled_geometry(kind):
    mesh = get_object_mesh(ObjectConfig(kind=kind, scale=(2, 2, 2)))
    assert mesh.is_watertight
    assert mesh.extents.tolist() == pytest.approx([0.1, 0.1, 0.1])
    assert mesh.volume > 0
