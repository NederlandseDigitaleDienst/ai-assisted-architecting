import pytest

from archi_tool.model import ModelError
from archi_tool.validate import validate
from archi_tool.views import add_view


def test_grid_view(model):
    diagram = add_view(model, "Grid", layout="grid")
    objects = diagram.findall("child")
    assert len(objects) == 3
    connections = list(diagram.iter("sourceConnection"))
    assert len(connections) == 2
    for obj in objects:
        bounds = obj.find("bounds")
        assert bounds is not None
        assert obj[0] is bounds
    errors, _ = validate(model)
    assert errors == []


def test_cluster_view_places_head_above_children(model):
    diagram = add_view(model, "Cluster", layout="cluster",
                       element_types={"Capability"},
                       relation_types={"Aggregation"})
    objects = {obj.get("archimateElement"): obj
               for obj in diagram.findall("child")}
    assert set(objects) == {"id-el-alfa", "id-el-beta"}
    alfa_y = int(objects["id-el-alfa"].find("bounds").get("y"))
    beta_y = int(objects["id-el-beta"].find("bounds").get("y"))
    assert alfa_y < beta_y
    connections = list(diagram.iter("sourceConnection"))
    assert len(connections) == 1
    assert connections[0].get("archimateRelationship") == "id-rel-agg"
    target = objects["id-el-beta"]
    assert target.get("targetConnections") == connections[0].get("id")
    errors, _ = validate(model)
    assert errors == []


def test_property_filter_selection(model):
    diagram = add_view(model, "Alleen gebieden", layout="grid",
                       prop="Capability-niveau=gebied")
    objects = diagram.findall("child")
    assert [o.get("archimateElement") for o in objects] == ["id-el-alfa"]


def test_empty_selection_raises(model):
    with pytest.raises(ModelError):
        add_view(model, "Leeg", element_types={"Node"})


def test_explicit_elements_without_filters_select_only_those(model):
    diagram = add_view(model, "Expliciet", layout="grid",
                       extra_elements=[model.resolve("id-el-alfa")])
    objects = diagram.findall("child")
    assert [o.get("archimateElement") for o in objects] == ["id-el-alfa"]


def test_explicit_elements_extend_filtered_selection(model):
    diagram = add_view(model, "Filter plus expliciet", layout="grid",
                       element_types={"Goal"},
                       extra_elements=[model.resolve("id-el-alfa"),
                                       model.resolve("id-el-gamma")])
    objects = diagram.findall("child")
    ids = [o.get("archimateElement") for o in objects]
    assert set(ids) == {"id-el-alfa", "id-el-gamma"}
    assert len(ids) == 2
    errors, _ = validate(model)
    assert errors == []
