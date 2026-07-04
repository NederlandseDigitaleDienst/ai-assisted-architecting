"""Tests for the Archi engine cache and fetch logic. No test hits the network
or downloads the real ~165 MB distribution: the download is monkeypatched to
lay down a fake binary, so cache-hit, auto-fetch and --no-download behaviour
are all exercised offline."""
import pytest

from archi_tool import engine
from archi_tool.model import ModelError


@pytest.fixture
def cache(tmp_path, monkeypatch):
    from archi_tool import normalize as normalize_mod

    monkeypatch.setenv("ARCHI_CACHE", str(tmp_path / "cache"))
    # no installed Archi and nothing on PATH, so lookups fall to the cache
    monkeypatch.delenv("ARCHI_APP", raising=False)
    monkeypatch.setattr(normalize_mod, "ARCHI_CANDIDATES", [])
    monkeypatch.setattr(normalize_mod.shutil, "which", lambda name: None)
    return tmp_path / "cache"


def _fake_binary(cache):
    """Place a stand-in binary where cached_binary() expects it."""
    key = engine._platform_key()
    _, rel = engine._PLATFORMS[key]
    binary = cache / engine.ARCHI_VERSION / rel
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_text("#!/bin/sh\n")
    return binary


def _fake_extract_into(target):
    """Lay down the binary under the extraction target (a staging dir), as a
    real extract would, so download_engine can move it into place."""
    _, rel = engine._PLATFORMS[engine._platform_key()]
    dest = target / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("#!/bin/sh\n")


class _fake_urlopen:
    """Minimal stand-in for urllib.request.urlopen as a context manager."""
    def __init__(self, text):
        self._data = text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self._data


def test_platform_binary_paths_match_distribution():
    """The binary paths inside each distribution, verified against the real
    5.9.0 artifacts. If a version bump changes the layout, this catches it."""
    assert engine._PLATFORMS["linux"][1] == "Archi/Archi"
    assert engine._PLATFORMS["windows"][1] == "Archi/Archi.exe"
    assert engine._PLATFORMS["darwin-arm64"][1] == (
        "Archi.app/Contents/MacOS/Archi")
    assert engine._PLATFORMS["darwin-x86_64"][1] == (
        "Archi.app/Contents/MacOS/Archi")


def test_cached_binary_none_when_empty(cache):
    assert engine.cached_binary() is None


def test_cached_binary_found_after_extract(cache):
    binary = _fake_binary(cache)
    assert engine.cached_binary() == binary


def test_download_engine_is_reused_when_present(cache, monkeypatch):
    binary = _fake_binary(cache)

    def explode(*a, **k):
        raise AssertionError("download must not run when the binary is cached")

    monkeypatch.setattr(engine, "_download", explode)
    assert engine.download_engine(quiet=True) == binary


def test_download_engine_fetches_and_extracts(cache, monkeypatch):
    calls = {}

    def fake_download(url, dest):
        calls["url"] = url
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"archive")

    def fake_extract(archive, key, target):
        # simulate the archive laying down the binary at its path under the
        # extraction target (a staging dir, which the code moves into place)
        _, rel = engine._PLATFORMS[engine._platform_key()]
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("#!/bin/sh\n")

    monkeypatch.setattr(engine, "_download", fake_download)
    monkeypatch.setattr(engine, "_extract", fake_extract)
    # skip checksum lookup (would hit the network); covered by its own tests
    monkeypatch.setattr(engine, "_expected_sha1", lambda asset: None)

    binary = engine.download_engine(quiet=True)
    assert binary.exists()
    assert engine.ARCHI_VERSION in calls["url"]
    assert calls["url"].startswith(
        "https://github.com/archimatetool/archi.io/releases/download")


def test_checksum_mismatch_aborts_download(cache, monkeypatch):
    def fake_download(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"tampered archive")

    monkeypatch.setattr(engine, "_download", fake_download)
    monkeypatch.setattr(engine, "_expected_sha1", lambda asset: "deadbeef")
    # extraction must never run on a bad archive
    monkeypatch.setattr(engine, "_extract", lambda *a: pytest.fail(
        "extract must not run after a checksum mismatch"))
    with pytest.raises(ModelError, match="Checksum"):
        engine.download_engine(quiet=True)


def test_checksum_absent_does_not_block(cache, monkeypatch):
    """A transient failure to fetch SUMSSHA1 must not block install."""
    def fake_download(url, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"archive")

    monkeypatch.setattr(engine, "_download", fake_download)
    monkeypatch.setattr(engine, "_expected_sha1", lambda asset: None)
    monkeypatch.setattr(engine, "_extract", lambda a, k, t: _fake_extract_into(t))
    assert engine.download_engine(quiet=True).exists()


def test_which_does_not_return_own_entry_point(tmp_path, monkeypatch):
    """On case-insensitive filesystems which("Archi") can resolve to our own
    `archi` CLI. find_archi_binary must reject that, not drive itself."""
    from archi_tool import normalize as normalize_mod

    bindir = tmp_path / "bin"
    bindir.mkdir()
    # a single file that both `archi` and `Archi` resolve to (the collision)
    entry = bindir / "archi"
    entry.write_text("#!/bin/sh\n")
    entry.chmod(0o755)

    monkeypatch.delenv("ARCHI_APP", raising=False)
    monkeypatch.setenv("ARCHI_CACHE", str(tmp_path / "empty-cache"))
    monkeypatch.setattr(normalize_mod, "ARCHI_CANDIDATES", [])

    def fake_which(name):
        # both names resolve to the same file, as on a case-insensitive FS
        return str(entry) if name.lower() == "archi" else None

    monkeypatch.setattr(normalize_mod.shutil, "which", fake_which)
    assert normalize_mod.find_archi_binary() is None


def test_cache_wins_over_path(cache, monkeypatch):
    """A downloaded engine in the cache must be preferred over a PATH match."""
    from archi_tool import normalize as normalize_mod

    binary = _fake_binary(cache)
    monkeypatch.setattr(
        normalize_mod.shutil, "which", lambda n: "/somewhere/Archi")
    assert normalize_mod.find_archi_binary() == str(binary)


def test_normalize_no_download_fails_without_engine(cache, tmp_path):
    from archi_tool.normalize import normalize
    model = tmp_path / "m.archimate"
    model.write_text('<?xml version="1.0"?><model/>', encoding="utf-8")
    with pytest.raises(ModelError, match="Archi niet gevonden"):
        normalize(str(model), download=False)


def test_unsafe_archive_member_is_rejected(cache, tmp_path):
    import tarfile

    # a tar entry that would escape the target directory
    payload = tmp_path / "evil.txt"
    payload.write_text("x")
    archive = tmp_path / "evil.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(payload, arcname="../escape.txt")
    with tarfile.open(archive, "r:gz") as tar:
        with pytest.raises(ModelError, match="Onveilig pad"):
            engine._safe_extract_tar(tar, tmp_path / "out")


def test_symlink_escape_in_tar_is_rejected(cache, tmp_path):
    """A symlink pointing outside the tree plus a file written through it is
    the classic tar-slip that a name-only check misses; filter="data" catches
    it."""
    import io
    import tarfile

    archive = tmp_path / "evil.tgz"
    with tarfile.open(archive, "w:gz") as tar:
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc"        # escapes the extraction target
        tar.addfile(link)
        member = tarfile.TarInfo("link/pwned")
        data = b"x"
        member.size = len(data)
        tar.addfile(member, io.BytesIO(data))
    with tarfile.open(archive, "r:gz") as tar:
        with pytest.raises(ModelError, match="Onveilig pad"):
            engine._safe_extract_tar(tar, tmp_path / "out")
    # nothing escaped
    assert not (tmp_path / "out" / "pwned").exists()


def test_mount_point_parsing_picks_volumes_line():
    # realistic multi-line hdiutil output; only the /Volumes line is the mount
    stdout = (
        "/dev/disk4          \tGUID_partition_scheme\t\n"
        "/dev/disk4s1        \tApple_APFS         \t\n"
        "/dev/disk4s2        \tApple_HFS          \t/Volumes/Archi\n")
    assert engine._parse_mount_point(stdout) == "/Volumes/Archi"


def test_mount_point_parsing_none_when_absent():
    assert engine._parse_mount_point("/dev/disk4\tApple_APFS\t\n") is None


def test_arm_linux_is_refused(monkeypatch):
    monkeypatch.setattr(engine.platform, "system", lambda: "Linux")
    monkeypatch.setattr(engine.platform, "machine", lambda: "aarch64")
    with pytest.raises(ModelError, match="x86_64"):
        engine._platform_key()


def test_checksum_file_without_asset_line_fails(cache, monkeypatch):
    """A fetched SUMSSHA1 that lists no hash for our asset is suspicious and
    must fail, not silently skip verification."""
    monkeypatch.setattr(
        engine.urllib.request, "urlopen",
        lambda url: _fake_urlopen("deadbeef  some-other-file.zip\n"))
    with pytest.raises(ModelError, match="geen hash"):
        engine._expected_sha1(f"Archi-Win64-{engine.ARCHI_VERSION}.zip")
