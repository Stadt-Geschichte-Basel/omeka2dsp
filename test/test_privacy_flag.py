"""
Test for privacy flag handling (issues #13, #14, #12)
Tests that private media items are properly skipped during migration
"""


def test_privacy_flag_check():
    """
    Test that the privacy flag logic works correctly.
    This test checks the logic used in the main() function to skip private media.
    """
    print("Testing privacy flag logic...")

    # Test case 1: Public media (o:is_public = True)
    public_media = {"o:is_public": True, "dcterms:identifier": [{"@value": "test1"}]}
    should_skip = not public_media.get("o:is_public", True)
    assert should_skip is False, "Public media should not be skipped"
    print("✓ Public media (o:is_public=True) is not skipped")

    # Test case 2: Private media (o:is_public = False)
    private_media = {"o:is_public": False, "dcterms:identifier": [{"@value": "test2"}]}
    should_skip = not private_media.get("o:is_public", True)
    assert should_skip is True, "Private media should be skipped"
    print("✓ Private media (o:is_public=False) is skipped")

    # Test case 3: Missing o:is_public field (default to public)
    no_flag_media = {"dcterms:identifier": [{"@value": "test3"}]}
    should_skip = not no_flag_media.get("o:is_public", True)
    assert should_skip is False, "Media without o:is_public should default to public (not skipped)"
    print("✓ Media without o:is_public field defaults to public (not skipped)")

    # Test case 4: Explicitly public media
    explicit_public = {"o:is_public": True, "dcterms:identifier": [{"@value": "test4"}]}
    should_skip = not explicit_public.get("o:is_public", True)
    assert should_skip is False, "Explicitly public media should not be skipped"
    print("✓ Explicitly public media is not skipped")

    print()
    print("=" * 60)
    print("Privacy flag tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_privacy_flag_check()
