"""Shared brand-pack helpers used by render.py, catalog.py, and clone_plan.py."""
from __future__ import annotations

from pathlib import Path


def norm(name: str) -> str:
    """Normalize layout / placeholder names for tolerant lookup.

    Brand packs ship layout names with typographic quirks the source
    designer typed — non-breaking space (NBSP) between words, trailing
    whitespace, and the like. Users typing the clean name should still
    resolve to the layout the master actually contains.
    """
    return name.replace("\xa0", " ").strip()


def master_path(brand_pack: Path) -> Path:
    """Locate the on-disk master template for a brand pack.

    Three shapes are accepted, in order:
      1. `<brand_pack>/master.pptx`        — the feinschliff convention.
      2. `<brand_pack>/master/master.pptx` — historical (abzug) convention.
      3. `<brand_pack>/master.pptx.ref`    — a text file holding either an
         `http(s)://` URL or a local path to the actual binary. Used by
         gallery / corporate packs whose master lives outside the repo (a
         public R2 bucket, or a local asset directory) so the binary never
         needs to be checked in. URLs are fetched once into a gitignored
         `.master.pptx` cache beside the `.ref`.
    """
    brand_pack = Path(brand_pack)
    for candidate in (brand_pack / "master.pptx", brand_pack / "master" / "master.pptx"):
        if candidate.exists():
            return candidate

    ref = brand_pack / "master.pptx.ref"
    if ref.exists():
        target = ref.read_text().strip()
        if target.startswith(("http://", "https://")):
            return _fetch_cached(target, brand_pack)
        local = Path(target).expanduser()
        if not local.exists():
            raise FileNotFoundError(
                f"master.pptx.ref points to {local}, which does not exist. "
                "Materialize the binary at that path (the pack is expected to "
                "live in a local asset directory, not in this repo)."
            )
        return local

    raise FileNotFoundError(f"no master.pptx (or .ref) found for brand pack {brand_pack}")


def _fetch_cached(url: str, brand_pack: Path) -> Path:
    """Download a `master.pptx.ref` URL once into a gitignored sibling cache.

    Public gallery packs host their master off-repo (so the binary never lands
    in git); the renderer fetches it on demand. The cache is keyed by URL — if
    the `.ref` later points elsewhere, the stale copy is replaced."""
    import urllib.request

    cache = brand_pack / ".master.pptx"
    stamp = brand_pack / ".master.pptx.url"
    if cache.exists() and stamp.exists() and stamp.read_text().strip() == url:
        return cache
    tmp = cache.with_suffix(".tmp")
    # A real User-Agent — Cloudflare's WAF 403s the default `Python-urllib`.
    req = urllib.request.Request(url, headers={"User-Agent": "feinschliff-brand-fetch/1"})
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310 (trusted brand-pack URL)
            tmp.write_bytes(resp.read())
    except Exception as exc:  # network / 404 — surface which pack and URL
        raise FileNotFoundError(
            f"master.pptx.ref for {brand_pack.name} points to {url}, "
            f"which could not be fetched: {exc}"
        ) from exc
    tmp.replace(cache)
    stamp.write_text(url)
    return cache


def index_layouts(prs) -> dict:
    """Build a `{normalized_name: layout}` map. Raise on collisions so a brand
    pack with two layouts that normalize to the same name fails loud instead
    of silently dispatching to whichever one wins the dict-overwrite race."""
    index: dict = {}
    for layout in prs.slide_layouts:
        key = norm(layout.name)
        if key in index:
            raise ValueError(
                f"layout name collision after normalization: {key!r} "
                f"(from {index[key].name!r} and {layout.name!r})"
            )
        index[key] = layout
    return index
