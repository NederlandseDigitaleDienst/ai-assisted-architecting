"""End-to-end tests for the CLI: exit codes, Dutch messages, error paths."""
from archi_tool.cli import main


def run(capsys, *argv):
    status = main(list(argv))
    captured = capsys.readouterr()
    return status, captured.out + captured.err


def test_validate_clean_model(model_path, capsys):
    status, output = run(capsys, "--model", str(model_path), "validate")
    assert status == 0
    assert "OK: het model is consistent." in output


def test_missing_file_gives_dutch_error(tmp_path, capsys):
    missing = tmp_path / "bestaat-niet.archimate"
    status, output = run(capsys, "--model", str(missing), "validate")
    assert status == 1
    assert output.startswith("FOUT: kan")


def test_unparseable_file_gives_dutch_error(tmp_path, capsys):
    corrupt = tmp_path / "kapot.archimate"
    corrupt.write_text('<?xml version="1.0"?><kapot', encoding="utf-8")
    status, output = run(capsys, "--model", str(corrupt), "validate")
    assert status == 1
    assert output.startswith("FOUT: kan")


def test_normalize_skips_lxml_parse(tmp_path, capsys, monkeypatch):
    """normalize must reach Archi-binary detection even when lxml cannot
    parse the file; only the missing binary may stop it here."""
    monkeypatch.setenv("ARCHI_APP", str(tmp_path / "geen-archi"))
    corrupt = tmp_path / "kapot.archimate"
    corrupt.write_text('<?xml version="1.0"?><kapot', encoding="utf-8")
    status, output = run(capsys, "--model", str(corrupt), "normalize")
    assert status == 1
    assert "Archi niet gevonden" in output


def test_mutation_refuses_invalid_and_reports(model_path, capsys):
    status, output = run(capsys, "--model", str(model_path), "add-relation",
                         "--type", "Influence",
                         "--source", "Testview", "--target", "Doel Gamma")
    assert status == 1
    assert "is een view" in output


def test_set_property_confirms(model_path, capsys):
    status, output = run(capsys, "--model", str(model_path), "set-property",
                         "id-el-alfa", "Bron=test")
    assert status == 0
    assert "Property gezet op 'id-el-alfa': Bron = test" in output


def test_rename_confirms(model_path, capsys):
    status, output = run(capsys, "--model", str(model_path), "rename",
                         "id-el-beta", "Bouwblok Beta 2")
    assert status == 0
    assert "heet nu 'Bouwblok Beta 2'" in output


def test_unknown_property_key_warns(model_path, capsys, tmp_path):
    """The conventions check runs when docs/conventies.md sits two levels
    above the model, mirroring the repo layout."""
    repo = tmp_path / "repo"
    (repo / "models").mkdir(parents=True)
    (repo / "docs").mkdir()
    (repo / "docs" / "conventies.md").write_text(
        "## 3. Property-keys\n\n- `Bron` — bronverwijzing\n",
        encoding="utf-8")
    nested = repo / "models" / "model.archimate"
    nested.write_bytes(model_path.read_bytes())

    status, output = run(capsys, "--model", str(nested), "set-property",
                         "id-el-alfa", "Vrije-key=x")
    assert status == 0
    assert "WAARSCHUWING: Property-key 'Vrije-key'" in output


def test_tree_shows_nested_folders(model_path, capsys):
    """Models organised in subfolders (Archi allows arbitrary nesting) must
    show every folder and its elements, not just the top level."""
    from lxml import etree

    tree = etree.parse(str(model_path))
    strategy = tree.getroot().find("folder[@name='Strategy']")
    sub = etree.SubElement(strategy, "folder", {
        "name": "Thema X", "id": "id-folder-thema-x"})
    beta = strategy.find("element[@name='Bouwblok Beta']")
    strategy.remove(beta)
    sub.append(beta)
    tree.write(str(model_path), encoding="utf-8", xml_declaration=True)

    status, output = run(capsys, "--model", str(model_path), "tree")
    assert status == 0
    assert "Strategy (strategy): 1 item(s)" in output
    assert "  Thema X: 1 item(s)" in output
    assert "Bouwblok Beta" in output
