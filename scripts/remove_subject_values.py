"""Delete all hasSubjectList values from DaSCH resources (issue #7).

Subjects are no longer migrated (Iconclass classification was dropped for time
and personnel reasons), but earlier sample/test runs wrote subject values to
DaSCH. This one-off maintenance script removes them so DaSCH stays free of
subject tags. Run with --dry-run first to see what would be deleted.
"""

import argparse
import logging
import urllib.parse

import requests
from data_2_dasch import (
    API_HOST,
    DEFAULT_TIMEOUT,
    DSP_PWD,
    DSP_USER,
    MEDIA_RESOURCE_TYPES,
    METADATA_RESOURCE_TYPE,
    ONTOLOGY_CONTEXT,
    PREFIX,
    extract_dasch_propvalue_multiple,
    get_full_resource,
    login,
    update_value,
)


def find_resources_with_subject(token: str, object_class: str) -> list:
    """Return IRIs of resources of the given class that have a hasSubjectList value.

    Gravsearch results are paginated: OFFSET is the 0-based page index, and the
    response carries knora-api:mayHaveMoreResults while further pages exist.
    """
    iris = []
    offset = 0
    while True:
        query = f"""
            PREFIX knora-api: <http://api.knora.org/ontology/knora-api/v2#>
            PREFIX {PREFIX} <{ONTOLOGY_CONTEXT}>
            CONSTRUCT {{
                ?resource knora-api:isMainResource true .
                ?resource {PREFIX}hasSubjectList ?subject .
            }} WHERE {{
                ?resource a {object_class} .
                ?resource {PREFIX}hasSubjectList ?subject .
            }}
            OFFSET {offset}
            """
        response = requests.post(
            f"{API_HOST}/v2/searchextended",
            data=query.encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/sparql-query; charset=utf-8",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code != 200:
            logging.error(f"Search failed for {object_class}: {response.status_code}")
            logging.error(response.text)
            break
        result = response.json()
        # A single hit comes back as the resource itself, multiple hits under @graph.
        resources = result.get("@graph", [result] if "@id" in result else [])
        iris.extend(resource["@id"] for resource in resources)
        if not result.get("knora-api:mayHaveMoreResults"):
            break
        offset += 1
    return iris


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only report which subject values would be deleted",
    )
    args = parser.parse_args()

    # Stream-only logging; deliberately not data_2_dasch.setup_logging(), which
    # would truncate the migration log.
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    token = login(DSP_USER, DSP_PWD)
    total = 0
    for object_class in [METADATA_RESOURCE_TYPE, *sorted(MEDIA_RESOURCE_TYPES)]:
        for resource_iri in find_resources_with_subject(token, object_class):
            resource = get_full_resource(
                token, urllib.parse.quote(resource_iri, safe="")
            )
            for value in extract_dasch_propvalue_multiple(resource, "hasSubjectList"):
                total += 1
                if args.dry_run:
                    logging.info(
                        f"[dry-run] would delete hasSubjectList '{value}' "
                        f"from {resource_iri}"
                    )
                else:
                    update_value(
                        token, resource, value, "hasSubjectList", "ListValue", "delete"
                    )
    logging.info(f"{'Found' if args.dry_run else 'Deleted'} {total} subject value(s)")


if __name__ == "__main__":
    main()
