from language_core.grammar import profile_from_mapping


def test_profile_from_mapping_keeps_strict_defaults() -> None:
    profile = profile_from_mapping(
        "strict",
        {"profile_key": "strict", "index_base": 0, "require_semicolons": False},
    )
    assert profile.name == "strict"
    assert profile.index_base == 0
    assert profile.require_semicolons is False
    assert profile.max_instructions == 100_000

    base = profile_from_mapping("strict", {"index_base": 4})
    assert base.index_base == 1
