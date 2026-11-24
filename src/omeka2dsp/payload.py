"""JSON-LD bodies for create, change, erase, and file permissions."""

from collections.abc import Mapping, Sequence
from typing import Any

from omeka2dsp.fields import Kind, Project, fields_for
from omeka2dsp.lists import DspList
from omeka2dsp.media import FILE_VALUES, PRIVATE_FILE_PERMISSIONS
from omeka2dsp.plan import Change
from omeka2dsp.values import TEXT_ENTRY_KEYS, Entry, OmekaRecord, first_literal, wanted

# A DSP request body. The keys depend on the ontology prefix.
JsonLd = dict[str, Any]

CONTENT_KEYS = {
    "knora-api:TextValue": "knora-api:valueAsString",
    "knora-api:ListValue": "knora-api:listValueAsListNode",
    "knora-api:LinkValue": "knora-api:linkValueHasTargetIri",
}


def context(project: Project) -> dict[str, str]:
    return {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "knora-api": "http://api.knora.org/ontology/knora-api/v2#",
        project.ontology_name: f"{project.ontology_iri}#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
    }


def entry(value_type: str, value: str | Entry) -> Entry:
    """A new DSP value. A text entry keeps only the keys that DSP accepts."""
    if isinstance(value, Mapping):
        return {k: v for k, v in value.items() if k in TEXT_ENTRY_KEYS}
    key = CONTENT_KEYS[value_type]
    content = value if value_type == "knora-api:TextValue" else {"@id": value}
    return {"@type": value_type, key: content}


def create(
    project: Project,
    resource_class: str,
    record: OmekaRecord,
    lists: Sequence[DspList],
    parent_iri: str | None = None,
    filename: str | None = None,
    restricted: bool = False,
) -> JsonLd:
    """The body of POST /v2/resources for an Omeka record.

    A restricted file gets its permissions in the body, so it is never public.
    """
    body: JsonLd = {
        "@context": context(project),
        "@type": project.name(resource_class),
        "knora-api:attachedToProject": {"@id": project.iri},
        "rdfs:label": first_literal(record.get("dcterms:title")),
    }
    for field in fields_for(resource_class):
        if field.kind is Kind.LINK:
            if parent_iri:
                link = entry(field.value_type, parent_iri)
                body[project.name(f"{field.prop}Value")] = link
            continue
        values = wanted(field, record, lists).values
        entries = [entry(field.value_type, value) for value in values]
        if field.kind is Kind.RICH_TEXT or field.many:
            if entries:
                body[project.name(field.prop)] = entries
        elif entries or field.required:
            body[project.name(field.prop)] = (
                entries[0] if entries else entry(field.value_type, "")
            )
    if filename and resource_class in FILE_VALUES:
        prop, value_type = FILE_VALUES[resource_class]
        body[prop] = {"@type": value_type, "knora-api:fileValueHasFilename": filename}
        if restricted:
            body[prop]["knora-api:hasPermissions"] = PRIVATE_FILE_PERMISSIONS
    return body


def change(project: Project, resource: Mapping[str, Any], value: Change) -> JsonLd:
    """The body of a value create, update, or delete request."""
    if value.action == "delete":
        dsp_value: Entry = {"@id": value.value_id, "@type": value.value_type}
    else:
        dsp_value = entry(value.value_type, value.value or "")
        if value.action == "update" and value.value_id:
            dsp_value["@id"] = value.value_id
    return {
        "@context": context(project),
        "@id": resource["@id"],
        "@type": resource["@type"],
        project.name(value.field): dsp_value,
    }


def erase(project: Project, resource: Mapping[str, Any]) -> JsonLd:
    body: JsonLd = {
        "@context": context(project),
        "@id": resource["@id"],
        "@type": resource["@type"],
    }
    if "knora-api:lastModificationDate" in resource:
        body["knora-api:lastModificationDate"] = resource[
            "knora-api:lastModificationDate"
        ]
    return body


def file_permissions(
    project: Project,
    resource: Mapping[str, Any],
    prop: str,
    value: Entry,
    permissions: str,
) -> JsonLd:
    """The body that sets the permissions of a file value."""
    return {
        "@context": context(project),
        "@id": resource["@id"],
        "@type": resource["@type"],
        prop: {
            "@id": value["@id"],
            "@type": value["@type"],
            "knora-api:hasPermissions": permissions,
        },
    }


CARDINALITIES = {
    "1": ("owl:cardinality", 1),
    "0-1": ("owl:maxCardinality", 1),
    "0-n": ("owl:minCardinality", 0),
    "1-n": ("owl:minCardinality", 1),
}


def text_class(
    model: Mapping[str, Any], project: Project, last_modified: Any
) -> JsonLd:
    """The body of POST /v2/ontologies/classes for the Text class.

    The class comes from data/data_model_dasch.json. SGB:Text
    (knora-api:TextRepresentation) stores CSV and JSON files unchanged.
    """
    ontology = model["project"]["ontologies"][0]
    text = next(r for r in ontology["resources"] if r["name"] == "Text")
    restrictions = [
        {
            "@type": "owl:Restriction",
            CARDINALITIES[c["cardinality"]][0]: CARDINALITIES[c["cardinality"]][1],
            "owl:onProperty": {"@id": project.name(c["propname"].lstrip(":"))},
            "salsah-gui:guiOrder": c["gui_order"],
        }
        for c in text["cardinalities"]
    ]

    def lang(values: Mapping[str, str]) -> list[dict[str, str]]:
        return [{"@language": k, "@value": v} for k, v in values.items()]

    return {
        "@id": project.ontology_iri,
        "@type": "owl:Ontology",
        "knora-api:lastModificationDate": last_modified,
        "@graph": [
            {
                "@id": project.name("Text"),
                "@type": "owl:Class",
                "rdfs:label": lang(text["labels"]),
                "rdfs:comment": lang(text["comments"]),
                "rdfs:subClassOf": [{"@id": f"knora-api:{text['super']}"}]
                + restrictions,
            }
        ],
        "@context": {
            "knora-api": "http://api.knora.org/ontology/knora-api/v2#",
            "salsah-gui": "http://api.knora.org/ontology/salsah-gui/v2#",
            "owl": "http://www.w3.org/2002/07/owl#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            project.ontology_name: f"{project.ontology_iri}#",
        },
    }
