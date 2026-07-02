import logging
import os
from urllib.parse import urljoin

import requests

# Configuration
OMEKA_API_URL = os.getenv("OMEKA_API_URL", 'https://omeka.unibe.ch/api/')
KEY_IDENTITY = os.getenv("KEY_IDENTITY")
KEY_CREDENTIAL = os.getenv("KEY_CREDENTIAL")
ITEM_SET_ID = os.getenv("ITEM_SET_ID", '10780')


def get_paginated_items(url, params):
    """Fetches all items from a paginated API endpoint."""
    items = []
    while url:
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            logging.error(f"Error fetching items: {err}")
            break
        items.extend(response.json())
        url = response.links.get("next", {}).get("url")
        params = None

    return items


def get_items_from_collection(collection_id):
    """Fetches all items from a specified collection."""
    params = {
        "item_set_id": collection_id,
        "key_identity": KEY_IDENTITY,
        "key_credential": KEY_CREDENTIAL,
        "per_page": 100,
    }
    return get_paginated_items(urljoin(OMEKA_API_URL, "items"), params)


def get_media(item_id):
    """Fetches media associated with a specific item ID."""
    params = {"key_identity": KEY_IDENTITY, "key_credential": KEY_CREDENTIAL}
    return get_paginated_items(
        urljoin(OMEKA_API_URL, f"media?item_id={item_id}"), params
    )


# --- Data Extraction and Transformation Functions ---
def extract_property(props, prop_id):
    """Extracts a property value from properties based on property ID."""
    for prop in props:
        if prop.get("property_id") == prop_id:
            return prop.get("@value", "")
    return ""


def extract_combined_values(props):
    """Combines text values and URIs from properties into a single list."""
    values = [
        prop.get("@value", "").replace(";", "&#59")
        for prop in props
        if "@value" in prop
    ]
    uris = [
        f"<a href='{prop.get('@id', '').replace(';', '&#59')}'>{prop.get('o:label', '').replace(';', '&#59')}</a>"
        for prop in props
        if "@id" in prop
    ]
    return values + uris
