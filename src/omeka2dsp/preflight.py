"""Check a payload against the ontology before an upload.

The ontology is the graph from GET /v2/ontologies/allentities/{ontology-iri}.
"""

from collections.abc import Mapping
from typing import Any

from omeka2dsp.fields import FIELDS, Kind, fields_for
from omeka2dsp.media import FILE_EXTENSIONS, FILE_VALUES, ingest_filename
from omeka2dsp.values import OmekaRecord, wanted

# Omeka term -> DSP list property. A source value without a payload value
# means that the list lookup failed.
LIST_PROPERTIES = {
    field.term: field.prop for field in FIELDS if field.kind is Kind.LIST and field.term
}


def _number(value: Any) -> int | None:
    """An owl cardinality: an int, or a dict with @value."""
    if isinstance(value, Mapping):
        value = value.get("@value")
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def index_ontology(
    ontology: Mapping[str, Any],
) -> tuple[dict[str, set[str]], dict[str, str], dict[tuple[str, str], int]]:
    """Return (class -> allowed properties, property -> knora-api:objectType,
    (class, property) -> maximum number of values)."""
    classes: dict[str, set[str]] = {}
    object_types: dict[str, str] = {}
    limits: dict[tuple[str, str], int] = {}
    for entity in ontology.get("@graph", []):
        kind, iri = entity.get("@type"), entity.get("@id")
        if kind == "owl:Class":
            restrictions = entity.get("rdfs:subClassOf") or []
            if isinstance(restrictions, dict):
                restrictions = [restrictions]
            restrictions = [
                r for r in restrictions if isinstance(r, dict) and "owl:onProperty" in r
            ]
            classes[iri] = {r["owl:onProperty"]["@id"] for r in restrictions}
            for r in restrictions:
                limit = _number(r.get("owl:maxCardinality", r.get("owl:cardinality")))
                if limit is not None:
                    limits[(iri, r["owl:onProperty"]["@id"])] = limit
        elif kind == "owl:ObjectProperty":
            object_type = (entity.get("knora-api:objectType") or {}).get("@id")
            if object_type:
                object_types[iri] = object_type
    return classes, object_types, limits


def _empty(value: Mapping[str, Any]) -> bool:
    return not value.get("knora-api:valueAsString") and not value.get(
        "knora-api:textValueAsXml"
    )


def preflight(
    payload: Mapping[str, Any],
    record: OmekaRecord,
    ontology: Mapping[str, Any],
    prefix: str,
) -> list[str]:
    """The problems of a payload. An empty list means that it looks valid."""
    classes, object_types, limits = index_ontology(ontology)
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
        entries = entry if isinstance(entry, list) else [entry]
        limit = limits.get((resource_class, prop))
        if limit is not None and len(entries) > limit:
            problems.append(f"{prop}: {len(entries)} values, at most {limit} allowed")
        for value in entries:
            if value.get("@type") == "knora-api:TextValue" and _empty(value):
                problems.append(f"{prop}: empty value")
            if not value.get("@type"):
                problems.append(f"{prop}: value has no @type")
            elif value.get("@type") != expected:
                problems.append(f"{prop}: {value.get('@type')} is not {expected}")
    for term, dsp_prop in LIST_PROPERTIES.items():
        prop = f"{prefix}{dsp_prop}"
        labels = [v.value or v.label for v in record.get(term) if v.value or v.label]
        if prop in allowed and labels and prop not in payload:
            problems.append(f"{prop}: no list node for {labels}")
    local = resource_class.removeprefix(prefix)
    for field in fields_for(local):
        if field.kind is Kind.RICH_TEXT:
            for bad in wanted(field, record, []).unresolved:
                problems.append(f"{prefix}{field.prop}: invalid URI '{bad}'")
    name = ingest_filename(record.original_url or "")
    if local in FILE_VALUES and name:
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if extension not in FILE_EXTENSIONS[local]:
            problems.append(f"file '{name}' does not fit class {local}")
    return problems
