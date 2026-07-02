"""Load, query, mutate and save native Archi .archimate models.

The .archimate format is Eclipse EMF XML. Only the root element lives in the
archimate namespace; all other elements (folder, element, property, child,
bounds, sourceConnection, documentation) are unqualified. Concepts carry an
xsi:type attribute such as "archimate:Capability"; relationship types end in
"Relationship" (American spelling: RealizationRelationship). Folders per
ArchiMate layer are fixed by Archi and identified by their type attribute.
"""
from __future__ import annotations

import uuid

from lxml import etree

ARCHIMATE_NS = "http://www.archimatetool.com/archimate"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XSI_TYPE = "{%s}type" % XSI_NS
MODEL_TAG = "{%s}model" % ARCHIMATE_NS

DIAGRAM_TYPE = "ArchimateDiagramModel"

ELEMENT_LAYERS = {
    "strategy": {"Resource", "Capability", "CourseOfAction", "ValueStream"},
    "business": {
        "BusinessActor", "BusinessRole", "BusinessCollaboration",
        "BusinessInterface", "BusinessProcess", "BusinessFunction",
        "BusinessInteraction", "BusinessEvent", "BusinessService",
        "BusinessObject", "Contract", "Representation", "Product",
    },
    "application": {
        "ApplicationComponent", "ApplicationCollaboration",
        "ApplicationInterface", "ApplicationFunction", "ApplicationInteraction",
        "ApplicationProcess", "ApplicationEvent", "ApplicationService",
        "DataObject",
    },
    "technology": {
        "Node", "Device", "SystemSoftware", "TechnologyCollaboration",
        "TechnologyInterface", "Path", "CommunicationNetwork",
        "TechnologyFunction", "TechnologyProcess", "TechnologyInteraction",
        "TechnologyEvent", "TechnologyService", "Artifact", "Material",
        "Equipment", "Facility", "DistributionNetwork",
    },
    "motivation": {
        "Stakeholder", "Driver", "Assessment", "Goal", "Outcome",
        "Principle", "Requirement", "Constraint", "Meaning", "Value",
    },
    "implementation_migration": {
        "WorkPackage", "Deliverable", "ImplementationEvent", "Plateau", "Gap",
    },
    "other": {"Location", "Grouping", "Junction"},
}
FOLDER_BY_ELEMENT_TYPE = {
    t: layer for layer, types in ELEMENT_LAYERS.items() for t in types
}

RELATIONSHIP_TYPES = {
    "Composition", "Aggregation", "Assignment", "Realization", "Serving",
    "Access", "Influence", "Triggering", "Flow", "Specialization",
    "Association",
}


class ModelError(Exception):
    """User-facing error; message is Dutch."""


def new_id() -> str:
    return "id-" + str(uuid.uuid4())


def xsi_type(node) -> str:
    """Return the bare xsi:type ("archimate:Capability" -> "Capability")."""
    value = node.get(XSI_TYPE) or ""
    return value.split(":", 1)[-1]


def is_relationship(node) -> bool:
    return node.tag == "element" and xsi_type(node).endswith("Relationship")


def is_diagram(node) -> bool:
    return node.tag == "element" and xsi_type(node) == DIAGRAM_TYPE


def is_element(node) -> bool:
    return (node.tag == "element"
            and not is_relationship(node) and not is_diagram(node))


class ArchiModel:
    def __init__(self, path):
        self.path = str(path)
        self.tree = etree.parse(self.path)
        self.root = self.tree.getroot()
        if self.root.tag != MODEL_TAG:
            raise ModelError(
                f"Geen .archimate-model: rootelement is {self.root.tag}")

    # --- queries ---------------------------------------------------------

    @property
    def name(self) -> str:
        return self.root.get("name") or ""

    def id_index(self) -> dict:
        return {n.get("id"): n for n in self.root.iter() if n.get("id")}

    def folder(self, folder_type: str):
        for f in self.root.iter("folder"):
            if f.get("type") == folder_type:
                return f
        raise ModelError(f"Folder met type '{folder_type}' niet gevonden")

    def elements(self) -> list:
        return [n for n in self.root.iter("element") if is_element(n)]

    def relationships(self) -> list:
        return [n for n in self.root.iter("element") if is_relationship(n)]

    def diagrams(self) -> list:
        return [n for n in self.root.iter("element") if is_diagram(n)]

    def properties(self, node) -> dict:
        return {p.get("key"): p.get("value") for p in node.findall("property")}

    def documentation(self, node) -> str:
        doc = node.find("documentation")
        return (doc.text or "") if doc is not None else ""

    def resolve(self, ref: str):
        """Resolve a concept by id, or by exact name if that is unique."""
        index = self.id_index()
        if ref in index:
            return index[ref]
        matches = [n for n in self.root.iter("element") if n.get("name") == ref]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ModelError(f"Niet gevonden: '{ref}' (geen id en geen naam)")
        ids = ", ".join(m.get("id") for m in matches)
        raise ModelError(
            f"Naam '{ref}' is niet uniek ({len(matches)}x); "
            f"gebruik het id. Kandidaten: {ids}")

    def relations_of(self, concept_id: str) -> list:
        return [r for r in self.relationships()
                if concept_id in (r.get("source"), r.get("target"))]

    # --- mutations ---------------------------------------------------------

    def set_model_name(self, name: str):
        self.root.set("name", name)

    def add_element(self, el_type: str, name: str, folder_type: str = None,
                    properties: dict = None, documentation: str = None):
        if el_type not in FOLDER_BY_ELEMENT_TYPE:
            known = ", ".join(sorted(FOLDER_BY_ELEMENT_TYPE))
            raise ModelError(
                f"Onbekend elementtype '{el_type}'. Toegestaan: {known}")
        target = self.folder(folder_type or FOLDER_BY_ELEMENT_TYPE[el_type])
        el = etree.SubElement(target, "element", {
            XSI_TYPE: f"archimate:{el_type}", "name": name, "id": new_id()})
        if documentation:
            doc = etree.SubElement(el, "documentation")
            doc.text = documentation
        for key, value in (properties or {}).items():
            etree.SubElement(el, "property", {"key": key, "value": value})
        return el

    def add_relation(self, rel_type: str, source: str, target: str,
                     name: str = None):
        rel_type = rel_type.removesuffix("Relationship")
        if rel_type not in RELATIONSHIP_TYPES:
            known = ", ".join(sorted(RELATIONSHIP_TYPES))
            raise ModelError(
                f"Onbekend relatietype '{rel_type}'. Toegestaan: {known}")
        src = self.resolve(source)
        tgt = self.resolve(target)
        # resolve() also matches views and relations by name; only elements
        # are valid endpoints (ArchiMate allows a relation endpoint solely
        # for Association)
        for role, node in (("source", src), ("target", tgt)):
            if is_diagram(node):
                raise ModelError(
                    f"{role} '{node.get('name')}' is een view; relaties "
                    "kunnen geen views verbinden")
            if is_relationship(node) and rel_type != "Association":
                raise ModelError(
                    f"{role} '{node.get('name')}' is zelf een relatie; "
                    "alleen een AssociationRelationship mag een relatie "
                    "als eindpunt hebben")
        attrs = {XSI_TYPE: f"archimate:{rel_type}Relationship",
                 "id": new_id(),
                 "source": src.get("id"), "target": tgt.get("id")}
        if name:
            attrs["name"] = name
        return etree.SubElement(self.folder("relations"), "element", attrs)

    def set_property(self, ref: str, key: str, value: str):
        el = self.resolve(ref)
        for p in el.findall("property"):
            if p.get("key") == key:
                p.set("value", value)
                return
        etree.SubElement(el, "property", {"key": key, "value": value})

    def rename(self, ref: str, name: str):
        self.resolve(ref).set("name", name)

    def set_documentation(self, ref: str, text: str):
        el = self.resolve(ref)
        doc = el.find("documentation")
        if doc is None:
            doc = etree.Element("documentation")
            el.insert(0, doc)
        doc.text = text

    def remove(self, ref: str, cascade: bool = False):
        el = self.resolve(ref)
        el_id = el.get("id")
        if is_relationship(el):
            connections = [c for c in self.root.iter("sourceConnection")
                           if c.get("archimateRelationship") == el_id]
            if connections and not cascade:
                raise ModelError(
                    f"Relatie {el_id} wordt gebruikt in {len(connections)} "
                    "view-verbinding(en); gebruik --cascade om die mee te "
                    "verwijderen")
            for c in connections:
                self._remove_connection(c)
        else:
            relations = self.relations_of(el_id)
            diagram_objects = [d for d in self.root.iter("child")
                               if d.get("archimateElement") == el_id]
            if (relations or diagram_objects) and not cascade:
                raise ModelError(
                    f"Element {el_id} heeft {len(relations)} relatie(s) en "
                    f"{len(diagram_objects)} view-object(en); gebruik "
                    "--cascade om die mee te verwijderen")
            for r in relations:
                self.remove(r.get("id"), cascade=True)
            for d in diagram_objects:
                self._remove_diagram_object(d)
        el.getparent().remove(el)

    def _remove_connection(self, conn):
        conn_id = conn.get("id")
        for node in self.root.iter("child"):
            listed = (node.get("targetConnections") or "").split()
            if conn_id in listed:
                remaining = [i for i in listed if i != conn_id]
                if remaining:
                    node.set("targetConnections", " ".join(remaining))
                else:
                    del node.attrib["targetConnections"]
        conn.getparent().remove(conn)

    def _remove_diagram_object(self, obj):
        for sub in list(obj.findall("child")):
            self._remove_diagram_object(sub)
        for conn in list(obj.findall("sourceConnection")):
            self._remove_connection(conn)
        obj_id = obj.get("id")
        incoming = [c for c in self.root.iter("sourceConnection")
                    if c.get("target") == obj_id]
        for conn in incoming:
            self._remove_connection(conn)
        obj.getparent().remove(obj)

    # --- persistence -------------------------------------------------------

    def save(self, path=None):
        etree.indent(self.root, space="  ")
        body = etree.tostring(self.root, encoding="unicode")
        # newline="\n" keeps LF on every platform (no CRLF churn on Windows)
        with open(path or self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write(body)
            f.write("\n")
