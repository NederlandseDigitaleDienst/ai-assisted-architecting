"""Model files are untrusted input: entities and DTDs must never pull local
files or URLs into the model."""
import pytest
from lxml import etree

from archi_tool.model import ArchiModel

MODEL_TAIL = """
<archimate:model xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:archimate="http://www.archimatetool.com/archimate"
    name="&leak;" id="id-m" version="5.0.0">
  <folder name="Views" id="id-f" type="diagrams"/>
</archimate:model>
"""


def write_crafted_model(tmp_path, doctype):
    secret = tmp_path / "secret.txt"
    secret.write_text("SECRET-FROM-DISK", encoding="utf-8")
    (tmp_path / "evil.dtd").write_text(
        "<!ENTITY % all \"<!ENTITY leak '%file;'>\">\n%all;\n", encoding="utf-8")
    path = tmp_path / "evil.archimate"
    path.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                    + doctype.format(dir=tmp_path.as_uri()) + MODEL_TAIL,
                    encoding="utf-8")
    return path


def assert_nothing_leaks(path):
    try:
        model = ArchiModel(path)
    except etree.XMLSyntaxError:
        return  # refusing the file is fine too
    assert "SECRET" not in (model.root.get("name") or "")


@pytest.mark.parametrize("doctype", [
    # external parameter entity pulling a DTD that defines the entity
    """<!DOCTYPE model [
  <!ENTITY % file SYSTEM "{dir}/secret.txt">
  <!ENTITY % dtd SYSTEM "{dir}/evil.dtd">
  %dtd;
]>""",
    # plain external general entity
    """<!DOCTYPE model [
  <!ENTITY leak SYSTEM "{dir}/secret.txt">
]>""",
])
def test_crafted_model_cannot_read_local_files(tmp_path, doctype):
    assert_nothing_leaks(write_crafted_model(tmp_path, doctype))
