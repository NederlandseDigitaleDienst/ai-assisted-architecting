"""Fetch and cache the Archi engine so `normalize` works without a manual
install.

`normalize` drives Archi's headless command-line application. Archi is a full
cross-platform desktop distribution (~165 MB, with a bundled Java runtime, so
it is self-contained) published on GitHub releases at ``archimatetool/archi.io``.
There is no smaller headless-only artifact; we download the full distribution
once, cache it per user, and point ARCHI_APP at the extracted binary.

The version is pinned so the download is deterministic and reproducible. Bump
ARCHI_VERSION deliberately.
"""
from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

from .model import ModelError

ARCHI_VERSION = "5.9.0"
RELEASE_BASE = (
    "https://github.com/archimatetool/archi.io/releases/download"
    f"/{ARCHI_VERSION}")

# per platform: (asset filename, relative path to the binary inside the
# extracted tree). Archi bundles its own JRE, so no system Java is needed.
_PLATFORMS = {
    "linux": (
        f"Archi-Linux64-{ARCHI_VERSION}.tgz",
        "Archi/Archi"),
    "windows": (
        f"Archi-Win64-{ARCHI_VERSION}.zip",
        "Archi/Archi.exe"),
    # macOS ships a .dmg; both Intel and Apple Silicon expose the same binary
    # path once the app bundle is copied out of the mounted image
    "darwin-arm64": (
        f"Archi-Mac-Silicon-{ARCHI_VERSION}.dmg",
        "Archi.app/Contents/MacOS/Archi"),
    "darwin-x86_64": (
        f"Archi-Mac-{ARCHI_VERSION}.dmg",
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


def cached_binary() -> Path | None:
    """The extracted engine binary for the pinned version, if present."""
    key = _platform_key()
    _, rel = _PLATFORMS[key]
    binary = cache_dir() / ARCHI_VERSION / rel
    return binary if binary.exists() else None


def _download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    # a plain urlopen keeps the dependency footprint at zero beyond stdlib
    with urllib.request.urlopen(url) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


def _expected_sha1(asset) -> str | None:
    """Fetch the release's SUMSSHA1 file and return the hash for ``asset``.

    Returns None only when the checksum file can't be fetched (a transient
    network failure shouldn't block install; the download itself is over HTTPS
    from GitHub). If the file *is* fetched but lists no hash for ``asset``,
    that is suspicious (renamed/tampered manifest) and raises rather than
    silently skipping verification.
    """
    url = f"{RELEASE_BASE}/Archi-{ARCHI_VERSION}-SUMSSHA1"
    try:
        with urllib.request.urlopen(url) as response:
            text = response.read().decode("utf-8", "replace")
    except OSError:
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("*") == asset:
            return parts[0].lower()
    raise ModelError(
        f"Checksumbestand bevat geen hash voor {asset}; verificatie "
        "afgebroken.")


def _sha1(path) -> str:
    digest = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise ModelError(f"Onveilig pad in archief: {exc}")


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
    """Download and extract the pinned Archi engine into the cache. Returns
    the binary path. Raises ModelError on any failure.

    Extraction happens in a staging directory and is only moved into place
    atomically once the binary is present, so a crash mid-extract never leaves
    a half-populated cache that later looks complete.
    """
    key = _platform_key()
    asset, rel = _PLATFORMS[key]
    version_dir = cache_dir() / ARCHI_VERSION
    binary = version_dir / rel
    if binary.exists():
        return binary

    url = f"{RELEASE_BASE}/{asset}"
    if not quiet:
        print(f"Archi-engine ophalen ({asset}, ~165 MB, eenmalig) …")
    cache_dir().mkdir(parents=True, exist_ok=True)
    staging = version_dir.with_name(f"{ARCHI_VERSION}.staging")
    shutil.rmtree(staging, ignore_errors=True)
    archive = staging / "_download" / asset
    try:
        _download(url, archive)
        expected = _expected_sha1(asset)
        if expected is not None:
            actual = _sha1(archive)
            if actual != expected:
                raise ModelError(
                    f"Checksum van {asset} klopt niet (verwacht {expected}, "
                    f"kreeg {actual}); download afgebroken.")
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
            f"Kon de Archi-engine niet ophalen van {url}: {exc}")
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    return binary
