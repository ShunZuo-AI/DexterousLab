from pathlib import Path

from dexterous_lab.runtime import runtime_environment
from dexterous_lab.storage import DATA_ROOT, storage_environment
from dexterous_lab.config import PROJECT_ROOT
from dexterous_lab.assets.catalog import ASSET_ROOT


def test_project_storage_is_on_data_volume():
    assert DATA_ROOT == PROJECT_ROOT
    assert ASSET_ROOT == PROJECT_ROOT / 'assets'
    for path in storage_environment().values():
        assert Path(path).is_relative_to(DATA_ROOT)


def test_simulator_inherits_data_volume_paths():
    environment = runtime_environment({"TMPDIR": "/tmp", "XDG_CACHE_HOME": "/root/.cache"})
    assert environment["TMPDIR"] == str(DATA_ROOT / "assets/cache")
    assert environment["XDG_CACHE_HOME"] == str(DATA_ROOT / ".cache")
    assert Path(environment["TMPDIR"]).is_dir()
