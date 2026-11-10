"""Provider plans, binary downloads, integrity checks and failure preservation."""

import hashlib
import io
import json
from unittest.mock import Mock, patch

import pytest

from dexterous_lab.assets.downloads import (
    download_file, list_files, open_download, run_download, safe_filename,
)
from dexterous_lab.cli import build_parser


def binary(data=b"model", content_type="application/octet-stream"):
    response = io.BytesIO(data)
    response.headers = {"Content-Length": str(len(data)), "Content-Type": content_type}
    return response


def item(data=b"model"):
    return {"name": "meshes/object.zip", "url": "https://example.org/object.zip",
            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "license": "CC-BY-4.0"}


def test_binary_download_verified_and_reused(tmp_path):
    opener = Mock()
    opener.open.return_value = binary()
    with patch("dexterous_lab.assets.downloads.build_opener", return_value=opener):
        result = download_file(item(), tmp_path, 100)
        assert download_file(item(), tmp_path, 100)["status"] == "already_present"
    assert result["status"] == "downloaded"
    assert opener.open.call_count == 1
    report = json.loads((tmp_path / "meshes/object.zip.download/provenance.json").read_text())
    assert report["hash_verified_against_upstream"] is True
    assert report["grasp_success"] is None
    assert report["simulation_status"] == "not_run"


def test_changed_existing_file_is_never_overwritten(tmp_path):
    opener = Mock()
    opener.open.return_value = binary()
    with patch("dexterous_lab.assets.downloads.build_opener", return_value=opener):
        result = download_file(item(), tmp_path, 100)
    from pathlib import Path
    Path(result["path"]).write_bytes(b"user data")
    with pytest.raises(ValueError, match="changed"):
        download_file(item(), tmp_path, 100)
    assert Path(result["path"]).read_bytes() == b"user data"


@pytest.mark.parametrize("reason", ["hash", "length", "limit", "empty"])
def test_incomplete_or_invalid_download_does_not_publish(tmp_path, reason):
    response = binary(b"wrong" if reason == "hash" else b"model")
    if reason == "length": response.headers["Content-Length"] = "20"
    if reason == "empty": response = binary(b"")
    opener = Mock()
    opener.open.return_value = response
    with patch("dexterous_lab.assets.downloads.build_opener", return_value=opener):
        with pytest.raises(ValueError):
            download_file(item(), tmp_path, 1 if reason == "limit" else 100)
    assert not list(tmp_path.rglob("*.download"))
    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("name", ["", ".", "../file", "/root/file", "folder/../../file", "folder\\file"])
def test_filename_cannot_escape_download_directory(name):
    with pytest.raises(ValueError): safe_filename(name)


def test_google_drive_confirmation_is_followed_once():
    form = b'<form id="download-form" action="https://drive.usercontent.google.com/download"><input name="id" value="123"><input name="confirm" value="t"></form>'
    opener = Mock()
    opener.open.side_effect = [binary(form, "text/html"), binary()]
    response = open_download(opener, "https://drive.google.com/uc?id=123")
    assert response.read() == b"model"
    assert "confirm=t" in opener.open.call_args.args[0].full_url
    response.close()


def test_html_login_page_is_not_saved_as_a_model():
    opener = Mock()
    opener.open.return_value = binary(b"<html>login required</html>", "text/html")
    with pytest.raises(ValueError, match="HTML"):
        open_download(opener, "https://example.org/model.zip")


@pytest.mark.parametrize("source", ["dexgraspnet2", "oakink"])
def test_huggingface_files_use_pinned_revision_and_lfs_hash(source):
    values = [{"sha": "abc123"}, {"siblings": [
        {"rfilename": "README.md"},
        {"rfilename": "shape/objects.zip", "lfs": {"size": 99, "sha256": "a" * 64}},
    ]}]
    with patch("dexterous_lab.assets.downloads.get_metadata", side_effect=[json.dumps(x).encode() for x in values]):
        result = list_files(source)
    assert len(result) == 1
    assert "/resolve/abc123/shape/objects.zip" in result[0]["url"]
    assert result[0]["bytes"] == 99
    assert result[0]["sha256"] == "a" * 64


def test_gendexgrasp_uses_author_file_ids():
    files = {row["name"]: row for row in list_files("gendexgrasp")}
    assert set(files) == {"data.zip", "MultiDex.zip", "env.zip"}
    assert "1WRV7m9AAfDOFE6Z9InIRJwhhlRUSQzCX" in files["data.zip"]["url"]


def test_dexgraspnet_lists_only_official_directory_archives():
    entries = [{"name": "meshdata.tar.gz", "type": "file", "size": 345939166},
               {"name": "folder", "type": "directory"}]
    with patch("dexterous_lab.assets.downloads.get_metadata", return_value=json.dumps(entries).encode()) as metadata:
        result = list_files("dexgraspnet")
    assert [row["name"] for row in result] == ["meshdata.tar.gz"]
    assert "/files/dl-release/" in metadata.call_args.args[0]


def test_objaverse_requires_explicit_license_and_hash(tmp_path):
    manifest = tmp_path / "objects.json"
    manifest.write_text(json.dumps([{"name": "hand.glb", "url": "https://example.org/object"}]))
    with pytest.raises(ValueError, match="sha256"):
        list_files("objaverse-xl", manifest)
    value = dict(item(), source_page="https://example.org/author")
    manifest.write_text(json.dumps([value]))
    assert list_files("objaverse-xl", manifest)[0]["database_license"] == "ODC-By-1.0"


@pytest.mark.parametrize("source", ["ycb", "dexgraspnet", "gendexgrasp", "dexgraspnet2", "oakink", "objaverse-xl"])
def test_all_providers_have_public_cli_and_script_options(source):
    args = build_parser().parse_args(["assets", "download", source, "--list-files"])
    assert args.source == source
    assert args.list_files is True


def test_dry_run_has_no_binary_requests():
    args = build_parser().parse_args(["assets", "download", "gendexgrasp", "--files", "data.zip", "--dry-run"])
    with patch("dexterous_lab.assets.downloads.download_file") as download:
        result = run_download(args)
    download.assert_not_called()
    assert result["downloaded"] is False
    assert result["files"][0]["name"] == "data.zip"


def test_huggingface_mirror_is_explicit_and_canonical_url_is_preserved():
    values = [{"sha": "abc123"}, {"siblings": [{"rfilename": "objects.zip", "size": 12}]}]
    with patch("dexterous_lab.assets.downloads.get_metadata", side_effect=[json.dumps(x).encode() for x in values]) as metadata:
        result = list_files("oakink", hf_endpoint="https://hf-mirror.com")
    assert metadata.call_args.args[0].startswith("https://hf-mirror.com/")
    assert result[0]["canonical_url"].startswith("https://huggingface.co/")


def test_unmanaged_files_are_preserved(tmp_path):
    destination = tmp_path / "meshes/object.zip"
    destination.parent.mkdir()
    destination.write_text("user archive")
    with pytest.raises(FileExistsError):
        download_file(item(), tmp_path, 100)
    assert destination.read_text() == "user archive"


def test_objaverse_without_a_manifest_is_an_explicit_error():
    with pytest.raises(ValueError, match="per-object licenses"):
        list_files("objaverse-xl")


def test_selected_objaverse_objects_use_the_same_verified_transfer(tmp_path):
    row = dict(item(), source_page="https://example.org/author")
    manifest = tmp_path / "objects.json"
    manifest.write_text(json.dumps([row]))
    args = build_parser().parse_args([
        "assets", "download", "objaverse-xl", "--manifest", str(manifest),
        "--output-dir", str(tmp_path / "models"), "--max-gb", "1",
    ])
    opener = Mock()
    opener.open.return_value = binary()
    with patch("dexterous_lab.assets.downloads.build_opener", return_value=opener):
        result = run_download(args)
    assert result[0]["status"] == "downloaded"
    assert "objects.json" not in result[0]["path"]


def test_downloaded_asset_cannot_be_a_symlink(tmp_path):
    destination = tmp_path / "meshes/object.zip.download"
    destination.parent.mkdir()
    destination.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symbolic link"):
        download_file(item(), tmp_path, 100)


def test_mislabeled_html_is_rejected(tmp_path):
    opener = Mock()
    opener.open.return_value = binary(b"<!doctype html><html>Denied</html>")
    with patch("dexterous_lab.assets.downloads.build_opener", return_value=opener):
        with pytest.raises(ValueError, match="HTML content"):
            download_file(dict(item(), sha256=None, bytes=None), tmp_path, 100)
    assert not list(tmp_path.rglob("*.download"))


def test_bad_sha256_is_rejected_before_network(tmp_path):
    with pytest.raises(ValueError, match="SHA-256"):
        download_file(dict(item(), sha256="placeholder"), tmp_path, 100)
