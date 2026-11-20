"""Read Omeka items and media from the Omeka API or from a snapshot directory."""

import json
import logging
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from omeka2dsp.dsp import HttpSession
from omeka2dsp.settings import Settings
from omeka2dsp.values import OmekaRecord

log = logging.getLogger(__name__)

# The order of sgb_validator.snapshots.read_snapshot: a "_transformed" file
# comes before a plain file, and a plain file before a "_raw" file.
SNAPSHOT_SUFFIXES = ("_transformed", "", "_raw")


def _pages(session: HttpSession, url: str, params: dict[str, Any] | None) -> list[Any]:
    records: list[Any] = []
    next_url: str | None = url
    while next_url:
        try:
            response = session.get(next_url, params=params)
            response.raise_for_status()
        except requests.exceptions.RequestException as error:
            log.error(f"Error fetching items: {error}")
            break
        records.extend(response.json())
        next_url = response.links.get("next", {}).get("url")
        params = None
    return records


def _keys(settings: Settings) -> dict[str, Any]:
    return {
        "key_identity": settings.key_identity,
        "key_credential": settings.key_credential,
    }


def api_items(settings: Settings, session: HttpSession) -> list[OmekaRecord]:
    """All items of the item set."""
    params = {"item_set_id": settings.item_set_id, "per_page": 100, **_keys(settings)}
    url = urljoin(settings.omeka_api_url, "items")
    return [OmekaRecord.parse(raw) for raw in _pages(session, url, params)]


def api_media(
    settings: Settings, session: HttpSession, item: OmekaRecord
) -> list[OmekaRecord]:
    params = {"item_id": item.id, **_keys(settings)}
    url = urljoin(settings.omeka_api_url, "media")
    return [OmekaRecord.parse(raw) for raw in _pages(session, url, params)]


def _read(directory: Path, name: str) -> list[OmekaRecord]:
    for suffix in SNAPSHOT_SUFFIXES:
        path = directory / f"{name}{suffix}.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return [
                OmekaRecord.parse(raw)
                for raw in (data if isinstance(data, list) else [data])
            ]
    raise FileNotFoundError(f"No {name}*.json in snapshot {directory}")


def snapshot(directory: Path) -> tuple[list[OmekaRecord], list[OmekaRecord]]:
    """The items and media of an sgb-data-validator snapshot directory."""
    return _read(directory, "items"), _read(directory, "media")


def media_by_item(media: Iterable[OmekaRecord]) -> dict[int, list[OmekaRecord]]:
    grouped: dict[int, list[OmekaRecord]] = defaultdict(list)
    for record in media:
        if record.item_id is not None:
            grouped[record.item_id].append(record)
    return dict(grouped)


def select(items: Iterable[OmekaRecord], ids: set[str]) -> list[OmekaRecord]:
    """The items with a dcterms:identifier in ids."""
    return [item for item in items if item.identifiers() & ids]
