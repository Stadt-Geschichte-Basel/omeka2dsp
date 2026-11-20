"""Check a DSP payload against the project ontology before an upload.

All functions are pure: the ontology is the JSON-LD graph from
GET /v2/ontologies/allentities/{ontology-iri}.
"""

# Omeka property -> DSP list property. When the Omeka record has a value but
# the payload has no list value, the list lookup did not resolve.
LIST_PROPERTIES = {
    "dcterms:temporal": "hasTemporalList",
    "dcterms:language": "hasLanguageList",
    "dcterms:license": "hasLicenseList",
    "dcterms:format": "hasFormatList",
    "dcterms:type": "hasTypeList",
}


def index_ontology(ontology: dict) -> tuple[dict[str, set[str]], dict[str, str]]:
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
            object_types[iri] = (entity.get("knora-api:objectType") or {}).get("@id")
    return classes, object_types


def _values(entry) -> list[dict]:
    return entry if isinstance(entry, list) else [entry]


def preflight(payload: dict, item: dict, ontology: dict, prefix: str) -> list[str]:
    """Return a list of problems. An empty list means the payload looks valid."""
    classes, object_types = index_ontology(ontology)
    resource_class = payload.get("@type")
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
        for value in _values(entry):
            if value.get("@type") != expected:
                problems.append(f"{prop}: {value.get('@type')} is not {expected}")
    for omeka_prop, dsp_prop in LIST_PROPERTIES.items():
        prop = f"{prefix}{dsp_prop}"
        has_source_value = any(
            value.get("@value") or value.get("o:label")
            for value in item.get(omeka_prop, [])
        )
        if prop in allowed and has_source_value and prop not in payload:
            labels = [
                value.get("@value") or value.get("o:label")
                for value in item[omeka_prop]
            ]
            problems.append(f"{prop}: no list node for {labels}")
    return problems
