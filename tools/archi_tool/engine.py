"""Fetch and cache the Archi engine so `normalize` works without a manual
install.

`normalize` drives Archi's headless command-line application. Archi is a full
cross-platform desktop distribution (~165 MB, with a bundled Java runtime, so
it is self-contained) published on GitHub releases at ``archimatetool/archi.io``.
There is no smaller headless-only artifact; we download the full distribution
once, cache it per user, and point ARCHI_APP at the extracted binary.

The version is pinned so the download is deterministic and reproducible. Bump
ARCHI_VERSION deliberately. archi.io only keeps the latest release online,
though, so once Archi publishes a newer version the pinned one disappears. In
that case we fall back to the latest release, with a warning, rather than
leaving `normalize` broken until someone bumps the pin (ADR 0011).
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from .model import ModelError

ARCHI_VERSION = "5.10.0"
RELEASES = "https://github.com/archimatetool/archi.io/releases"
RELEASES_API = "https://api.github.com/repos/archimatetool/archi.io/releases"

# per platform: (asset filename pattern, relative path to the binary inside
# the extracted tree). Archi bundles its own JRE, so no system Java is needed.
_PLATFORMS = {
    "linux": ("Archi-Linux64-{version}.tgz", "Archi/Archi"),
    "windows": ("Archi-Win64-{version}.zip", "Archi/Archi.exe"),
    # macOS ships a .dmg; both Intel and Apple Silicon expose the same binary
    # path once the app bundle is copied out of the mounted image
    "darwin-arm64": ("Archi-Mac-Silicon-{version}.dmg",
                     "Archi.app/Contents/MacOS/Archi"),
    "darwin-x86_64": ("Archi-Mac-{version}.dmg",
                      "Archi.app/Contents/MacOS/Archi"),
}


def cache_dir() -> Path:
    """Per-user cache root, overridable for tests and air-gapped setups."""
    override = os.environ.get("ARCHI_CACHE")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(base) / "archi-cli"


def _platform_key() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        # Archi ships both Intel and Apple Silicon builds
        return "darwin-arm64" if machine in ("arm64", "aarch64") else "darwin-x86_64"
    if system in ("linux", "windows"):
        # only 64-bit x86 builds exist; refuse ARM rather than hand back an
        # unrunnable x86 binary that fails cryptically at normalize time
        if machine not in ("x86_64", "amd64"):
            raise ModelError(
                f"Archi levert alleen een x86_64-build voor {system}, geen "
                f"'{machine}'. Installeer Archi handmatig en zet ARCHI_APP.")
        return system
    raise ModelError(
        f"Geen Archi-download bekend voor platform '{system}'. Installeer "
        "Archi handmatig en zet ARCHI_APP.")


def _version_key(version: str) -> tuple:
    return tuple(int(p) if p.isdigit() else 0 for p in version.split("."))


def cached_binary() -> Path | None:
    """An extracted engine binary in the cache, if present: the pinned
    version when available, otherwise the newest cached one (left behind by
    a fallback download), so a fallback does not refetch on every run."""
    _, rel = _PLATFORMS[_platform_key()]
    root = cache_dir()
    pinned = root / ARCHI_VERSION / rel
    if pinned.exists():
        return pinned
    if not root.is_dir():
        return None
    versions = [d.name for d in root.iterdir()
                if d.is_dir() and (d / rel).exists()
                and not d.name.endswith(".staging")]
    if not versions:
        return None
    return root / max(versions, key=_version_key) / rel


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    # a plain urlopen keeps the dependency footprint at zero beyond stdlib
    with urllib.request.urlopen(url) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


def _fetch_text(url) -> str | None:
    """GET a small text file; None when it does not exist (HTTP 404)."""
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise ModelError(f"Kon {url} niet ophalen: {exc}") from exc
    except OSError as exc:
        raise ModelError(f"Kon {url} niet ophalen: {exc}") from exc


def _tag_candidates(version: str) -> list[str]:
    """Release tags archi.io has used for a version: "5.9.0" for older
    releases, "5.10_0" (last dot as underscore) since 5.10."""
    head, _, last = version.rpartition(".")
    return [version, f"{head}_{last}"] if head else [version]


def _latest_tag() -> str:
    """Tag of the latest release, read from the /releases/latest redirect
    (no API call, so no rate limit)."""
    try:
        with urllib.request.urlopen(f"{RELEASES}/latest") as response:
            final_url = response.geturl()
    except OSError as exc:
        raise ModelError(
            f"Kon de nieuwste Archi-release niet bepalen: {exc}") from exc
    tag = final_url.rstrip("/").rsplit("/", 1)[-1]
    if "/releases/tag/" not in final_url or not tag:
        raise ModelError(
            f"Kon de nieuwste Archi-release niet bepalen uit {final_url}")
    return tag


def _checksums_url(tag: str, version: str) -> str:
    return f"{RELEASES}/download/{tag}/Archi-{version}-SUMSSHA1"


def resolve_release(*, quiet=False) -> tuple[str, str, str]:
    """(version, tag, SUMSSHA1 text) of the release to download.

    The pinned version when it is still online, else the latest release. The
    checksum file doubles as the existence probe, and fetching it first means
    every download is verified.
    """
    for tag in _tag_candidates(ARCHI_VERSION):
        sums = _fetch_text(_checksums_url(tag, ARCHI_VERSION))
        if sums is not None:
            return ARCHI_VERSION, tag, sums
    tag = _latest_tag()
    version = tag.replace("_", ".")
    sums = _fetch_text(_checksums_url(tag, version))
    if sums is None:
        raise ModelError(
            f"Archi {ARCHI_VERSION} staat niet meer online en de nieuwste "
            f"release ({tag}) heeft geen checksumbestand. Installeer Archi "
            "handmatig en zet ARCHI_APP.")
    if not quiet:
        print(f"WAARSCHUWING: Archi {ARCHI_VERSION} staat niet meer online; "
              f"de nieuwste versie {version} wordt gebruikt.", file=sys.stderr)
    return version, tag, sums


def _expected_sha1(asset: str, sums: str) -> str:
    """The hash for ``asset`` from a SUMSSHA1 text. A checksum file that does
    not list the asset is suspicious (renamed or tampered manifest), so that
    raises rather than skipping verification."""
    for line in sums.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            return parts[0].lower()
    raise ModelError(
        f"Checksumbestand bevat geen hash voor {asset}; verificatie "
        "afgebroken.")


def _hash(path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha1(path) -> str:
    return _hash(path, "sha1")


def _github_sha256(tag: str, asset: str) -> str | None:
    """The SHA-256 that GitHub computed for ``asset`` when it was uploaded,
    from the releases API; None when the API is unreachable or rate limited.
    A token in GITHUB_TOKEN or GH_TOKEN (set in CI) raises the rate limit."""
    request = urllib.request.Request(
        f"{RELEASES_API}/tags/{tag}",
        headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request) as response:
            release = json.load(response)
    except (OSError, ValueError):
        return None
    for item in release.get("assets", []):
        digest = item.get("digest") or ""
        if item.get("name") == asset and digest.startswith("sha256:"):
            return digest.removeprefix("sha256:").lower()
    return None


def _verify(archive, asset: str, expected_sha1: str, tag: str,
            *, quiet=False):
    """Check the download against archi.io's SUMSSHA1 list. That list has
    been wrong before (5.10.0 lists a stale hash for the Windows zip), so a
    mismatch is checked against the digest GitHub itself recorded at upload
    before it fails: a file that matches that is byte-identical to the
    published asset."""
    actual = _sha1(archive)
    if actual == expected_sha1:
        return
    github = _github_sha256(tag, asset)
    if github is not None and _hash(archive, "sha256") == github:
        if not quiet:
            print(f"WAARSCHUWING: de checksumlijst van Archi noemt voor "
                  f"{asset} een verouderde hash; de download is geverifieerd "
                  "tegen de SHA-256 die GitHub bij de upload vastlegde.",
                  file=sys.stderr)
        return
    raise ModelError(
        f"Checksum van {asset} klopt niet (verwacht {expected_sha1}, "
        f"kreeg {actual}); download afgebroken.")


def _extract(archive, key, target):
    """Unpack the downloaded archive into ``target``; format follows platform."""
    if key == "linux":
        with tarfile.open(archive, "r:gz") as tar:
            _safe_extract_tar(tar, target)
    elif key == "windows":
        with zipfile.ZipFile(archive) as zf:
            _safe_extract_zip(zf, target)
    else:  # macOS .dmg: mount, copy the .app out, unmount
        _extract_dmg(archive, target)


def _is_within(base, target) -> bool:
    base = Path(base).resolve()
    try:
        Path(target).resolve().relative_to(base)
        return True
    except ValueError:
        return False


def _safe_extract_tar(tar, target):
    # filter="data" (Python 3.12+) refuses absolute paths, parent traversal,
    # and — crucially — symlinks/hardlinks that point outside the tree, which a
    # name-only check misses. The Archi tgz has 145 legit *relative in-tree*
    # symlinks (bundled JRE license files), which this filter allows.
    try:
        tar.extractall(target, filter="data")
    except tarfile.FilterError as exc:
        raise ModelError(f"Onveilig pad in archief: {exc}") from exc


def _safe_extract_zip(zf, target):
    # zip has no symlink members, so a name check is sufficient here
    for name in zf.namelist():
        if not _is_within(target, Path(target) / name):
            raise ModelError(f"Onveilig pad in archief: {name}")
    zf.extractall(target)


def _parse_mount_point(hdiutil_stdout) -> str | None:
    """Extract the /Volumes mount point from `hdiutil attach` output.

    Output is tab-separated with a dev node, a type and (for the data volume)
    a mount point. A multi-partition image has extra lines without a mount
    point, so we select the line whose last field is an actual /Volumes path
    rather than blindly taking the last line.
    """
    for line in reversed(hdiutil_stdout.splitlines()):
        field = line.split("\t")[-1].strip()
        if field.startswith("/Volumes/"):
            return field
    return None


def _extract_dmg(archive, target):
    """Mount a .dmg, copy the Archi.app out, detach again. macOS only."""
    mount = subprocess.run(
        ["hdiutil", "attach", "-nobrowse", "-readonly", str(archive)],
        capture_output=True, text=True)
    if mount.returncode != 0:
        raise ModelError("Kon de Archi-.dmg niet mounten:\n" + mount.stderr)
    mount_point = _parse_mount_point(mount.stdout)
    if not mount_point:
        raise ModelError(
            "Kon het mountpunt van de Archi-.dmg niet bepalen:\n"
            + mount.stdout)
    try:
        source = Path(mount_point) / "Archi.app"
        if not source.exists():
            raise ModelError(
                f"Archi.app niet gevonden in de gemounte image ({mount_point})")
        Path(target).mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, Path(target) / "Archi.app")
    finally:
        detach = subprocess.run(["hdiutil", "detach", mount_point],
                                capture_output=True, text=True)
        if detach.returncode != 0:
            # a copytree can leave the volume briefly busy; force as a fallback
            subprocess.run(["hdiutil", "detach", "-force", mount_point],
                           capture_output=True, text=True)


def find_or_none():
    """Any already-available Archi binary (installed, on PATH, or cached),
    without triggering a download. Returns a path string or None."""
    from .normalize import find_archi_binary
    return find_archi_binary()


def download_engine(*, quiet=False) -> Path:
    """Download and extract the Archi engine into the cache. Returns the
    binary path. Raises ModelError on any failure.

    Extraction happens in a staging directory and is only moved into place
    atomically once the binary is present, so a crash mid-extract never leaves
    a half-populated cache that later looks complete.
    """
    cached = cached_binary()
    if cached is not None:
        return cached
    key = _platform_key()
    pattern, rel = _PLATFORMS[key]
    version, tag, sums = resolve_release(quiet=quiet)
    asset = pattern.format(version=version)
    expected = _expected_sha1(asset, sums)
    version_dir = cache_dir() / version
    binary = version_dir / rel

    url = f"{RELEASES}/download/{tag}/{asset}"
    if not quiet:
        print(f"Archi-engine ophalen ({asset}, ~165 MB, eenmalig) …")
    cache_dir().mkdir(parents=True, exist_ok=True)
    staging = version_dir.with_name(f"{version}.staging")
    shutil.rmtree(staging, ignore_errors=True)
    archive = staging / "_download" / asset
    try:
        _download(url, archive)
        _verify(archive, asset, expected, tag, quiet=quiet)
        _extract(archive, key, staging)
        shutil.rmtree(staging / "_download", ignore_errors=True)
        staged_binary = staging / rel
        if not staged_binary.exists():
            raise ModelError(
                "Archi-engine uitgepakt maar de binary staat niet op de "
                f"verwachte plek: {staged_binary}")
        if key != "windows":
            staged_binary.chmod(0o755)
        # atomic swap into the real cache location
        shutil.rmtree(version_dir, ignore_errors=True)
        os.replace(staging, version_dir)
    except OSError as exc:
        raise ModelError(
            f"Kon de Archi-engine niet ophalen van {url}: {exc}") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return binary
