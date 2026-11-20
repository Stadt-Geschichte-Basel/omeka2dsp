from omeka2dsp.fields import FIELDS, MEDIA, PARENT, Kind, Project, fields_for


def test_each_property_has_one_row():
    props = [field.prop for field in FIELDS]
    assert len(props) == len(set(props))


def test_list_fields_have_a_list_key():
    for field in FIELDS:
        assert (field.kind is Kind.LIST) == (field.list_key is not None)


def test_parent_and_media_fields():
    parent = {field.prop for field in fields_for(PARENT)}
    assert "isPartOf" in parent and "hasCreator" not in parent
    for media_class in MEDIA:
        props = {field.prop for field in fields_for(media_class)}
        assert "linkToParentObject" in props and "isPartOf" not in props


def test_project_names():
    project = Project(iri="p", shortcode="0001", ontology_name="SGB", ontology_iri="o")
    assert project.name("hasTitle") == "SGB:hasTitle"
    assert project.local("SGB:Parent") == "Parent"
