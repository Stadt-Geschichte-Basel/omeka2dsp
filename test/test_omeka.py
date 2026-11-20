import json

import pytest
import requests

from fakes import SETTINGS, response, session
from omeka2dsp.omeka import api_items, media_by_item, select, snapshot
from omeka2dsp.values import OmekaRecord


def item(identifier, o_id=1):
    return {"o:id": o_id, "dcterms:identifier": [{"@value": identifier}]}


def test_snapshot_prefers_transformed(tmp_path):
    (tmp_path / "items_raw.json").write_text(json.dumps([item("raw")]))
    (tmp_path / "items_transformed.json").write_text(json.dumps([item("clean")]))
    (tmp_path / "media_raw.json").write_text(json.dumps([]))
    items, media = snapshot(tmp_path)
    assert [i.identifier for i in items] == ["clean"] and media == []


def test_media_by_item_and_select():
    media = [
        OmekaRecord.parse({"o:id": 10, "o:item": {"o:id": 1}}),
        OmekaRecord.parse({"o:id": 11, "o:item": {"o:id": 2}}),
    ]
    assert media_by_item(media) == {1: [media[0]], 2: [media[1]]}
    items = [OmekaRecord.parse(item("abb1", 1)), OmekaRecord.parse(item("abb2", 2))]
    assert select(items, {"abb2"}) == [items[1]]


def test_items_follow_the_next_link():
    http, transport = session(
        {
            ("GET", "page=2"): response(200, [item("b")]),
            ("GET", "/items"): response(
                200, [item("a")], "https://omeka/api/items?page=2"
            ),
        }
    )
    assert [i.identifier for i in api_items(SETTINGS, http)] == ["a", "b"]
    assert "item_set_id=10780" in transport.sent[0]["url"]


def test_failed_page_stops_the_run():
    http, _ = session(
        {
            ("GET", "page=2"): response(500),
            ("GET", "/items"): response(
                200, [item("a")], "https://omeka/api/items?page=2"
            ),
        }
    )
    with pytest.raises(requests.HTTPError):
        api_items(SETTINGS, http)


def test_omeka_requests_use_the_timeout():
    http, transport = session({("GET", "/items"): response(200, [])})
    api_items(SETTINGS, http)
    assert transport.sent[0]["timeout"] == SETTINGS.http_timeout
