import logging
import os
from urllib.parse import urljoin, urlparse

import requests

# Configuration
OMEKA_API_URL = os.getenv("OMEKA_API_URL", 'https://omeka.unibe.ch/api/')
KEY_IDENTITY = os.getenv("KEY_IDENTITY")
KEY_CREDENTIAL = os.getenv("KEY_CREDENTIAL")
ITEM_SET_ID = os.getenv("ITEM_SET_ID", '10780')


# --- Helper Functions for Data Extraction ---
def is_valid_url(url):
    """Checks if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def download_file(url, dest_path):
    """Downloads a file from a given URL to the specified destination path."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    except requests.exceptions.RequestException as err:
        logging.error(f"File download error: {err}")
        raise


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
def extract_property(props, prop_id, as_uri=False, only_label=False):
    """Extracts a property value or URI from properties based on property ID."""
    for prop in props:
        if prop.get("property_id") == prop_id:
            if as_uri:
                return f"[{prop.get('o:label', '')}]({prop.get('@id', '')})"
            if only_label: 
                return prop.get('o:label', '')
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


def update_omeka_item(item_id: int, property_id: int, dsp_uri: str) -> bool:
    """
    Updates an Omeka item by adding a DSP URI to a specific property.
    
    Args:
        item_id: The Omeka item ID to update
        property_id: The property ID (e.g., for dcterms:hasVersion)  
        dsp_uri: The DSP resource URI to add
        
    Returns:
        bool: True if update successful, False otherwise
    """
    url = urljoin(OMEKA_API_URL, f"items/{item_id}")
    
    # First, get the current item data
    params = {
        "key_identity": KEY_IDENTITY,
        "key_credential": KEY_CREDENTIAL
    }
    
    try:
        # Get current item
        response = requests.get(url, params=params)
        response.raise_for_status()
        item_data = response.json()
        
        # Prepare the property update payload
        # Find the property key for the given property_id
        property_key = None
        for key in item_data.keys():
            if key.startswith("dcterms:") or key.startswith("bibo:") or key.startswith("foaf:"):
                # Check if this property already exists and has the right property_id
                if isinstance(item_data[key], list) and len(item_data[key]) > 0:
                    if item_data[key][0].get("property_id") == property_id:
                        property_key = key
                        break
        
        # If property doesn't exist yet, we need to determine the correct key
        # For dcterms:hasVersion, property_id should be for hasVersion
        if not property_key:
            property_key = "dcterms:hasVersion"
        
        # Prepare the property value
        new_property_value = {
            "@value": dsp_uri,
            "property_id": property_id,
            "type": "literal"
        }
        
        # Add to existing values or create new property
        if property_key in item_data and isinstance(item_data[property_key], list):
            item_data[property_key].append(new_property_value)
        else:
            item_data[property_key] = [new_property_value]
        
        # Update the item via PUT request
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.put(url, json=item_data, params=params, headers=headers)
        response.raise_for_status()
        
        logging.info(f"Successfully updated Omeka item {item_id} with DSP URI: {dsp_uri}")
        return True
        
    except requests.exceptions.RequestException as err:
        logging.error(f"Failed to update Omeka item {item_id}: {err}")
        return False
