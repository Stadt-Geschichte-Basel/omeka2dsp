"""Check a payload against the ontology before an upload.

The ontology is the graph from GET /v2/ontologies/allentities/{ontology-iri}.
"""

from collections.abc import Mapping
from typing import Any

from omeka2dsp.fields import FIELDS, Kind
from omeka2dsp.values import OmekaRecord

# Omeka term -> DSP list property. A source value without a payload value
# means that the list lookup failed.
LIST_PROPERTIES = {
    field.term: field.prop for field in FIELDS if field.kind is Kind.LIST and field.term
}


def index_ontology(
    ontology: Mapping[str, Any],
) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Return (class -> allowed properties, property -> knora-api:objectType)."""
    classes: dict[str, set[str]] = {}
    object_types: dict[str, str] = {}
    for entity in ontology.get("@graph", []):
        kind, iri = entity.get("@type"), entity.get("@id")
        if kind == "owl:Class":
            restrictions = entity.get("rdfs:subClassOf") or []
            if isinstance(restrictions, dict):
                restrictions = [restrictions]
            classes[iri] = {
                r["owl:onProperty"]["@id"]
                for r in restrictions
                if isinstance(r, dict) and "owl:onProperty" in r
            }
        elif kind == "owl:ObjectProperty":
            object_type = (entity.get("knora-api:objectType") or {}).get("@id")
            if object_type:
                object_types[iri] = object_type
    return classes, object_types


def preflight(
    payload: Mapping[str, Any],
    record: OmekaRecord,
    ontology: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    """The problems of a payload. An empty list means that it looks valid."""
    classes, object_types = index_ontology(ontology)
    resource_class = payload.get("@type", "")
    if resource_class not in classes:
        return [f"unknown class {resource_class}"]
    allowed = classes[resource_class]
    problems = []
    for prop, entry in payload.items():
        if not prop.startswith(prefix):
            continue
        if prop not in allowed:
            problems.append(f"{prop} is not allowed on {resource_class}")
            continue
        expected = object_types.get(prop)
        if not expected:
            problems.append(f"{prop}: no knora-api:objectType in the ontology")
            continue
        for value in entry if isinstance(entry, list) else [entry]:
            if not value.get("@type"):
                problems.append(f"{prop}: value has no @type")
            elif value.get("@type") != expected:
                problems.append(f"{prop}: {value.get('@type')} is not {expected}")
    for term, dsp_prop in LIST_PROPERTIES.items():
        prop = f"{prefix}{dsp_prop}"
        labels = [v.value or v.label for v in record.get(term) if v.value or v.label]
        if prop in allowed and labels and prop not in payload:
            problems.append(f"{prop}: no list node for {labels}")
    return problems
