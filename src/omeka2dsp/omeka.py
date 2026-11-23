"""Read Omeka items and media with omeka-s-client, from the API or a snapshot."""

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from omeka_s_client import OmekaClient, read_snapshot

from omeka2dsp.settings import Settings
from omeka2dsp.values import OmekaRecord


def client(settings: Settings, **overrides: Any) -> OmekaClient:
    """An Omeka client for the settings. Tests can set transport, sleep and retries."""
    return OmekaClient(
        settings.omeka_api_url,
        key_identity=settings.key_identity,
        key_credential=settings.key_credential,
        timeout=settings.http_timeout,
        cache_busting=True,
        **overrides,
    )


def api_items(settings: Settings, omeka: OmekaClient) -> list[OmekaRecord]:
    """All items of the item set.

    The verified listing repeats the read when the pages do not agree.
    A failed page raises an OmekaError. A partial list would skip records.
    """
    records = omeka.list(
        "items",
        filters={"item_set_id": settings.item_set_id},
        per_page=100,
        verify=True,
    )
    return [OmekaRecord.parse(raw) for raw in records]


def api_media(omeka: OmekaClient, item: OmekaRecord) -> list[OmekaRecord]:
    if item.id is None:
        return []
    records = omeka.list("media", filters={"item_id": item.id}, per_page=100)
    return [OmekaRecord.parse(raw) for raw in records]


def snapshot(directory: Path) -> tuple[list[OmekaRecord], list[OmekaRecord]]:
    """The items and media of a snapshot directory.

    The reader prefers a "_transformed" file to a plain file, and a plain file
    to a "_raw" file. It checks the record counts in each manifest.
    """
    data = read_snapshot(directory)
    return (
        [OmekaRecord.parse(raw) for raw in data.items],
        [OmekaRecord.parse(raw) for raw in data.media],
    )


def media_by_item(media: Iterable[OmekaRecord]) -> dict[int, list[OmekaRecord]]:
    grouped: dict[int, list[OmekaRecord]] = defaultdict(list)
    for record in media:
        if record.item_id is not None:
            grouped[record.item_id].append(record)
    return dict(grouped)


def select(items: Iterable[OmekaRecord], ids: set[str]) -> list[OmekaRecord]:
    """The items with a dcterms:identifier in ids."""
    return [item for item in items if item.identifiers() & ids]
