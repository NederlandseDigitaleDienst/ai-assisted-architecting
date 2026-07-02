from archi_tool.normalize import find_archi_binary


def test_archi_app_override_wins(monkeypatch, tmp_path):
    fake = tmp_path / "Archi"
    fake.write_text("", encoding="utf-8")
    monkeypatch.setenv("ARCHI_APP", str(fake))
    assert find_archi_binary() == str(fake)


def test_archi_app_override_does_not_fall_through(monkeypatch, tmp_path):
    monkeypatch.setenv("ARCHI_APP", str(tmp_path / "bestaat-niet"))
    assert find_archi_binary() is None
