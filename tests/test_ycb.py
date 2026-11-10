"""YCB downloads preserve user files and reject unsafe or changed package contents."""

import io
import json
from pathlib import Path
import tarfile
from unittest.mock import patch

import pytest

from dexterous_lab.assets.catalog import AssetCatalog
from dexterous_lab.assets.ycb import (
    download_archive, download_object, extract_mesh_package, verify_download,
)
from dexterous_lab.config import ObjectConfig


def package_bytes(name="025_mug/google_16k/textured.obj", *, link=False):
    content = io.BytesIO()
    with tarfile.open(fileobj=content, mode="w:gz") as package:
        member = tarfile.TarInfo(name)
        if link:
            member.type = tarfile.SYMTYPE
            member.linkname = "/outside"
            package.addfile(member)
        else:
            data = b"v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n"
            member.size = len(data)
            package.addfile(member, io.BytesIO(data))
    return content.getvalue()


@pytest.fixture
def catalog(tmp_path):
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    for category in ("hands", "objects"):
        (manifests / f"{category}.json").write_text(json.dumps({category: []}))
    return AssetCatalog(manifests, tmp_path / "assets")


def test_download_registers_source_and_skips_unchanged_files(catalog):
    data = package_bytes()
    def fetch(url, path):
        path.write_bytes(data)
        return len(data)

    with patch("dexterous_lab.assets.ycb.download_archive", side_effect=fetch) as request:
        result = download_object("mug", catalog)
        assert result["status"] == "fetched"
        assert download_object("mug", catalog)["status"] == "already_present"
    request.assert_called_once()
    record = catalog.get("ycb/025_mug")
    assert record["simulation_status"] == "not_run"
    assert record["license"]["spdx"] == "CC-BY-4.0"
    assert verify_download(result["directory"])["archive_bytes"] == len(data)
    Path(record["local_raw_path"]).write_text("modified")
    with pytest.raises(ValueError, match="changed"):
        download_object("mug", catalog)


def test_download_preserves_existing_unmanaged_directory(catalog):
    directory = catalog.asset_root / "objects/ycb/025_mug"
    directory.mkdir(parents=True)
    user_file = directory / "experiment.txt"
    user_file.write_text("keep me")
    with pytest.raises(FileNotFoundError):
        download_object("mug", catalog)
    assert user_file.read_text() == "keep me"


@pytest.mark.parametrize("name,link", [("../escaped.obj", False), ("/escaped.obj", False), ("mesh.obj", True)])
def test_extract_rejects_paths_and_links(tmp_path, name, link):
    archive = tmp_path / "package.tgz"
    archive.write_bytes(package_bytes(name, link=link))
    with pytest.raises(ValueError, match="Unsafe"):
        extract_mesh_package(archive, tmp_path / "raw")
    assert not (tmp_path / "escaped.obj").exists()


def test_incomplete_download_is_not_registered(catalog):
    with patch("dexterous_lab.assets.ycb.download_archive", side_effect=ValueError("Incomplete")):
        with pytest.raises(ValueError, match="Incomplete"):
            download_object("mug", catalog)
    assert catalog.records("objects") == []
    assert not (catalog.asset_root / "objects/ycb/025_mug").exists()
    assert not list((catalog.asset_root / "objects/ycb").glob("*.tmp"))


def test_relative_usd_paths_use_project_root_not_working_directory(tmp_path, monkeypatch):
    import dexterous_lab.config as config

    (tmp_path / "object.usd").write_text("test path only")
    monkeypatch.setattr(config, "PROJECT_ROOT", tmp_path)
    configuration = ObjectConfig(kind="usd", usd_path="object.usd")
    assert configuration.usd_path == str(tmp_path / "object.usd")


def test_range_download_checks_response_offsets(tmp_path):
    response = io.BytesIO(b"123")
    response.headers = {"Content-Length": "3", "Content-Range": "bytes 1-3/3"}
    response.status = 206
    head = io.BytesIO()
    head.headers = {"Content-Length": "3"}
    with patch("dexterous_lab.assets.ycb.urlopen", side_effect=[head, response]):
        with pytest.raises(ValueError, match="byte range"):
            download_archive("https://example.test/object", tmp_path / "bad.tgz")


def test_range_download_reassembles_exact_bytes(tmp_path):
    response = io.BytesIO(b"123")
    response.headers = {"Content-Range": "bytes 0-2/3"}
    response.status = 206
    head = io.BytesIO()
    head.headers = {"Content-Length": "3"}
    destination = tmp_path / "object.tgz"
    with patch("dexterous_lab.assets.ycb.urlopen", side_effect=[head, response]):
        assert download_archive("https://example.test/object", destination) == 3
    assert destination.read_bytes() == b"123"


def test_range_download_reassembles_multiple_chunks_in_order(tmp_path):
    data = bytes(range(256)) * 1200

    def open_request(request, timeout):
        if request.get_method() == "HEAD":
            response = io.BytesIO()
            response.headers = {"Content-Length": str(len(data))}
        else:
            start, end = map(int, request.get_header("Range").removeprefix("bytes=").split("-"))
            response = io.BytesIO(data[start:end + 1])
            response.headers = {"Content-Range": f"bytes {start}-{end}/{len(data)}"}
            response.status = 206
        return response

    destination = tmp_path / "multi.tgz"
    with patch("dexterous_lab.assets.ycb.urlopen", side_effect=open_request):
        assert download_archive("https://example.test/object", destination) == len(data)
    assert destination.read_bytes() == data


def test_catalog_record_without_local_model_can_be_downloaded_again(catalog):
    import shutil

    data = package_bytes()

    def fetch(url, path):
        path.write_bytes(data)
        return len(data)

    with patch("dexterous_lab.assets.ycb.download_archive", side_effect=fetch):
        result = download_object("mug", catalog)
        shutil.rmtree(result["directory"])
        assert download_object("mug", catalog)["status"] == "fetched"
    assert len(catalog.records("objects")) == 1
    assert Path(catalog.get("ycb/025_mug")["local_raw_path"]).is_file()


def test_invalid_normals_are_repaired_only_in_a_copy(tmp_path):
    from dexterous_lab.assets.ycb import prepare_converter_input

    raw = tmp_path / "raw"
    raw.mkdir()
    source = raw / "textured.obj"
    original = "mtllib textured.mtl\nv 0 0 0\nvt 0.25 0.75\nvn nan nan nan\nf 1/1/1 1/1/1 1//1\n"
    source.write_text(original)
    (raw / "textured.mtl").write_text("map_Kd texture.png")
    output, repair = prepare_converter_input(source, tmp_path / "derived")
    assert source.read_text() == original
    assert "vn " not in output.read_text()
    assert "f 1/1 1/1 1" in output.read_text()
    assert "vt 0.25 0.75" in output.read_text()
    assert (output.parent / "textured.mtl").is_file()
    assert repair["invalid_normals"] == 1


def test_invalid_positions_cannot_be_silently_repaired(tmp_path):
    from dexterous_lab.assets.ycb import prepare_converter_input

    source = tmp_path / "textured.obj"
    source.write_text("v nan 0 0\n")
    with pytest.raises(ValueError, match="positions"):
        prepare_converter_input(source, tmp_path / "derived")
