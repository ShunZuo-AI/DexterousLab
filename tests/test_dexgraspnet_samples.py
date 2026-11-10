"""Selected archive extraction and explicit metric scaling preserve source assets."""

import io
from pathlib import Path
import tarfile

import numpy as np
import pytest
import trimesh

from dexterous_lab.assets.dexgraspnet_samples import extract_samples, load_scaled_pieces


def make_archive(path, entries):
    with tarfile.open(path, "w:gz") as package:
        for name, data in entries:
            entry = tarfile.TarInfo(name)
            entry.size = len(data)
            package.addfile(entry, io.BytesIO(data))


def test_extracts_only_selected_object(tmp_path):
    archive = tmp_path / "source.tgz"
    make_archive(archive, [("meshdata/apple/coacd/decomposed.obj", b"selected"),
                           ("meshdata/banana/coacd/decomposed.obj", b"other")])
    destination = tmp_path / "subset"
    extract_samples(archive, destination, ["apple"])
    assert (destination / "meshdata/apple/coacd/decomposed.obj").read_bytes() == b"selected"
    assert not (destination / "meshdata/banana").exists()
    with pytest.raises(FileExistsError):
        extract_samples(archive, destination, ["apple"])


def test_unsafe_selected_path_is_rejected(tmp_path):
    archive = tmp_path / "source.tgz"
    make_archive(archive, [("meshdata/apple/../../../escaped.obj", b"no")])
    with pytest.raises(ValueError, match="Unsafe"):
        extract_samples(archive, tmp_path / "subset", ["apple"])
    assert not (tmp_path / "escaped.obj").exists()


def test_missing_object_is_explicit(tmp_path):
    archive = tmp_path / "source.tgz"
    make_archive(archive, [("meshdata/other/coacd/decomposed.obj", b"other")])
    with pytest.raises(ValueError, match="missing"):
        extract_samples(archive, tmp_path / "subset", ["apple"])


def test_scaled_pieces_keep_relative_geometry_and_do_not_modify_raw(tmp_path):
    a = trimesh.creation.box(extents=[2, 1, 1])
    a.apply_translation([3, 0, 0])
    b = trimesh.creation.box(extents=[1, 1, 1])
    b.apply_translation([5, 0, 0])
    a.export(tmp_path / "coacd_convex_piece_0.obj")
    b.export(tmp_path / "coacd_convex_piece_1.obj")
    original = (tmp_path / "coacd_convex_piece_0.obj").read_bytes()
    pieces, report = load_scaled_pieces(tmp_path, 0.1)
    combined = trimesh.util.concatenate(pieces)
    assert max(combined.extents) == pytest.approx(0.1)
    assert combined.bounds.mean(axis=0) == pytest.approx([0, 0, 0])
    assert len(pieces) == 2
    assert report["meters_per_source_unit"] == pytest.approx(0.1 / 3.5)
    assert (tmp_path / "coacd_convex_piece_0.obj").read_bytes() == original


@pytest.mark.parametrize("size", [0, -1, 1, float("nan")])
def test_invalid_experimental_size_is_rejected(tmp_path, size):
    with pytest.raises(ValueError, match="between"):
        load_scaled_pieces(tmp_path, size)


def test_materially_nonconvex_piece_is_not_silently_hulled(tmp_path):
    # Two separated closed solids stored as one piece are not a valid convex piece.
    a = trimesh.creation.box()
    b = trimesh.creation.box()
    b.apply_translation([3, 0, 0])
    trimesh.util.concatenate([a, b]).export(tmp_path / "coacd_convex_piece_0.obj")
    with pytest.raises(ValueError, match="materially non-convex"):
        load_scaled_pieces(tmp_path, 0.1)
