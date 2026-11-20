import json
from pathlib import Path

from omeka2dsp.lists import resolve

ROOT = Path(__file__).parent.parent
EXAMPLE = json.loads((ROOT / "data" / "example_api_get_listvalues.json").read_text())

# The DSP license list uses the license URL as the node label, and Omeka's
# dcterms:license @value is the same URL (issue #7).
LICENSE_URLS = {
    "https://creativecommons.org/publicdomain/mark/1.0/": "license_cc_pdm",
    "https://creativecommons.org/publicdomain/zero/1.0/": "license_cc0",
    "https://creativecommons.org/licenses/by/4.0/": "license_cc_by_4",
    "https://creativecommons.org/licenses/by-sa/4.0/": "license_cc_by_sa_4",
    "https://creativecommons.org/licenses/by-nc-sa/4.0/": "license_cc_by_nc_sa_4",
    "http://rightsstatements.org/vocab/InC/1.0/": "license_in_c",
    "http://rightsstatements.org/vocab/InC-RUU/1.0/": "license_in_c_ruu",
}
LICENSES = [
    {
        "rdfs:label": "Licenses",
        "knora-api:hasSubListNode": [
            {"@id": f"http://rdfh.ch/lists/0123/{name}", "rdfs:label": url}
            for url, name in LICENSE_URLS.items()
        ],
    }
]


def test_license_urls_resolve():
    for url, name in LICENSE_URLS.items():
        assert resolve(LICENSES, "license", url) == f"http://rdfh.ch/lists/0123/{name}"


def test_unknown_label_or_list_returns_none():
    assert resolve(LICENSES, "license", "https://example.com/x/") is None
    assert resolve(LICENSES, "language", "de") is None
    assert resolve(LICENSES, "license", "") is None


def test_lookup_ignores_case_and_reads_admin_labels():
    assert resolve(EXAMPLE, "type", "image") == resolve(EXAMPLE, "type", "Image")
    admin = [
        {
            "labels": [{"value": "ISO 639-1", "language": "en"}],
            "knora-api:hasSubListNode": {"@id": "iri-de", "name": "de"},
        }
    ]
    assert resolve(admin, "language", " de ") == "iri-de"
