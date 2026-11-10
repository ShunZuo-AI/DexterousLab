"""Download selected research files, preserving provenance and existing user data.

Large archives are saved without extraction or registration as simulation-ready assets.
"""

from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import os
import re
from pathlib import Path, PurePosixPath
import shutil
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
import uuid

from dexterous_lab.assets.catalog import sha256_file
from dexterous_lab.config import CONFIG_ROOT, PROJECT_ROOT


SOURCES = json.loads((CONFIG_ROOT / "downloads/sources.json").read_text())
ARCHIVES = (".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")


def get_metadata(url):
    """Read bounded public metadata, with no simulator or dataset SDK dependency."""
    with build_opener().open(Request(url), timeout=30) as response:
        data = response.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError("Metadata exceeds 32 MiB; select a smaller upstream index")
    return data


def safe_filename(name):
    path = PurePosixPath(name)
    if not name or name in (".", "..") or path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError(f"Unsafe download filename: {name!r}")
    return path


class DownloadLinks(HTMLParser):
    """Read archive links and Google's public download confirmation form."""

    def __init__(self):
        super().__init__()
        self.links = []
        self.action = None
        self.fields = {}
        self.in_download_form = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "form":
            self.in_download_form = attrs.get("id") == "download-form"
            if self.in_download_form:
                self.action = attrs.get("action")
        if tag == "input" and self.in_download_form and attrs.get("name"):
            self.fields[attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.in_download_form = False


def list_files(source, manifest=None, hf_endpoint=None):
    """List provider files without transferring model archives."""
    if source == "ycb":
        from dexterous_lab.assets.ycb import OBJECTS

        return [{"name": name, "ycb_object": value} for name, value in OBJECTS.items()]
    config = SOURCES[source]
    if config.get("hf_repository"):
        repository = config["hf_repository"]
        endpoint = (hf_endpoint or os.environ.get("HF_ENDPOINT", "https://huggingface.co")).rstrip("/")
        if urlparse(endpoint).scheme != "https":
            raise ValueError("HF endpoint must use HTTPS")
        info = json.loads(get_metadata(f"{endpoint}/api/datasets/{repository}"))
        revision = info["sha"]
        # The expanded file listing supplies LFS SHA-256 values without fetching blobs.
        info = json.loads(get_metadata(
            f"{endpoint}/api/datasets/{repository}/revision/{revision}?blobs=true"
        ))
        result = []
        for item in info["siblings"]:
            name = item["rfilename"]
            if not name.endswith(ARCHIVES):
                continue
            safe_filename(name)
            result.append({
                "name": name,
                "url": f"{endpoint}/datasets/{repository}/resolve/{revision}/{quote(name)}",
                "canonical_url": f"https://huggingface.co/datasets/{repository}/resolve/{revision}/{quote(name)}",
                "bytes": item.get("size") or item.get("lfs", {}).get("size"),
                "sha256": item.get("lfs", {}).get("sha256"),
                "revision": revision, "license": config["license"], "source_page": config["page"],
            })
        return result
    if source == "gendexgrasp":
        return [
            {"name": name, "url": "https://drive.google.com/uc?" + urlencode({"export": "download", "id": file_id}),
             "license": config["license"], "source_page": config["page"]}
            for name, file_id in config["google_drive"].items()
        ]
    if source == "dexgraspnet":
        # The official mirror's frontend fetches this JSON endpoint via /files.
        directory = config["directory"]
        parsed = urlparse(directory)
        index_url = f"{parsed.scheme}://{parsed.netloc}/files{parsed.path}"
        entries = json.loads(get_metadata(index_url))
        result = []
        for entry in entries:
            name = entry["name"]
            if entry["type"] != "file" or not name.endswith(ARCHIVES):
                continue
            safe_filename(name)
            result.append({
                "name": name, "url": urljoin(directory, quote(name)),
                "bytes": entry["size"], "license": config["license"],
                "source_page": config["page"],
            })
        if not result:
            raise ValueError("DexGraspNet mirror returned no archives; use --url with an official archive link")
        return result
    if source == "objaverse-xl":
        if not manifest:
            raise ValueError("Objaverse-XL requires --manifest: select objects from official metadata with per-object licenses")
        rows = json.loads(Path(manifest).read_text())
        if not isinstance(rows, list) or not rows or len(rows) > 1000:
            raise ValueError("Objaverse manifest must contain 1 to 1000 selected objects")
        names = set()
        for row in rows:
            for key in ("name", "url", "sha256", "license", "source_page"):
                if not row.get(key):
                    raise ValueError(f"Objaverse object is missing {key}")
            safe_filename(row["name"])
            if row["name"] in names:
                raise ValueError("Duplicate Objaverse filenames")
            names.add(row["name"])
            row["database_license"] = "ODC-By-1.0"
        return rows
    raise ValueError(f"Unsupported source: {source}")


def open_download(opener, url):
    """Open a binary download, handling Google's public confirmation form once."""
    if urlparse(url).scheme != "https":
        raise ValueError("Download URL must use HTTPS")
    response = opener.open(Request(url), timeout=60)
    if "text/html" not in response.headers.get("Content-Type", "").lower():
        return response
    with response:
        page = response.read(2 * 1024 * 1024).decode(errors="replace")
    parser = DownloadLinks()
    parser.feed(page)
    action = urljoin(url, parser.action or "")
    host = urlparse(action).hostname or ""
    if urlparse(url).hostname != "drive.google.com" or not parser.action or host not in (
        "drive.google.com", "drive.usercontent.google.com"
    ):
        raise ValueError("Server returned an HTML login/error page instead of an asset; check upstream access")
    separator = "&" if "?" in action else "?"
    response = opener.open(Request(action + separator + urlencode(parser.fields)), timeout=60)
    if "text/html" in response.headers.get("Content-Type", "").lower():
        response.close()
        raise ValueError("Google Drive requires login, is quota-limited, or denied access; no asset downloaded")
    return response


def download_file(item, directory, max_bytes):
    """Download one binary file atomically and verify checksums on repeat runs."""
    name = safe_filename(item["name"])
    if item.get("sha256") and not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
        raise ValueError("SHA-256 must contain 64 lowercase hexadecimal characters")
    if item.get("bytes") is not None and (type(item["bytes"]) is not int or item["bytes"] <= 0):
        raise ValueError("Expected download bytes must be a positive integer")
    destination = (Path(directory) / name).absolute()
    bundle = destination.with_name(destination.name + ".download")
    if destination.is_symlink() or bundle.is_symlink():
        raise ValueError("Download output cannot be a symbolic link")
    if destination.exists():
        raise FileExistsError(f"Preserving unmanaged file: {destination}")
    if bundle.exists():
        provenance = json.loads((bundle / "provenance.json").read_text())
        if (bundle / "payload").is_symlink():
            raise ValueError("Download payload cannot be a symbolic link")
        actual = sha256_file(bundle / "payload")
        if actual != provenance["sha256"] or (item.get("sha256") and actual != item["sha256"]):
            raise ValueError(f"Existing download is changed or differs from upstream: {bundle}")
        if provenance["request"] != item:
            raise ValueError(f"Existing download metadata differs; choose another output directory: {bundle}")
        return {"status": "already_present", "path": str(bundle / "payload"), "name": str(name)}
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = item.get("bytes")
    if expected and expected > max_bytes:
        raise ValueError(f"{name} exceeds --max-gb; no download started")
    reserve = 2 * 1024**3
    if shutil.disk_usage(destination.parent).free < (expected or max_bytes) + reserve:
        raise ValueError("Insufficient free space for download plus 2 GiB reserve")
    staging = bundle.with_name(bundle.name + "." + uuid.uuid4().hex + ".tmp")
    staging.mkdir()
    try:
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        with open_download(opener, item["url"]) as response:
            length = response.headers.get("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError("HTTP Content-Length exceeds --max-gb")
            count = 0
            with (staging / "payload").open("xb") as stream:
                while block := response.read(1024 * 1024):
                    if count == 0 and block.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                        raise ValueError("Server returned HTML content instead of a binary model")
                    count += len(block)
                    if count > max_bytes:
                        raise ValueError("Download exceeded --max-gb")
                    stream.write(block)
        if not count or (length and count != int(length)) or (expected and count != expected):
            raise ValueError("Incomplete or unexpected download size")
        actual = sha256_file(staging / "payload")
        if item.get("sha256") and actual != item["sha256"]:
            raise ValueError("Upstream SHA-256 mismatch")
        report = {
            "request": item, "bytes": count, "sha256": actual,
            "downloaded_utc": datetime.now(timezone.utc).isoformat(),
            "hash_verified_against_upstream": bool(item.get("sha256")),
            "simulation_status": "not_run", "grasp_success": None,
        }
        (staging / "provenance.json").write_text(json.dumps(report, indent=2) + "\n")
        staging.rename(bundle)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return {"status": "downloaded", "name": str(name), "path": str(bundle / "payload"), "bytes": count}


def run_download(args):
    """Build a selected-file plan or download it without installing dataset environments."""
    if args.source == "ycb":
        from dexterous_lab.assets.ycb import download_objects

        if args.manifest or args.url:
            raise ValueError("YCB samples use --files with sample names, not --manifest or --url")
        if args.list_files or args.dry_run:
            return list_files("ycb")
        if args.output_dir:
            raise ValueError("YCB uses the existing project catalog directory; omit --output-dir")
        return download_objects(args.files or ["cracker_box", "mustard_bottle", "mug"])
    if args.url:
        if args.source not in ("dexgraspnet", "gendexgrasp") or not args.files or len(args.files) != 1:
            raise ValueError("--url supports one named DexGraspNet/GenDexGrasp file via --files")
        config = SOURCES[args.source]
        items = [{"name": args.files[0], "url": args.url, "license": config["license"], "source_page": config["page"]}]
    else:
        items = list_files(args.source, args.manifest, args.hf_endpoint)
    if args.list_files:
        return items
    if args.files:
        lookup = {item["name"]: item for item in items}
        unknown = set(args.files) - lookup.keys()
        if unknown:
            raise ValueError(f"Unknown files: {sorted(unknown)}; use --list-files")
        items = [lookup[name] for name in args.files]
    elif args.source != "objaverse-xl":
        raise ValueError("Select explicit --files; use --list-files to inspect the provider")
    for item in items:
        safe_filename(item["name"])
        if urlparse(item["url"]).scheme != "https":
            raise ValueError("Download URL must use HTTPS")
    directory = args.output_dir or PROJECT_ROOT / "assets/objects" / args.source / "downloads"
    if args.dry_run:
        return {"source": args.source, "output_directory": str(directory), "files": items, "downloaded": False}
    if args.max_gb <= 0:
        raise ValueError("--max-gb must be positive")
    return [download_file(item, directory, args.max_gb * 1024**3) for item in items]
