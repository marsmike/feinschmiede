"""Layout-affinity profiles parsed from ``.slide.dsl`` frontmatter.

Every layout carries its picker-affinity profile as a YAML frontmatter
fence at the top of its ``.slide.dsl`` file::

    ---
    role: data-quantity
    ideal_count: [2, 4]
    data_band: kpi          # none | kpi | table | chart
    comparison: false
    narrative_role: ...      # optional
    narrative_act: ...       # optional: situation | complication | resolution
    time_axis_role: ...      # optional: strategic | chronological | tactical
    diagram_complexity: ...  # optional: simple | medium | deep
    variety_exempt: false    # optional, default false
    when_not_to_use:         # optional
      - narrative_role=closing
    ---
    # human-readable header comment continues…
    canvas 1920x1080
    …

The profile lives *next to the layout it describes* — a single source of
truth. :func:`build_profile_table` parses the discovered layout set into the
``{name: profile}`` table consumed by :mod:`feinschliff.layout_picker`,
replacing the old hand-maintained ``_LAYOUTS`` dict. Because the table is
derived from whatever :func:`feinschliff.layout_discovery.discover_layout_paths`
finds, the picker's universe is the on-disk universe by construction — a
layout can never exist on disk yet be unpickable.

The internal profile dict mirrors the keys the picker's scoring loop reads:
``role``, ``ideal_count`` (tuple), ``data``, ``comp``, plus the optional
``narrative_role`` / ``narrative_act`` / ``time_axis_role`` /
``diagram_complexity`` / ``when_not_to_use`` / ``follows_not`` /
``follows_well`` / ``variety_exempt`` fields.
Decompiled brand-pack layouts may additionally carry content metadata —
``fixed_chrome`` (bool), ``chrome_text`` (bool — native chrome draws its
own baked labels), ``description`` (str), ``chrome_subject`` (str),
``when_to_use`` (str — curated positive pick guidance), ``family`` (str —
the slide-type: framing/process/organizational/…), ``element_tree`` (list
of str — one line per slide element in reading order), ``slots`` (per-slot
role/chars/class map), ``image_queries`` (slot → query hint) — which is
passed through verbatim when well-typed and silently omitted otherwise
(type-or-ignore; never required, never validated beyond type).
"""
from __future__ import annotations

from pathlib import Path

import yaml

def split_frontmatter(text: str) -> tuple[str | None, str | None]:
    """Split a ``---\\n...\\n---`` YAML frontmatter fence from a text file.

    Returns ``(frontmatter_text, body_text)``; both are ``None`` when the
    file has no opening ``---`` fence.  The body is padded with blank lines
    so that line numbers in the original file are preserved.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip() != "---":
        return None, None
    for i, line in enumerate(lines[1:], start=1):
        if line.rstrip() == "---":
            fm = "".join(lines[1:i])
            body = "".join([""] * (i + 1) + lines[i + 1:])
            return fm, body
    return None, None


# Declared-value enums (the values a layout may *declare* in its profile).
# Kept local so this module does not import the picker (which imports us).
_VALID_DATA_BANDS = frozenset({"none", "kpi", "table", "chart"})
_VALID_NARRATIVE_ACTS = frozenset({"situation", "complication", "resolution"})
_VALID_TIME_AXIS_ROLES = frozenset({"strategic", "chronological", "tactical"})
_VALID_DIAGRAM_COMPLEXITY = frozenset({"simple", "medium", "deep"})

# Frontmatter key → internal profile key. The picker scoring loop reads the
# internal names (`data`, `comp`); the frontmatter uses the clearer external
# names (`data_band`, `comparison`).
_REQUIRED_KEYS = ("role", "ideal_count", "data_band", "comparison")
_OPTIONAL_STR_KEYS = {
    "narrative_role": "narrative_role",
    "narrative_act": "narrative_act",
    "time_axis_role": "time_axis_role",
    "diagram_complexity": "diagram_complexity",
}


class ProfileError(ValueError):
    """A layout's frontmatter profile is missing or malformed."""


def parse_profile(frontmatter_text: str, *, source: str) -> dict:
    """Parse one frontmatter YAML block into an internal profile dict.

    Raises :class:`ProfileError` with *source* context on any schema
    violation — required key missing, wrong type, or out-of-enum value.
    """
    try:
        raw = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise ProfileError(f"{source}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"{source}: frontmatter must be a YAML mapping")

    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise ProfileError(f"{source}: frontmatter missing required key {key!r}")

    profile: dict = {}

    role = raw["role"]
    if not isinstance(role, str) or not role:
        raise ProfileError(f"{source}: 'role' must be a non-empty string")
    profile["role"] = role

    ideal = raw["ideal_count"]
    if (
        not isinstance(ideal, (list, tuple))
        or len(ideal) != 2
        or not all(isinstance(n, int) for n in ideal)
        or ideal[0] > ideal[1]
    ):
        raise ProfileError(
            f"{source}: 'ideal_count' must be [lo, hi] integers with lo<=hi, got {ideal!r}"
        )
    profile["ideal_count"] = (int(ideal[0]), int(ideal[1]))

    data_band = raw["data_band"]
    if data_band not in _VALID_DATA_BANDS:
        raise ProfileError(
            f"{source}: 'data_band' {data_band!r} not in {sorted(_VALID_DATA_BANDS)}"
        )
    profile["data"] = data_band

    comparison = raw["comparison"]
    if not isinstance(comparison, bool):
        raise ProfileError(f"{source}: 'comparison' must be a boolean, got {comparison!r}")
    profile["comp"] = comparison

    # Optional string-enum fields. Empty/absent → omitted (stays neutral in
    # scoring, matching the legacy "field not present" contract).
    enum_map = {
        "narrative_act": _VALID_NARRATIVE_ACTS,
        "time_axis_role": _VALID_TIME_AXIS_ROLES,
        "diagram_complexity": _VALID_DIAGRAM_COMPLEXITY,
    }
    for fm_key, prof_key in _OPTIONAL_STR_KEYS.items():
        if raw.get(fm_key) in (None, ""):
            continue
        val = raw[fm_key]
        if not isinstance(val, str):
            raise ProfileError(f"{source}: {fm_key!r} must be a string, got {val!r}")
        allowed = enum_map.get(fm_key)
        if allowed is not None and val not in allowed:
            raise ProfileError(
                f"{source}: {fm_key!r} {val!r} not in {sorted(allowed)}"
            )
        profile[prof_key] = val

    wntu = raw.get("when_not_to_use")
    if wntu is not None:
        if not isinstance(wntu, list) or not all(isinstance(r, str) for r in wntu):
            raise ProfileError(f"{source}: 'when_not_to_use' must be a list of strings")
        profile["when_not_to_use"] = wntu

    follows_not = raw.get("follows_not")
    if follows_not is not None:
        if not isinstance(follows_not, list) or not all(isinstance(r, str) for r in follows_not):
            raise ProfileError(f"{source}: 'follows_not' must be a list of strings")
        profile["follows_not"] = follows_not

    follows_well = raw.get("follows_well")
    if follows_well is not None:
        if not isinstance(follows_well, list) or not all(isinstance(r, str) for r in follows_well):
            raise ProfileError(f"{source}: 'follows_well' must be a list of strings")
        profile["follows_well"] = follows_well

    if "variety_exempt" in raw:
        ve = raw["variety_exempt"]
        if not isinstance(ve, bool):
            raise ProfileError(f"{source}: 'variety_exempt' must be a boolean")
        profile["variety_exempt"] = ve

    # Content-metadata passthrough (decompiled brand packs). Optional and
    # tolerant by design — present with the right type → carried through;
    # absent or mistyped → omitted, never an error. The picker's
    # fixed-chrome guard and the /deck planner read these to keep
    # fact-heavy content off layouts whose decoration is carried verbatim.
    for key in ("fixed_chrome", "chrome_text"):
        if isinstance(raw.get(key), bool):
            profile[key] = raw[key]
    for key in ("description", "chrome_subject", "when_to_use", "family",
                "source", "source_hash"):
        val = raw.get(key)
        if isinstance(val, str) and val:
            profile[key] = val
    tree = raw.get("element_tree")
    if (isinstance(tree, list) and tree
            and all(isinstance(e, str) for e in tree)):
        profile["element_tree"] = tree

    # `slots:` (per-slot role/chars/class metadata) and `image_queries`
    # pass through the same tolerant way so deck-build slot auto-binding
    # (feinschliff.deck.content_metadata) can read them off the profile
    # without re-parsing frontmatter. Mistyped entries are dropped.
    slots = raw.get("slots")
    if isinstance(slots, dict):
        well_typed = {
            name: entry for name, entry in slots.items()
            if isinstance(entry, dict)
        }
        if well_typed:
            profile["slots"] = well_typed
    queries = raw.get("image_queries")
    if isinstance(queries, dict):
        well_typed_q = {
            name: q for name, q in queries.items()
            if isinstance(q, str) and q
        }
        if well_typed_q:
            profile["image_queries"] = well_typed_q

    return profile


def load_profile(path: Path) -> dict:
    """Read a ``.slide.dsl`` file and return its internal profile dict.

    Raises :class:`ProfileError` when the file has no frontmatter fence or
    the fence fails validation.

    Drift detection: when the layout's frontmatter declares a
    ``source_hash`` and the actual body's SHA-1 differs, emit a one-line
    warning to stderr. That signal catches layouts whose body was edited
    without re-running ``feinschliff-builder slotify`` — picker metadata
    + visible body are out of sync. Suppress with
    ``FEINSCHLIFF_QUIET_LAYOUT_DRIFT=1``.
    """
    import hashlib as _hashlib
    import os as _os
    import sys as _sys

    text = path.read_text(encoding="utf-8")
    fm, body = split_frontmatter(text)
    if fm is None:
        raise ProfileError(
            f"{path}: no '--- … ---' frontmatter profile. Every layout must "
            f"declare its picker affinity (role / ideal_count / data_band / "
            f"comparison) so the picker can rank it."
        )
    profile = parse_profile(fm, source=str(path))
    declared = profile.get("source_hash")
    if (declared and body is not None
            and not _os.environ.get("FEINSCHLIFF_QUIET_LAYOUT_DRIFT")):
        # split_frontmatter pads the body with blank lines (line-number
        # preservation). lstrip() so fence-size changes don't trip drift.
        actual = _hashlib.sha1(body.strip().encode("utf-8")).hexdigest()[:12]
        if actual != declared:
            print(
                f"layout-drift: {path}: source_hash={declared!r} but body "
                f"hashes to {actual!r}. Re-run `feinschliff-builder slotify "
                f"--brand-pack <pack>` to refresh, or suppress with "
                f"FEINSCHLIFF_QUIET_LAYOUT_DRIFT=1.",
                file=_sys.stderr,
            )
    return profile


def build_profile_table(
    paths: dict[str, Path], *, strict: bool = True
) -> dict[str, dict]:
    """Build the ``{name: profile}`` picker table from discovered layouts.

    *paths* maps layout name → ``.slide.dsl`` path (already resolved for
    source/brand precedence by the caller).

    When *strict* (the default), a missing/invalid profile raises
    :class:`ProfileError` — the toolkit's own layouts must all be pickable.
    When ``strict=False``, an unparseable layout is skipped (it simply won't
    be a pick candidate); used by tolerant runtime callers that would rather
    drop one third-party layout than fail the whole deck build.
    """
    table: dict[str, dict] = {}
    for name, path in paths.items():
        try:
            table[name] = load_profile(path)
        except ProfileError:
            if strict:
                raise
    return table
