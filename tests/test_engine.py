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


def _asset(version=None):
    pattern, _ = engine._PLATFORMS[engine._platform_key()]
    return pattern.format(version=version or engine.ARCHI_VERSION)


def _fake_network(monkeypatch, texts, latest_tag=None):
    """Serve SUMSSHA1 files from ``texts`` ({url: text}); any other URL is a
    404. Records every downloaded URL; the archive bytes are b"archive"."""
    calls = {"fetched": [], "downloaded": []}

    def fake_fetch(url):
        calls["fetched"].append(url)
        return texts.get(url)

    def fake_download(url, dest):
        calls["downloaded"].append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"archive")

    def fake_latest():
        if latest_tag is None:
            raise AssertionError("latest release must not be looked up")
        return latest_tag

    monkeypatch.setattr(engine, "_fetch_text", fake_fetch)
    monkeypatch.setattr(engine, "_download", fake_download)
    monkeypatch.setattr(engine, "_latest_tag", fake_latest)
    monkeypatch.setattr(engine, "_github_sha256", lambda tag, asset: None)
    monkeypatch.setattr(engine, "_extract", lambda a, k, t: _fake_extract_into(t))
    return calls


def _sums(version, sha1=None):
    import hashlib
    digest = sha1 or hashlib.sha1(b"archive").hexdigest()
    return f"{digest}    {_asset(version)}\n"


RELEASES = "https://github.com/archimatetool/archi.io/releases"


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
    """The binary paths inside each distribution, as in the real 5.9.0 and
    5.10.0 artifacts (engine-e2e checks them for real on every platform)."""
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


def test_tag_candidates_cover_both_tag_formats():
    assert engine._tag_candidates("5.9.0") == ["5.9.0", "5.9_0"]
    assert engine._tag_candidates("5.10.0") == ["5.10.0", "5.10_0"]


def test_download_uses_pinned_version_under_new_tag_format(cache, monkeypatch):
    # since 5.10 the tag is "5.10_0" while assets keep "5.10.0"
    head, _, last = engine.ARCHI_VERSION.rpartition(".")
    tag = f"{head}_{last}"
    sums_url = f"{RELEASES}/download/{tag}/Archi-{engine.ARCHI_VERSION}-SUMSSHA1"
    calls = _fake_network(monkeypatch, {sums_url: _sums(engine.ARCHI_VERSION)})

    binary = engine.download_engine(quiet=True)
    assert binary == cache / engine.ARCHI_VERSION / engine._PLATFORMS[
        engine._platform_key()][1]
    assert calls["downloaded"] == [f"{RELEASES}/download/{tag}/{_asset()}"]


def test_download_falls_back_to_latest_when_pin_is_gone(cache, monkeypatch,
                                                       capsys):
    sums_url = f"{RELEASES}/download/9.1_0/Archi-9.1.0-SUMSSHA1"
    calls = _fake_network(monkeypatch, {sums_url: _sums("9.1.0")},
                          latest_tag="9.1_0")

    binary = engine.download_engine()
    assert binary.exists()
    assert binary.is_relative_to(cache / "9.1.0")
    assert calls["downloaded"] == [f"{RELEASES}/download/9.1_0/{_asset('9.1.0')}"]
    err = capsys.readouterr().err
    assert f"Archi {engine.ARCHI_VERSION} staat niet meer online" in err
    assert "9.1.0" in err

    # the fallback engine is reused afterwards, without any network access
    monkeypatch.setattr(engine, "_fetch_text", lambda url: pytest.fail(
        "a cached fallback engine must not trigger a lookup"))
    assert engine.cached_binary() == binary
    assert engine.download_engine(quiet=True) == binary


def test_cached_pinned_version_wins_over_other_cached_versions(cache):
    _, rel = engine._PLATFORMS[engine._platform_key()]
    other = cache / "99.0.0" / rel
    other.parent.mkdir(parents=True)
    other.write_text("#!/bin/sh\n")
    pinned = _fake_binary(cache)
    assert engine.cached_binary() == pinned


def test_no_release_with_checksums_fails_clearly(cache, monkeypatch):
    _fake_network(monkeypatch, {}, latest_tag="9.1_0")
    with pytest.raises(ModelError, match="ARCHI_APP"):
        engine.download_engine(quiet=True)


def test_checksum_mismatch_aborts_download(cache, monkeypatch):
    sums_url = (f"{RELEASES}/download/{engine.ARCHI_VERSION}/"
                f"Archi-{engine.ARCHI_VERSION}-SUMSSHA1")
    _fake_network(monkeypatch,
                  {sums_url: _sums(engine.ARCHI_VERSION, sha1="deadbeef")})
    # extraction must never run on a bad archive
    monkeypatch.setattr(engine, "_extract", lambda *a: pytest.fail(
        "extract must not run after a checksum mismatch"))
    with pytest.raises(ModelError, match="Checksum"):
        engine.download_engine(quiet=True)


def test_stale_checksum_list_is_rescued_by_github_digest(cache, monkeypatch,
                                                         capsys):
    """archi.io's SUMSSHA1 for 5.10.0 lists a stale hash for the Windows zip;
    the digest GitHub recorded at upload settles it."""
    import hashlib
    sums_url = (f"{RELEASES}/download/{engine.ARCHI_VERSION}/"
                f"Archi-{engine.ARCHI_VERSION}-SUMSSHA1")
    _fake_network(monkeypatch,
                  {sums_url: _sums(engine.ARCHI_VERSION, sha1="deadbeef")})
    seen = {}

    def github_digest(tag, asset):
        seen["asked"] = (tag, asset)
        return hashlib.sha256(b"archive").hexdigest()

    monkeypatch.setattr(engine, "_github_sha256", github_digest)
    assert engine.download_engine().exists()
    assert seen["asked"] == (engine.ARCHI_VERSION, _asset())
    assert "verouderde hash" in capsys.readouterr().err


def test_checksum_mismatch_fails_when_github_digest_also_differs(cache,
                                                               monkeypatch):
    sums_url = (f"{RELEASES}/download/{engine.ARCHI_VERSION}/"
                f"Archi-{engine.ARCHI_VERSION}-SUMSSHA1")
    _fake_network(monkeypatch,
                  {sums_url: _sums(engine.ARCHI_VERSION, sha1="deadbeef")})
    monkeypatch.setattr(engine, "_github_sha256",
                        lambda tag, asset: "0" * 64)
    monkeypatch.setattr(engine, "_extract", lambda *a: pytest.fail(
        "extract must not run after a checksum mismatch"))
    with pytest.raises(ModelError, match="Checksum"):
        engine.download_engine(quiet=True)


def test_github_digest_read_from_release_api(monkeypatch):
    import json
    release = {"assets": [
        {"name": "Archi-Win64-5.10.0.zip", "digest": "sha256:ABC123"},
        {"name": "other.zip", "digest": "sha256:fff"}]}
    seen = {}

    def fake_urlopen(request):
        seen["url"] = request.full_url
        return _fake_urlopen(json.dumps(release))

    monkeypatch.setattr(engine.urllib.request, "urlopen", fake_urlopen)
    assert engine._github_sha256("5.10_0", "Archi-Win64-5.10.0.zip") == "abc123"
    assert seen["url"].endswith("/releases/tags/5.10_0")


def test_network_failure_is_a_model_error(cache, monkeypatch):
    import urllib.error

    def offline(url):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(engine.urllib.request, "urlopen", offline)
    with pytest.raises(ModelError, match="niet ophalen"):
        engine.download_engine(quiet=True)


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


def test_checksum_file_without_asset_line_fails():
    """A SUMSSHA1 that lists no hash for our asset is suspicious and must
    fail, not silently skip verification."""
    with pytest.raises(ModelError, match="geen hash"):
        engine._expected_sha1(f"Archi-Win64-{engine.ARCHI_VERSION}.zip",
                              "deadbeef  some-other-file.zip\n")


def test_latest_tag_read_from_redirect(monkeypatch):
    class Response(_fake_urlopen):
        def geturl(self):
            return f"{RELEASES}/tag/5.10_0"

    monkeypatch.setattr(engine.urllib.request, "urlopen",
                        lambda url: Response(""))
    assert engine._latest_tag() == "5.10_0"
