import json

import pytest
from omeka_s_client import OmekaHTTPError, SnapshotError, TransportResponse
from omeka_s_client.testing import FakeOmeka

from fakes import SETTINGS
from omeka2dsp import omeka
from omeka2dsp.omeka import api_items, api_media, media_by_item, select, snapshot
from omeka2dsp.values import OmekaRecord


def item(identifier, o_id=1, item_set=10780):
    return {
        "o:id": o_id,
        "o:item_set": [{"o:id": item_set}],
        "dcterms:identifier": [{"@value": identifier}],
    }


def client(fake, settings=SETTINGS):
    return omeka.client(settings, transport=fake, sleep=lambda _: None)


def test_snapshot_prefers_transformed(tmp_path):
    (tmp_path / "items_raw.json").write_text(json.dumps([item("raw")]))
    (tmp_path / "items_transformed.json").write_text(json.dumps([item("clean")]))
    (tmp_path / "media_raw.json").write_text(json.dumps([]))
    items, media = snapshot(tmp_path)
    assert [i.identifier for i in items] == ["clean"] and media == []


def test_snapshot_checks_the_manifest_counts(tmp_path):
    (tmp_path / "items.json").write_text(json.dumps([item("a")]))
    (tmp_path / "media.json").write_text(json.dumps([]))
    (tmp_path / "snapshot.json").write_text(json.dumps({"items_count": 2}))
    with pytest.raises(SnapshotError):
        snapshot(tmp_path)


def test_media_by_item_and_select():
    media = [
        OmekaRecord.parse({"o:id": 10, "o:item": {"o:id": 1}}),
        OmekaRecord.parse({"o:id": 11, "o:item": {"o:id": 2}}),
    ]
    assert media_by_item(media) == {1: [media[0]], 2: [media[1]]}
    items = [OmekaRecord.parse(item("abb1", 1)), OmekaRecord.parse(item("abb2", 2))]
    assert select(items, {"abb2"}) == [items[1]]


def test_duplicates_map_identifiers_to_omeka_ids():
    records = [
        OmekaRecord.parse(item("abb1", 1)),
        OmekaRecord.parse(item("abb1", 2)),
        OmekaRecord.parse(item("abb2", 3)),
        OmekaRecord.parse(item("", 4)),
        OmekaRecord.parse(item("", 5)),
    ]
    assert omeka.duplicates(records) == {"abb1": [1, 2]}


def test_items_of_the_item_set_on_all_pages():
    records = [item(f"abb{n}", n) for n in range(1, 151)] + [item("other", 999, 1)]
    fake = FakeOmeka({"items": records})
    with client(fake) as omeka_client:
        found = api_items(SETTINGS, omeka_client)
    assert len(found) == 150 and "other" not in {i.identifier for i in found}
    assert all("item_set_id=10780" in r.url for r in fake.requests)


def test_media_of_an_item():
    media = [
        {"o:id": 10, "o:item": {"o:id": 1}},
        {"o:id": 11, "o:item": {"o:id": 2}},
    ]
    with client(FakeOmeka({"media": media})) as omeka_client:
        found = api_media(omeka_client, OmekaRecord.parse(item("abb1", 1)))
    assert [m.id for m in found] == [10]


def test_failed_page_stops_the_run():
    def broken(request):
        return TransportResponse(500)

    with client(broken) as omeka_client, pytest.raises(OmekaHTTPError):
        api_items(SETTINGS, omeka_client)


def test_keys_go_with_each_request():
    fake = FakeOmeka({"items": [item("a")]})
    settings = SETTINGS.model_copy(update={"key_identity": "id", "key_credential": "c"})
    with client(fake, settings) as omeka_client:
        api_items(settings, omeka_client)
    assert all("key_identity=id" in r.url for r in fake.requests)


def test_api_url_without_trailing_slash_keeps_its_path():
    fake = FakeOmeka({"items": []})
    settings = SETTINGS.model_copy(
        update={"omeka_api_url": "https://omeka.test.com/sub/api"}
    )
    with client(fake, settings) as omeka_client:
        api_items(settings, omeka_client)
    assert fake.requests[0].url.startswith("https://omeka.test.com/sub/api/items")
