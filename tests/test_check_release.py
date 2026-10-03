"""The release consistency check: versions in all files agree, and a release
tag needs a matching changelog section."""

import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location(
    "check_release", ROOT / "scripts" / "check_release.py"
)
check_release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_release)


def copy_repo_files(tmp_path):
    for name in ("pyproject.toml", "uv.lock", "publiccode.yml", "CHANGELOG.md"):
        shutil.copy(ROOT / name, tmp_path / name)
    (tmp_path / ".claude-plugin").mkdir()
    shutil.copy(ROOT / ".claude-plugin" / "plugin.json", tmp_path / ".claude-plugin")
    return tmp_path


def test_repository_versions_agree():
    errors, _ = check_release.check(root=ROOT)
    assert errors == []


def test_diverging_version_is_reported(tmp_path):
    root = copy_repo_files(tmp_path)
    plugin = root / ".claude-plugin" / "plugin.json"
    plugin.write_text(
        plugin.read_text().replace('"version": "', '"version": "9.9.9-'), "utf-8"
    )
    errors, _ = check_release.check(root=root)
    assert any("Versies lopen uiteen" in e for e in errors)


def test_release_needs_matching_tag_and_changelog(tmp_path):
    root = copy_repo_files(tmp_path)
    version = check_release.versions(root)["pyproject.toml"]
    errors, notes = check_release.check(tag=f"v{version}", root=root)
    assert errors == []
    assert notes and "###" in notes  # the section body, without its heading
    errors, _ = check_release.check(tag="v0.0.0", root=root)
    assert any("Tag v0.0.0" in e for e in errors)
    (root / "CHANGELOG.md").write_text("# Changelog\n", "utf-8")
    errors, _ = check_release.check(tag=f"v{version}", root=root)
    assert any("geen gevulde sectie" in e for e in errors)
