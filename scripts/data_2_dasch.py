import argparse
from argparse import Namespace
import logging
import os
from pathlib import Path
import random
import tempfile
from typing import Any, Dict, List, cast
import urllib
import zipfile

import requests

from process_data_from_omeka import (
    get_items_from_collection,
    get_media,
    extract_combined_values,
    extract_property
)

# TODO: - improve error handling
#       - improve logging
#       - refactoring

# Configuration
ITEM_SET_ID = os.getenv("ITEM_SET_ID", '10780')

PROJECT_SHORT_CODE = os.getenv("PROJECT_SHORT_CODE")
API_HOST = os.getenv("API_HOST")
INGEST_HOST = os.getenv("INGEST_HOST")
DSP_USER = os.getenv("DSP_USER")
DSP_PWD = os.getenv("DSP_PWD")
ONTOLOGY_NAME = os.getenv("ONTOLOGY_NAME", "SGB")
PREFIX = f"{ONTOLOGY_NAME}:"

NUMBER_RANDOM_OBJECTS = 2
TEST_DATA = {'abb13025', 'abb14375', 'abb41033', 'abb11536', 'abb28998'}

ICONCLASS_SUBJECT_ENTRY = {
    "type": "literal",
    "property_id": 3,
    "property_label": "Subject",
    "is_public": True,
    "@value": "11A|Deity, God (in general) in Christian religion",
    "@language": "en",
}

ONTOLOGY_CONTEXT = (
    f"{API_HOST}/ontology/{PROJECT_SHORT_CODE}/{ONTOLOGY_NAME}/v2#"
    if all([API_HOST, PROJECT_SHORT_CODE, ONTOLOGY_NAME])
    else ""
)
METADATA_RESOURCE_TYPE = f"{PREFIX}Parent"
MEDIA_RESOURCE_TYPES = {
    f"{PREFIX}Document",
    f"{PREFIX}Image",
    f"{PREFIX}ResourceWithoutMedia",
}

LIST_LABELS = {
    "subject": {"Iconclass subject heading", "Iconclass Sachbegriff"},
    "temporal": {"Stadt.Geschichte.Basel Era", "Stadt.Geschichte.Basel Epoche"},
    "type": {"DCMI Type", "DCMI Type Vocabulary"},
    "format": {"Internet Media Type"},
    "language": {"ISO 639-1"},
    "license": {"Licenses", "License", "Rights statement"},
}


def build_context() -> dict:
    return {
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "knora-api": "http://api.knora.org/ontology/knora-api/v2#",
        ONTOLOGY_NAME: ONTOLOGY_CONTEXT,
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    }


def apply_iconclass_subject(records: List[Dict[str, Any]]) -> None:
    """Force test/sample records to use a known Iconclass subject label."""

    for record in records:
        record["dcterms:subject"] = [ICONCLASS_SUBJECT_ENTRY.copy()]

# Set up logging
file_handler = logging.FileHandler("data_2_dasch.log", mode='w')
file_handler.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[stream_handler, file_handler]
)


def parse_arguments() -> Namespace:
    """Parses the commandline for the path to the config-file and for the path to the output directory.

    Returns:
        Namespace: Argparse-Namespace object
    """

    parser = argparse.ArgumentParser(description="--mode")
    parser.add_argument("-m", "--mode", type=str, choices=['all_data', 'sample_data', 'test_data'], default='all_data',
                        help=f"which data should be processed? possible options: 'all_data' (all data), 'sample_data' ({NUMBER_RANDOM_OBJECTS} random metadata objects),'test_data' (10 selected test metadata objects)")
    args = parser.parse_args()

    return args


def login(email: str, password: str) -> str:
    endpoint = f"{API_HOST}/v2/authentication"
    response = requests.post(endpoint, json={"email": email, "password": password}, timeout=10)
    logging.info("Login successful")
    return cast(str, response.json()["token"])

def get_project():
    endpoint = f"{API_HOST}/admin/projects/shortcode/{PROJECT_SHORT_CODE}"
    response = requests.get(endpoint)
    project_data = response.json()
    try:
        project_id = cast(str, project_data["project"]["id"])
        ontology_iris = project_data["project"].get("ontologies", [])
    except KeyError as error:
        logging.error("Failed to parse project response: %s", error)
        raise

    if ontology_iris:
        ontology_context = ontology_iris[0]
        if not ontology_context.endswith("#"):
            ontology_context = f"{ontology_context}#"
        # Update the global context so subsequent payloads use the canonical IRI base.
        global ONTOLOGY_CONTEXT
        ONTOLOGY_CONTEXT = ontology_context

    if response.status_code == 200:
        logging.info(f"project Iri: {project_id}")
    else:
        logging.error(f"Failed to retrieve project. Status code: {response.status_code}")
        logging.error(f"Response: {response.text}")
    return project_id

# Get lists
def get_lists(project_iri):
    url_lists = f"{API_HOST}/admin/lists/?projectIri={project_iri}"
    response_lists = requests.get(url_lists)
    all_lists = []
    if response_lists.status_code == 200:
        for list in response_lists.json()["lists"]:
            list_id = list["id"]
            # URL encode the list IRI
            encoded_list_id = urllib.parse.quote(list_id, safe='')
            # Construct the API endpoint for this specific list ID
            url = f"{API_HOST}/v2/lists/{encoded_list_id}"
            response = requests.get(url)
            if response.status_code == 200:
                all_lists.append(response.json())
            else:
                logging.error(f"Failed to retrieve complete list for {list_id}. Status code: {response.status_code}")
                logging.error(f"Response:{response.text}")
        logging.info("Got Lists from project")
    else:
        logging.error(f"Failed to retrieve lists. Status code: {response_lists.status_code}")
        logging.error(f"Response: {response_lists.text}")
    return all_lists


def get_full_resource(token: str, resource_iri: str) -> dict:
    endpoint = f"{API_HOST}/v2/resources/{resource_iri}"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get(endpoint, headers=headers)
    return response.json()

def extract_dasch_propvalue(item, prop):

    full_property = f"{PREFIX}{prop}"
    if full_property in item:
        prop_value = item[full_property]
        return extract_value_from_entry(prop_value)
    return ""

def extract_dasch_propvalue_multiple(item, prop):
    full_property = f"{PREFIX}{prop}"
    values = []
    # Get the value(s) of the property, either as a list or a single entry
    prop_values = item.get(full_property)
    # If the property exists and is either a list or a dict (single value case)
    if prop_values:
        # If the property is a list, iterate over the entries
        if isinstance(prop_values, list):
            for entry in prop_values:
                value = extract_value_from_entry(entry)
                if value:
                    values.append(value)
        # If it's a single dictionary (not a list), extract the value directly
        elif isinstance(prop_values, dict):
            value = extract_value_from_entry(prop_values)
            if value:
                values.append(value)
    return values

def extract_value_from_entry(entry):
    entry_type = entry.get('@type')
    value = None
    
    if entry_type == "knora-api:TextValue":
        value = entry.get("knora-api:valueAsString")
    elif entry_type == "knora-api:ListValue":
        value = entry.get("knora-api:listValueAsListNode", {}).get("@id")
    elif entry_type == "knora-api:LinkValue":
        value = entry.get("knora-api:linkValueHasTargetIri", {}).get("@id")
    elif entry_type == "knora-api:UriValue":
        value = entry.get("knora-api:uriValueAsUri", {}).get("@value")
    return value

def get_resource_by_id(token: str, object_class: str, identifier: str) -> dict:
    endpoint = f"{API_HOST}/v2/searchextended"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/sparql-query; charset=utf-8"
    }
    query = f"""
        PREFIX knora-api: <http://api.knora.org/ontology/knora-api/v2#>
        PREFIX {PREFIX} <{ONTOLOGY_CONTEXT}>
        CONSTRUCT {{
            ?metadata knora-api:isMainResource true .
            ?metadata {PREFIX}hasIdentifier ?identifierValue .
            ?metadata {PREFIX}hasTitle ?title .
        }} WHERE {{
            ?metadata a {object_class} .
            ?metadata {PREFIX}hasIdentifier ?identifierValue .
            ?identifierValue knora-api:valueAsString ?identifier .
            ?metadata {PREFIX}hasTitle ?title .
            FILTER(?identifier = "{identifier}")
        }}
        """
    response = requests.post(endpoint, data=query.encode('utf-8'), headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error: {response.status_code}")
        logging.error(response.text)
        return {}


def update_value(token, item, value, field, field_type, type_of_change):

    context_data = build_context()
    complete_field_type = f"knora-api:{field_type}"
    payload = {
        "@context": context_data,
        "@id": item["@id"],
        "@type": item["@type"],
        f"{PREFIX}{field}": {
            "@type": complete_field_type
        }
    }

    if type_of_change in ["delete", "update"]:
        existing_value = item.get(f"{PREFIX}{field}")
        if isinstance(existing_value, dict):
            value_id = existing_value.get("@id")
        elif isinstance(existing_value, list):
            value_id = None
            for obj in existing_value:
                if field_type == "TextValue" and obj.get("knora-api:valueAsString") == value:
                    value_id = obj["@id"]
                    break
                elif field_type == "ListValue" and obj.get("knora-api:listValueAsListNode", {}).get("@id") == value:
                    value_id = obj["@id"]
                    break
                elif field_type == "UriValue" and obj.get("knora-api:uriValueAsUri", {}).get("@value") == value:
                    value_id = obj["@id"]
                    break
        else:
            value_id = None
        if value_id:
            payload[f"{PREFIX}{field}"]["@id"] = value_id

    if type_of_change in ["create", "update"]:
        if field_type == "TextValue":
            payload[f"{PREFIX}{field}"]["knora-api:valueAsString"] = value
        if field_type == "ListValue":
            payload[f"{PREFIX}{field}"]["knora-api:listValueAsListNode"] = {
                "@id": value
            }
        if field_type == "UriValue":
            payload[f"{PREFIX}{field}"]["knora-api:uriValueAsUri"] = {
                "@value": value,
                "@type": "http://www.w3.org/2001/XMLSchema#anyURI"
            }
        if field_type == "linkvalue":
            payload[f"{PREFIX}{field}"]["knora-api:linkValueHasTargetIri"] = {
                "@id": value 
            }

    if type_of_change == "delete":
        endpoint = f"{API_HOST}/v2/values/delete"
    else:
        endpoint = f"{API_HOST}/v2/values"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Asset-Ingested": "true",
    }

    if type_of_change == "update":
        response = requests.put(endpoint, json=payload, headers=headers, timeout=10)
    else:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=10)

    identifier_value = extract_dasch_propvalue(item, "hasIdentifier") or "unknown identifier"
    if response.status_code == 200:
        logging.info(f"{identifier_value}: {type_of_change}d {field} '{value}'")
    else:
        logging.error(
            f"{identifier_value}: update of {field} failed: {response.status_code}: {response.text}"
        )
        # logging.error(payload)

def arrays_equal(array1, array2):
    if len(array1) != len(array2):
        return False
    return set(array1) == set(array2)

def sync_value(prop, prop_type, dasch_value, omeka_value):
    dasch_value = dasch_value or ""
    omeka_value = omeka_value or ""
    if dasch_value == "" and omeka_value != "":
        return {"field": prop, "prop_type": prop_type, "type": "create", "value": omeka_value}
    elif dasch_value != "" and omeka_value == "":
        return {"field": prop, "prop_type": prop_type, "type": "delete", "value": omeka_value}
    elif dasch_value != "" and omeka_value != "" and dasch_value != omeka_value:
        return {"field": prop, "prop_type": prop_type, "type": "update", "value": omeka_value}


def sync_array_value(prop, prop_type, dasch_array, omeka_array):
    dasch_set = {value for value in dasch_array if value}
    omeka_set = {value for value in omeka_array if value}

    to_create = omeka_set - dasch_set  
    to_delete = dasch_set - omeka_set  

    changes = [{"field": prop, "prop_type": prop_type, "type": "create", "value": value} for value in to_create]
    changes += [{"field": prop, "prop_type": prop_type, "type": "delete", "value": value} for value in to_delete]

    return changes


def sync_mixed_value_array(prop, dasch_array, omeka_array):
    """
    Sync array values that can be either TextValue or UriValue.
    Each value's type is determined by its content (URI or text).
    This is used for issue #7 fields like creator, publisher, source, relation.
    """
    dasch_set = {value for value in dasch_array if value}
    omeka_set = {value for value in omeka_array if value}

    to_create = omeka_set - dasch_set  
    to_delete = dasch_set - omeka_set  

    changes = []
    for value in to_create:
        # Determine type based on content
        prop_type = "UriValue" if (value.startswith("http://") or value.startswith("https://")) else "TextValue"
        changes.append({"field": prop, "prop_type": prop_type, "type": "create", "value": value})
    
    for value in to_delete:
        # For deletion, we don't need to specify the type, but we'll determine it anyway
        prop_type = "UriValue" if (value.startswith("http://") or value.startswith("https://")) else "TextValue"
        changes.append({"field": prop, "prop_type": prop_type, "type": "delete", "value": value})

    return changes


def check_values(dasch_item, omeka_item, lists):
    modified_values = []
    title = sync_value(
        "hasTitle",
        "TextValue",
        extract_dasch_propvalue(dasch_item, "hasTitle"),
        extract_property(omeka_item.get("dcterms:title", []), 1),
    )
    if title:
        modified_values.append(title)

    description = sync_value(
        "hasDescription",
        "TextValue",
        extract_dasch_propvalue(dasch_item, "hasDescription"),
        extract_property(omeka_item.get("dcterms:description", []), 4),
    )
    if description:
        modified_values.append(description)

    subjects = []
    for data in extract_combined_values(omeka_item.get("dcterms:subject", [])):
        subject_iri = extract_listvalueiri_from_value(data, "subject", lists)
        if subject_iri:
            subjects.append(subject_iri)
    subject = sync_array_value(
        "hasSubjectList",
        "ListValue",
        extract_dasch_propvalue_multiple(dasch_item, "hasSubjectList"),
        subjects,
    )
    if subject:
        modified_values.extend(subject)

    temporal = sync_value(
        "hasTemporalList",
        "ListValue",
        extract_dasch_propvalue(dasch_item, "hasTemporalList"),
        extract_listvalueiri_from_value(
            extract_property(omeka_item.get("dcterms:temporal", []), 41),
            "temporal",
            lists,
        ),
    )
    if temporal:
        modified_values.append(temporal)

    language = sync_value(
        "hasLanguageList",
        "ListValue",
        extract_dasch_propvalue(dasch_item, "hasLanguageList"),
        extract_listvalueiri_from_value(
            extract_property(omeka_item.get("dcterms:language", []), 12),
            "language",
            lists,
        ),
    )
    if language:
        modified_values.append(language)

    # Check object specific fields
    if dasch_item["@type"] == METADATA_RESOURCE_TYPE:
        # Support mixed TextValue/UriValue for isPartOf (issue #7)
        is_part_of = sync_mixed_value_array(
            "isPartOf",
            extract_dasch_propvalue_multiple(dasch_item, "isPartOf"),
            extract_combined_values(omeka_item.get("dcterms:isPartOf", [])),
        )
        if is_part_of:
            modified_values.extend(is_part_of)

    # Check media specific fields
    if dasch_item["@type"] in MEDIA_RESOURCE_TYPES:
        # Support mixed TextValue/UriValue for creator, publisher, source, relation (issue #7)
        creator = sync_mixed_value_array(
            "hasCreator",
            extract_dasch_propvalue_multiple(dasch_item, "hasCreator"),
            extract_combined_values(omeka_item.get("dcterms:creator", [])),
        )
        if creator:
            modified_values.extend(creator)

        publisher = sync_mixed_value_array(
            "hasPublisher",
            extract_dasch_propvalue_multiple(dasch_item, "hasPublisher"),
            extract_combined_values(omeka_item.get("dcterms:publisher", [])),
        )
        if publisher:
            modified_values.extend(publisher)

        date = sync_value(
            "hasDate",
            "TextValue",
            extract_dasch_propvalue(dasch_item, "hasDate"),
            extract_property(omeka_item.get("dcterms:date", []), 7),
        )
        if date:
            modified_values.append(date)

        extent = sync_value(
            "hasExtent",
            "TextValue",
            extract_dasch_propvalue(dasch_item, "hasExtent"),
            extract_property(omeka_item.get("dcterms:extent", []), 25),
        )
        if extent:
            modified_values.append(extent)

        # Support multiple type values (issue #7)
        type_iris = []
        for type_label in extract_combined_values(omeka_item.get("dcterms:type", [])):
            type_iri = extract_listvalueiri_from_value(type_label, "type", lists)
            if type_iri:
                type_iris.append(type_iri)
        resource_types = sync_array_value(
            "hasTypeList",
            "ListValue",
            extract_dasch_propvalue_multiple(dasch_item, "hasTypeList"),
            type_iris,
        )
        if resource_types:
            modified_values.extend(resource_types)

        format_value = sync_value(
            "hasFormatList",
            "ListValue",
            extract_dasch_propvalue(dasch_item, "hasFormatList"),
            extract_listvalueiri_from_value(
                extract_property(omeka_item.get("dcterms:format", []), 9),
                "format",
                lists,
            ),
        )
        if format_value:
            modified_values.append(format_value)

        source = sync_mixed_value_array(
            "hasSource",
            extract_dasch_propvalue_multiple(dasch_item, "hasSource"),
            extract_combined_values(omeka_item.get("dcterms:source", [])),
        )
        if source:
            modified_values.extend(source)

        relation = sync_mixed_value_array(
            "hasRelation",
            extract_dasch_propvalue_multiple(dasch_item, "hasRelation"),
            extract_combined_values(omeka_item.get("dcterms:relation", [])),
        )
        if relation:
            modified_values.extend(relation)

        rights = sync_value(
            "hasRights",
            "TextValue",
            extract_dasch_propvalue(dasch_item, "hasRights"),
            extract_property(omeka_item.get("dcterms:rights", []), 15),
        )
        if rights:
            modified_values.append(rights)

        license_value = sync_value(
            "hasLicenseList",
            "ListValue",
            extract_dasch_propvalue(dasch_item, "hasLicenseList"),
            extract_listvalueiri_from_value(
                extract_property(omeka_item.get("dcterms:license", []), 49),
                "license",
                lists,
            ),
        )
        if license_value:
            modified_values.append(license_value)

        # Optional: abstract mapping (issue #7)
        abstract_values = extract_combined_values(omeka_item.get("dcterms:abstract", []))
        abstract_value = abstract_values[0] if abstract_values else ""
        abstract = sync_value(
            "hasAbstract",
            "TextValue",
            extract_dasch_propvalue(dasch_item, "hasAbstract"),
            abstract_value,
        )
        if abstract:
            modified_values.append(abstract)

    return modified_values
    

def _normalise_labels(raw_value):
    labels = set()
    if isinstance(raw_value, str):
        labels.add(raw_value)
    elif isinstance(raw_value, dict):
        label_value = raw_value.get("@value") or raw_value.get("value")
        if label_value:
            labels.add(label_value)
    elif isinstance(raw_value, list):
        for entry in raw_value:
            labels.update(_normalise_labels(entry))
    return labels


def extract_listvalueiri_from_value(value, list_key, lists):
    if not value:
        return None

    lookup_value = value.strip() if isinstance(value, str) else value
    possible_labels = LIST_LABELS.get(list_key, {list_key})

    def list_matches(list_data):
        labels = set()
        labels.update(_normalise_labels(list_data.get("rdfs:label")))
        labels.update(_normalise_labels(list_data.get("labels")))
        name = list_data.get("name")
        if name:
            labels.add(name)
        return bool(labels & possible_labels)

    reference = next((list_data for list_data in lists if list_matches(list_data)), None)

    if not reference:
        logging.warning(
            "No list found for key '%s' while looking up value '%s'",
            list_key,
            lookup_value,
        )
        return None

    sublist = reference.get("knora-api:hasSubListNode", [])
    if isinstance(sublist, dict):
        sublist = [sublist]

    for node in sublist:
        node_labels = set()
        node_labels.update(_normalise_labels(node.get("rdfs:label")))
        node_labels.update(_normalise_labels(node.get("labels")))
        node_name = node.get("name")
        if node_name:
            node_labels.add(node_name)
        if lookup_value in node_labels:
            return node.get("@id")

    logging.warning(
        "No match found for value '%s' in list with key '%s'",
        lookup_value,
        list_key,
    )
    return None


def build_text_or_uri_values(values):
    """
    Build a list of TextValue or UriValue objects based on content.
    URIs (starting with http:// or https://) become UriValue, others become TextValue.
    This addresses issue #7.
    """
    result = []
    for val in values:
        if isinstance(val, str):
            if val.startswith("http://") or val.startswith("https://"):
                result.append({
                    "@type": "knora-api:UriValue",
                    "knora-api:uriValueAsUri": {
                        "@value": val,
                        "@type": "http://www.w3.org/2001/XMLSchema#anyURI"
                    }
                })
            else:
                result.append({
                    "@type": "knora-api:TextValue",
                    "knora-api:valueAsString": val
                })
    return result


def construct_payload(item, type, project_iri, lists, parent_iri, internalMediaFilename):
    payload = {
        "@context": build_context(),
        "@type": type,
        "knora-api:attachedToProject": {"@id": project_iri},
        "rdfs:label": extract_property(item.get("dcterms:title", []), 1),
        f"{PREFIX}hasIdentifier": {
            "knora-api:valueAsString": extract_property(
                item.get("dcterms:identifier", []), 10
            ),
            "@type": "knora-api:TextValue",
        },
        f"{PREFIX}hasTitle": {
            "knora-api:valueAsString": extract_property(
                item.get("dcterms:title", []), 1
            ),
            "@type": "knora-api:TextValue",
        },
    }

    description_value = extract_property(item.get("dcterms:description", []), 4)
    if description_value:
        payload[f"{PREFIX}hasDescription"] = {
            "knora-api:valueAsString": description_value,
            "@type": "knora-api:TextValue",
        }

    subjects = []
    for data in extract_combined_values(item.get("dcterms:subject", [])):
        subject_iri = extract_listvalueiri_from_value(data, "subject", lists)
        if subject_iri:
            subjects.append(
                {
                    "@type": "knora-api:ListValue",
                    "knora-api:listValueAsListNode": {"@id": subject_iri},
                }
            )
    if subjects:
        payload[f"{PREFIX}hasSubjectList"] = subjects

    temporal_iri = extract_listvalueiri_from_value(
        extract_property(item.get("dcterms:temporal", []), 41), "temporal", lists
    )
    if temporal_iri:
        payload[f"{PREFIX}hasTemporalList"] = {
            "@type": "knora-api:ListValue",
            "knora-api:listValueAsListNode": {"@id": temporal_iri},
        }

    language_iri = extract_listvalueiri_from_value(
        extract_property(item.get("dcterms:language", []), 12), "language", lists
    )
    if language_iri:
        payload[f"{PREFIX}hasLanguageList"] = {
            "@type": "knora-api:ListValue",
            "knora-api:listValueAsListNode": {"@id": language_iri},
        }

    # Support URIs in isPartOf (issue #7)
    if "dcterms:isPartOf" in item:
        is_part_of_values = extract_combined_values(item.get("dcterms:isPartOf", []))
        is_part_of_entries = build_text_or_uri_values(is_part_of_values)
        if is_part_of_entries:
            payload[f"{PREFIX}isPartOf"] = is_part_of_entries

    if type in MEDIA_RESOURCE_TYPES and parent_iri:
        payload[f"{PREFIX}linkToParentObjectValue"] = {
            "@type": "knora-api:LinkValue",
            "knora-api:linkValueHasTargetIri": {"@id": parent_iri},
        }

    if type == f"{PREFIX}Image" and internalMediaFilename:
        payload["knora-api:hasStillImageFileValue"] = {
            "@type": "knora-api:StillImageFileValue",
            "knora-api:fileValueHasFilename": internalMediaFilename,
        }
    elif type == f"{PREFIX}Document" and internalMediaFilename:
        payload["knora-api:hasDocumentFileValue"] = {
            "@type": "knora-api:DocumentFileValue",
            "knora-api:fileValueHasFilename": internalMediaFilename,
        }

    if type in MEDIA_RESOURCE_TYPES:
        date_value = extract_property(item.get("dcterms:date", []), 7)
        if date_value:
            payload[f"{PREFIX}hasDate"] = {
                "knora-api:valueAsString": date_value,
                "@type": "knora-api:TextValue",
            }

        # Support multiple type values (issue #7)
        type_values = []
        for type_label in extract_combined_values(item.get("dcterms:type", [])):
            type_iri = extract_listvalueiri_from_value(type_label, "type", lists)
            if type_iri:
                type_values.append({
                    "@type": "knora-api:ListValue",
                    "knora-api:listValueAsListNode": {"@id": type_iri},
                })
        if type_values:
            payload[f"{PREFIX}hasTypeList"] = type_values

        format_iri = extract_listvalueiri_from_value(
            extract_property(item.get("dcterms:format", []), 9), "format", lists
        )
        if format_iri:
            payload[f"{PREFIX}hasFormatList"] = {
                "@type": "knora-api:ListValue",
                "knora-api:listValueAsListNode": {"@id": format_iri},
            }

        extent_value = extract_property(item.get("dcterms:extent", []), 25)
        if extent_value:
            payload[f"{PREFIX}hasExtent"] = {
                "knora-api:valueAsString": extent_value,
                "@type": "knora-api:TextValue",
            }

        # Optional: abstract mapping (issue #7)
        abstract_values = extract_combined_values(item.get("dcterms:abstract", []))
        if abstract_values:
            # Take the first abstract value if multiple exist
            payload[f"{PREFIX}hasAbstract"] = {
                "knora-api:valueAsString": abstract_values[0],
                "@type": "knora-api:TextValue",
            }

        rights_value = extract_property(item.get("dcterms:rights", []), 15)
        if rights_value:
            payload[f"{PREFIX}hasRights"] = {
                "knora-api:valueAsString": rights_value,
                "@type": "knora-api:TextValue",
            }

        license_iri = extract_listvalueiri_from_value(
            extract_property(item.get("dcterms:license", []), 49), "license", lists
        )
        if license_iri:
            payload[f"{PREFIX}hasLicenseList"] = {
                "@type": "knora-api:ListValue",
                "knora-api:listValueAsListNode": {"@id": license_iri},
            }

        # Support URIs for creator, publisher, source, relation (issue #7)
        if "dcterms:creator" in item:
            creator_values = extract_combined_values(item.get("dcterms:creator", []))
            creators = build_text_or_uri_values(creator_values)
            if creators:
                payload[f"{PREFIX}hasCreator"] = creators

        if "dcterms:publisher" in item:
            publisher_values = extract_combined_values(item.get("dcterms:publisher", []))
            publishers = build_text_or_uri_values(publisher_values)
            if publishers:
                payload[f"{PREFIX}hasPublisher"] = publishers

        if "dcterms:source" in item:
            source_values = extract_combined_values(item.get("dcterms:source", []))
            sources = build_text_or_uri_values(source_values)
            if sources:
                payload[f"{PREFIX}hasSource"] = sources

        if "dcterms:relation" in item:
            relation_values = extract_combined_values(item.get("dcterms:relation", []))
            relations = build_text_or_uri_values(relation_values)
            if relations:
                payload[f"{PREFIX}hasRelation"] = relations

    return payload

def upload_file_from_url(file_url: str, token: str, zip: bool = False) -> str:
    """
    Downloads a file from a URL and uploads it to the specified endpoint.

    Args:
        file_url (str): The URL of the file to be uploaded.
        token (str): The authentication token for the upload endpoint.

    Returns:
        str: The internal filename returned by the upload endpoint.
    """
    # Download the file from the URL
    try:
        response = requests.get(file_url, stream=True, timeout=10)
    except requests.exceptions.RequestException as err:
        logging.error(f"File download error: {err}")
        raise     
    # Extract the original filename from the URL
    original_filename = Path(urllib.parse.urlparse(file_url).path).name
    if not original_filename:
        raise ValueError("The file URL does not contain a valid filename.")

    # Save the file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(response.content)
        temp_file_path = Path(temp_file.name)

    if zip:
        zip_temp_file_path = temp_file_path.with_suffix(".zip")
        with zipfile.ZipFile(zip_temp_file_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(temp_file_path, arcname=original_filename)
        temp_file_path.unlink()
        temp_file_path = zip_temp_file_path

    # Prepare the upload
    final_filename = original_filename if not zip else temp_file_path.name
    encoded_filename = urllib.parse.quote(final_filename)
    endpoint = f"{INGEST_HOST}/projects/{PROJECT_SHORT_CODE}/assets/ingest/{encoded_filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }
    
    try:
        # Upload the file
        with open(temp_file_path, "rb") as file_data:
            upload_response = requests.post(endpoint, data=file_data, headers=headers, timeout=30)
        
        # Clean up the temporary file
        temp_file_path.unlink()

        # Handle the response
        if upload_response.status_code == 200:
            return cast(str, upload_response.json()["internalFilename"])
        else:
            logging.error(
                f"Unexpected response status {upload_response.status_code}: "
                f"{upload_response.text}"
            )
            return None
    except requests.exceptions.RequestException as err:
        logging.error(f"File upload error: {err}")
   
    return None


def create_resource(payload: dict, token: str) -> None:
    # https://docs.dasch.swiss/latest/DSP-API/03-endpoints/api-v2/editing-resources/#creating-a-resource
    resources_endpoint = f"{API_HOST}/v2/resources"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Asset-Ingested": "true",
    }

    response = requests.post(resources_endpoint, json=payload, headers=headers, timeout=10)
    identifier_value = payload.get(f"{PREFIX}hasIdentifier", {}).get("knora-api:valueAsString", "unknown identifier")
    if response.status_code == 200:
        logging.info(f"{identifier_value}: resource created on DaSCH")
    else:
        logging.error(
            f"{identifier_value}: resource creation failed: {response.status_code}: {response.text}"
        )
        logging.error(payload)


def specify_mediaclass(media_type: str) -> str:
    """
    DSP-API v2 currently supports using SIPI to store the following types of files:

    Images: JPEG, JPEG2000, TIFF, or PNG which are stored internally as JPEG2000
    Documents: PDF
    Audio: MPEG or Waveform audio file format (.wav, .x-wav, .vnd.wave)
    Text files: CSV, JSON, ODD, RNG, TXT, XLS, XLSX, XML, XSD, XSL
    Video files: MP4
    Archive files: ZIP, TAR, GZIP
    (https://docs.dasch.swiss/latest/DSP-API/03-endpoints/api-v2/editing-values/)
    """

    valid_images_types = {"image/tiff", "image/jpg", "image/jpeg", "image/png", "image/gif"}
    valid_text_types = {"text/csv", "text/markdown", "text/plain", "application/json"}
    valid_doc_types = {"application/pdf"}
    if media_type in valid_images_types:
        return f"{PREFIX}Image"
    if media_type in valid_text_types or media_type in valid_doc_types:
        return f"{PREFIX}Document"
    logging.warning(
        "Unsupported or missing media type '%s'; falling back to ResourceWithoutMedia",
        media_type,
    )
    return f"{PREFIX}ResourceWithoutMedia"
    

def main() -> None:

    args = parse_arguments()

    # Fetch item data
    items_data = get_items_from_collection(ITEM_SET_ID)

    constrain_to_iconclass = args.mode in {'sample_data', 'test_data'}

    if args.mode == 'sample_data':
        items_data = random.sample(items_data, NUMBER_RANDOM_OBJECTS)

    if args.mode == 'test_data':
        found_objects = []
        remaining_identifiers = TEST_DATA.copy()

        for obj in items_data:
            for identifier in obj.get('dcterms:identifier', []):
                if identifier['@value'] in remaining_identifiers:
                    found_objects.append(obj)
                    remaining_identifiers.remove(identifier['@value'])
                    
            if not remaining_identifiers:
                break
        items_data = found_objects

    if constrain_to_iconclass:
        apply_iconclass_subject(items_data)

    # get_project()
    token = login(DSP_USER, DSP_PWD)
    project_iri = get_project()
    # get list and list values
    project_lists = get_lists(project_iri)

    for item in items_data:
        item_id = extract_property(item.get("dcterms:identifier", []), 10)
        metadata_iri = get_resource_by_id(token, METADATA_RESOURCE_TYPE, item_id).get('@id')
        if metadata_iri:
            object = get_full_resource(token, urllib.parse.quote(metadata_iri, safe=''))

            if 'knora-api:lastModificationDate' in object:
                dasch_date = object['knora-api:lastModificationDate']['@value']
            else:
                dasch_date = object['knora-api:creationDate']['@value']
            if item['o:modified']['@value'] > dasch_date:
                logging.info(f"{item_id}: object exists already, but it was modified. Update object ...")
                modified_values = check_values(object, item, project_lists)
                # print(modified_values)
                for value in modified_values:
                    update_value(token, object,value["value"],value["field"],value["prop_type"],value["type"])
            else:
                logging.info(f"{item_id}: object exists already")

        else:
            payload = construct_payload(item, METADATA_RESOURCE_TYPE, project_iri, project_lists,"",None)
            create_resource(payload, token)
            metadata_iri = get_resource_by_id(token, METADATA_RESOURCE_TYPE, item_id).get('@id')
        media_data = get_media(item.get("o:id", ""))
        if constrain_to_iconclass:
            apply_iconclass_subject(media_data)
        if media_data:
            for media in media_data:
                # Skip private media (issues #13, #14, #12)
                if not media.get("o:is_public", True):
                    media_id = extract_property(media.get("dcterms:identifier", []), 10)
                    logging.info(f"{media_id}: skipping private media")
                    continue
                
                media_id = extract_property(media.get("dcterms:identifier", []), 10)
                media_class = specify_mediaclass(extract_property(media.get("dcterms:format", []), 9))
                mediadata_iri = get_resource_by_id(token, media_class, media_id).get('@id')
                if mediadata_iri:
                    object = get_full_resource(token, urllib.parse.quote(mediadata_iri, safe=''))

                    if 'knora-api:lastModificationDate' in object:
                        dasch_date = object['knora-api:lastModificationDate']['@value']
                    else:
                        dasch_date = object['knora-api:creationDate']['@value']
                    if media['o:modified']['@value'] > dasch_date:
                        logging.info(f"{media_id}: media exists already, but it was modified. Update object ...")
                        modified_values = check_values(object, media, project_lists)
                        # print(modified_values)
                        for value in modified_values:
                            update_value(token, object,value["value"],value["field"],value["prop_type"],value["type"])
                    else:
                        logging.info(f"{media_id}: media exists already")
                else:
                    logging.info(f"{media_id}: adding media to {media_class} ...")
                    object_location = media.get("o:original_url", "")
                    # upload the original file for supported media types
                    internalFilename = None
                    if media_class != f"{PREFIX}ResourceWithoutMedia":
                        internalFilename = upload_file_from_url(object_location,token)
                    if media_class == f"{PREFIX}ResourceWithoutMedia" or internalFilename:
                        media_payload = construct_payload(media, media_class, project_iri, project_lists, metadata_iri,internalFilename)
                        create_resource(media_payload, token)
                    else:
                        logging.error(f"{media_id}: could not create resource")


if __name__ == "__main__":
    main()
