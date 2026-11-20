"""Add the Text class from data/data_model_dasch.json to the live DSP ontology.

DSP rejects CSV and JSON as DocumentFileValue, and the SGB ontology had no class
for text files. SGB:Text (knora-api:TextRepresentation) stores them unchanged.

Default: print the request and write nothing. Use --apply to send it.
Needs a DSP user with project-admin rights.
"""

import json
import sys
import urllib.parse
from pathlib import Path

import data_2_dasch as d
import requests

CARDINALITIES = {
    "1": ("owl:cardinality", 1),
    "0-1": ("owl:maxCardinality", 1),
    "0-n": ("owl:minCardinality", 0),
    "1-n": ("owl:minCardinality", 1),
}
MODEL = Path(__file__).parent.parent / "data" / "data_model_dasch.json"


def class_request(model: dict, ontology_iri: str, last_modified: dict) -> dict:
    """Build the POST /v2/ontologies/classes body for the Text class."""
    ontology = model["project"]["ontologies"][0]
    text = next(r for r in ontology["resources"] if r["name"] == "Text")
    restrictions = [
        {
            "@type": "owl:Restriction",
            CARDINALITIES[c["cardinality"]][0]: CARDINALITIES[c["cardinality"]][1],
            "owl:onProperty": {"@id": f"{d.PREFIX}{c['propname'].lstrip(':')}"},
            "salsah-gui:guiOrder": c["gui_order"],
        }
        for c in text["cardinalities"]
    ]

    def lang(values):
        return [{"@language": k, "@value": v} for k, v in values.items()]

    return {
        "@id": ontology_iri,
        "@type": "owl:Ontology",
        "knora-api:lastModificationDate": last_modified,
        "@graph": [
            {
                "@id": f"{d.PREFIX}Text",
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
            d.ONTOLOGY_NAME: f"{ontology_iri}#",
        },
    }


def main() -> None:
    d.setup_logging()
    token = d.login(d.DSP_USER, d.DSP_PWD)
    project_iri = d.get_project()
    headers = {"Authorization": f"Bearer {token}"}
    ontology_iri = d.ONTOLOGY_CONTEXT.rstrip("#")
    meta = requests.get(
        f"{d.API_HOST}/v2/ontologies/metadata/{urllib.parse.quote(project_iri, safe='')}",
        headers=headers,
        timeout=d.DEFAULT_TIMEOUT,
    ).json()
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    body = class_request(model, ontology_iri, meta["knora-api:lastModificationDate"])
    if "--apply" not in sys.argv:
        print(json.dumps(body, indent=2, ensure_ascii=False))
        print("Dry run. Use --apply to create the class.")
        return
    response = requests.post(
        f"{d.API_HOST}/v2/ontologies/classes",
        json=body,
        headers=headers,
        timeout=60,
    )
    print(response.status_code, response.text[:1000])


if __name__ == "__main__":
    main()
