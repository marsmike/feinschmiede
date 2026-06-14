"""`_merge_annotations` preserves operator-curated picker constraints
across re-slotify runs. Without this, manual edits to `when_not_to_use`,
`follows_not`, `follows_well`, and a sticky `variety_exempt: true` get
silently wiped on the next `feinschliff-builder slotify` invocation."""
from __future__ import annotations

from feinschliff_builder.decompile.layout_profile_gen import _merge_annotations


def test_when_not_to_use_survives():
    profile = {"role": "data-comparison"}
    old_fm = (
        "role: data-comparison\n"
        "when_not_to_use: [role=content-columns, role=agenda]\n"
    )
    merged = _merge_annotations(profile, old_fm)
    assert merged["when_not_to_use"] == ["role=content-columns", "role=agenda"]


def test_when_not_to_use_unions_with_classifier():
    # Classifier already proposed one constraint; operator's list adds two more.
    profile = {"role": "chapter-opener",
               "when_not_to_use": ["role=content-columns"]}
    old_fm = (
        "role: chapter-opener\n"
        "when_not_to_use: [role=agenda, role=content-columns, role=closer]\n"
    )
    merged = _merge_annotations(profile, old_fm)
    # Existing + new, no duplicates, classifier order preserved at front.
    assert merged["when_not_to_use"] == [
        "role=content-columns", "role=agenda", "role=closer"]


def test_follows_not_and_follows_well_survive():
    profile = {"role": "closer"}
    old_fm = (
        "role: closer\n"
        "follows_not: [role=cover]\n"
        "follows_well: [role=recommendation]\n"
    )
    merged = _merge_annotations(profile, old_fm)
    assert merged["follows_not"] == ["role=cover"]
    assert merged["follows_well"] == ["role=recommendation"]


def test_variety_exempt_true_is_sticky():
    profile = {"role": "content-columns"}
    old_fm = "role: content-columns\nvariety_exempt: true\n"
    merged = _merge_annotations(profile, old_fm)
    assert merged["variety_exempt"] is True


def test_variety_exempt_false_does_not_force_overwrite():
    profile = {"role": "content-columns"}
    old_fm = "role: content-columns\nvariety_exempt: false\n"
    merged = _merge_annotations(profile, old_fm)
    assert "variety_exempt" not in merged
