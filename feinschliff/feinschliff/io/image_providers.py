"""Brand-configurable image provider chain.

Brand packs declare an ordered list of providers in ``tokens.json`` under
``$image_providers`` (plural). The build engine calls
:func:`ProviderChain.resolve` which walks the chain in order, returning the
first hit and logging misses per-provider. All providers are resolved before
falling back, so a slow network provider is tried only after fast local
providers have been exhausted.

Schema (tokens.json)::

    "$image_providers": [
        {"kind": "brand",         "name": "designkit", "root": "$brand_root/assets/designkit"},
        {"kind": "brand",         "name": "eforms",    "root": "$brand_root/assets/eforms"},
        {"kind": "unsplash"},
        {"kind": "llm_websearch"}
    ]

The ``$brand_root`` placeholder in ``root`` is expanded to the brand pack's
directory at resolve time.

Backwards compat
----------------
Brands that still use the old ``$image_provider`` (singular) key continue to
work — the build CLI wraps the single-provider dict into a one-element chain
automatically via :func:`chain_from_brand_config`.
"""
from __future__ import annotations

import json
import os
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from feinschliff.io.image_provider import ImageHit

if TYPE_CHECKING:
    from feinschliff.io.image_provider import ImageProvider


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class ResolutionResult:
    """Returned by :meth:`ProviderChain.resolve` on success."""
    hit: "ImageHit"
    provider_kind: str
    provider_name: str  # e.g. "brand:designkit", "unsplash", "llm_websearch"
    slot_id: str
    query: str


@dataclass
class ProviderMiss:
    """One provider's failed attempt, recorded in the trace."""
    provider_kind: str
    provider_name: str
    reason: str    # human-readable: "no-hit", "search-error", "folder-empty", …
    detail: str = ""


@dataclass
class ResolutionTrace:
    """Returned by :meth:`ProviderChain.resolve` on total failure."""
    query: str
    slot_id: str
    misses: list[ProviderMiss] = field(default_factory=list)

    def format_error(self) -> str:
        lines = [f"image query {self.query!r} (slot {self.slot_id!r}): all providers failed:"]
        for m in self.misses:
            detail = f" — {m.detail}" if m.detail else ""
            lines.append(f"  [{m.provider_name}] {m.reason}{detail}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------

# Image file extensions we accept when scanning brand-folder directories.
_IMG_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".svg", ".gif", ".tiff", ".tif"})

# Tokenise a query: lowercase, collapse non-alnum runs to single space.
_WORD_RE = re.compile(r"[^a-z0-9]+")


def _query_tokens(query: str) -> list[str]:
    return [t for t in _WORD_RE.split(query.lower()) if t]


def _score_filename(filename: str, query_tokens: list[str]) -> int:
    """Simple token-overlap score between a query and an asset filename.

    Each query token that appears as a substring of the lowercased filename
    without extension contributes 1 point. Returns 0 when no tokens match.
    """
    stem = Path(filename).stem.lower()
    stem_words = set(_WORD_RE.split(stem))
    return sum(1 for t in query_tokens if t in stem_words or t in stem)


class BrandFolderProvider:
    """Resolve image queries by scanning a local asset directory.

    Resolution strategy:
    1. Exact filename match (stem == query token-joined, case-insensitive).
    2. Token-overlap scoring — highest score wins.
    3. If tie on score > 0, alphabetically first wins (stable).
    4. If score is 0 for every file, returns ``None`` (no match).

    The directory is scanned lazily on first use; results are cached for
    the lifetime of this instance so repeated queries in a single build
    don't re-scan the filesystem.
    """

    kind = "brand"

    def __init__(self, name: str, root: Path) -> None:
        self._name = name
        self._root = root
        self._files: list[Path] | None = None  # lazy

    @property
    def provider_name(self) -> str:
        return f"brand:{self._name}"

    def _list_files(self) -> list[Path]:
        if self._files is not None:
            return self._files
        if not self._root.is_dir():
            self._files = []
            return self._files
        self._files = sorted(
            p for p in self._root.rglob("*")
            if p.is_file() and p.suffix.lower() in _IMG_SUFFIXES
        )
        return self._files

    def resolve(self, query: str) -> "ImageHit | None":
        """Return the best-match :class:`~feinschliff.io.image_provider.ImageHit`
        from the folder, or ``None`` on miss.
        """
        files = self._list_files()
        if not files:
            return None
        tokens = _query_tokens(query)
        if not tokens:
            return None
        scored = [(f, _score_filename(f.name, tokens)) for f in files]
        best_score = max(s for _, s in scored)
        if best_score == 0:
            return None
        best = min(f for f, s in scored if s == best_score)
        return ImageHit(
            url=best.as_uri(),
            license="internal-brand",
            attribution=f"{self._name}/{best.name}",
            width=None,
            height=None,
            mime=_mime_for_suffix(best.suffix.lower()),
        )


def _mime_for_suffix(suffix: str) -> str:
    return {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
        ".svg": "image/svg+xml", ".gif": "image/gif",
        ".tiff": "image/tiff", ".tif": "image/tiff",
    }.get(suffix, "application/octet-stream")


class UnsplashProviderWrapper:
    """Thin wrapper around the existing
    :class:`feinschliff.io.providers.unsplash.UnsplashProvider`.

    Delegates ``search()`` entirely to the existing implementation so
    all Unsplash retry / stub-mode / API-key logic is reused without
    duplication.
    """

    kind = "unsplash"
    provider_name = "unsplash"

    def __init__(self, config: dict | None = None) -> None:
        from feinschliff.io.providers.unsplash import UnsplashProvider
        self._inner: "ImageProvider" = UnsplashProvider(config)

    def resolve(self, query: str) -> "ImageHit | None":
        hits = self._inner.search(query, count=1)
        return hits[0] if hits else None


class LLMWebSearchProvider:
    """Deferred provider that halts the build and requests human/LLM resolution.

    When this provider is reached in the chain it writes the pending query to
    ``<deck_dir>/.image_provider_queue.jsonl`` and raises
    :class:`LLMResolutionPending` so the build halts with a structured message.

    On the *next* build invocation, :meth:`ProviderChain.resolve` reads
    ``<deck_dir>/.image_provider_resolved.jsonl`` first — any matching slot
    entry is treated as a direct binding override before the chain is walked.
    This lets the orchestrating Claude session act as the LLM-websearch provider
    without coupling feinschmiede to any specific search API.
    """

    kind = "llm_websearch"
    provider_name = "llm_websearch"

    def __init__(self, config: dict | None = None) -> None:
        self._config = config or {}

    def queue(self, slot_id: str, query: str, deck_dir: Path) -> None:
        """Append a pending resolution request to the queue file."""
        queue_path = deck_dir / ".image_provider_queue.jsonl"
        entry = json.dumps({"slot": slot_id, "query": query}, ensure_ascii=False)
        with queue_path.open("a", encoding="utf-8") as fh:
            fh.write(entry + "\n")


class LLMResolutionPending(Exception):
    """Raised when one or more image queries need LLM/human resolution.

    The exception message is human-readable and suitable for display to the
    operator. The ``queue_path`` attribute points to the JSONL queue file.
    """
    def __init__(self, message: str, queue_path: Path) -> None:
        super().__init__(message)
        self.queue_path = queue_path


# ---------------------------------------------------------------------------
# ProviderChain
# ---------------------------------------------------------------------------

class ProviderChain:
    """Walk an ordered list of providers, returning the first hit.

    Build from a list of provider spec dicts (as read from tokens.json
    ``$image_providers``) via :meth:`from_specs`, or use the convenience
    constructor :func:`chain_from_brand_config` which handles both the old
    singular ``$image_provider`` and the new plural ``$image_providers``.
    """

    def __init__(self, providers: list, brand_root: Path | None = None) -> None:
        """
        Parameters
        ----------
        providers:
            List of provider objects (``BrandFolderProvider``,
            ``UnsplashProviderWrapper``, ``LLMWebSearchProvider``, or any
            object with ``.kind``, ``.provider_name``, and ``.resolve(query)``).
        brand_root:
            Brand pack root directory, used for ``$brand_root`` expansion
            (informational; expansion happens at :meth:`from_specs` time).
        """
        self._providers = providers
        self._brand_root = brand_root

    def __len__(self) -> int:
        return len(self._providers)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_specs(
        cls,
        specs: list[dict],
        brand_root: Path | None = None,
    ) -> "ProviderChain":
        """Build a :class:`ProviderChain` from a list of spec dicts.

        Each spec must have a ``kind`` key:
        - ``{"kind": "brand", "name": "...", "root": "..."}``
        - ``{"kind": "unsplash", "config": {...}}``  (``config`` optional)
        - ``{"kind": "llm_websearch"}``

        ``$brand_root`` in ``root`` values is replaced with ``str(brand_root)``
        when brand_root is provided.
        """
        providers = []
        for spec in specs:
            if not isinstance(spec, dict):
                warnings.warn(
                    f"image_providers: ignoring non-dict spec {spec!r}",
                    RuntimeWarning, stacklevel=2,
                )
                continue
            kind = spec.get("kind", "")
            if kind == "brand":
                name = spec.get("name") or "brand"
                raw_root = spec.get("root", "")
                if brand_root is not None:
                    raw_root = raw_root.replace("$brand_root", str(brand_root))
                root = Path(os.path.expandvars(os.path.expanduser(raw_root)))
                providers.append(BrandFolderProvider(name=name, root=root))
            elif kind == "unsplash":
                providers.append(UnsplashProviderWrapper(config=spec.get("config")))
            elif kind == "llm_websearch":
                providers.append(LLMWebSearchProvider(config=spec.get("config")))
            else:
                warnings.warn(
                    f"image_providers: unknown provider kind {kind!r}; skipping.",
                    RuntimeWarning, stacklevel=2,
                )
        return cls(providers, brand_root=brand_root)

    # ------------------------------------------------------------------
    # Resolved-file preload (LLM websearch round-trip)
    # ------------------------------------------------------------------

    @staticmethod
    def _load_resolved(deck_dir: Path) -> dict[str, str]:
        """Read ``<deck_dir>/.image_provider_resolved.jsonl``.

        Returns a dict mapping ``slot_id → local_path`` for every valid
        entry. Malformed lines are skipped with a warning.
        """
        resolved_path = deck_dir / ".image_provider_resolved.jsonl"
        if not resolved_path.is_file():
            return {}
        out: dict[str, str] = {}
        for line_no, raw in enumerate(resolved_path.read_text(encoding="utf-8").splitlines(), 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
                slot = entry["slot"]
                path = entry["path"]
                out[slot] = path
            except (json.JSONDecodeError, KeyError) as exc:
                warnings.warn(
                    f".image_provider_resolved.jsonl line {line_no}: "
                    f"skipping malformed entry ({exc}): {raw[:120]}",
                    RuntimeWarning, stacklevel=2,
                )
        return out

    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def resolve(
        self,
        query: str,
        slot_id: str,
        deck_dir: Path | None,
    ) -> "ResolutionResult | ResolutionTrace":
        """Walk the chain and return the first successful hit.

        On success, returns a :class:`ResolutionResult`.
        On total failure, returns a :class:`ResolutionTrace` (never raises,
        unless ``LLMWebSearchProvider`` is reached — that raises
        :class:`LLMResolutionPending`).

        Pre-step: if ``deck_dir`` is set, check
        ``<deck_dir>/.image_provider_resolved.jsonl`` for a prior LLM
        resolution of this ``slot_id``. If found, bind directly without
        walking the chain.
        """
        # Pre-step: honour previously resolved LLM answers.
        if deck_dir is not None:
            pre = self._load_resolved(deck_dir)
            if slot_id in pre:
                local_path = pre[slot_id]
                hit = ImageHit(
                    url=Path(local_path).as_uri() if not local_path.startswith(("http", "file://")) else local_path,
                    license="llm_websearch",
                    attribution="LLM-resolved",
                    width=None, height=None, mime="",
                )
                return ResolutionResult(
                    hit=hit,
                    provider_kind="llm_websearch",
                    provider_name="llm_websearch",
                    slot_id=slot_id,
                    query=query,
                )

        if not self._providers:
            trace = ResolutionTrace(query=query, slot_id=slot_id)
            trace.misses.append(ProviderMiss(
                provider_kind="chain",
                provider_name="(empty chain)",
                reason="no providers configured",
            ))
            return trace

        trace = ResolutionTrace(query=query, slot_id=slot_id)
        llm_pending_slots: list[tuple[str, str]] = []  # (slot_id, query) pairs

        for provider in self._providers:
            p_kind = getattr(provider, "kind", "unknown")
            p_name = getattr(provider, "provider_name", p_kind)

            if isinstance(provider, LLMWebSearchProvider):
                # Queue this slot for LLM resolution.
                if deck_dir is not None:
                    provider.queue(slot_id, query, deck_dir)
                llm_pending_slots.append((slot_id, query))
                trace.misses.append(ProviderMiss(
                    provider_kind=p_kind,
                    provider_name=p_name,
                    reason="queued for LLM resolution",
                ))
                continue

            try:
                hit = provider.resolve(query)
            except Exception as exc:  # noqa: BLE001
                trace.misses.append(ProviderMiss(
                    provider_kind=p_kind,
                    provider_name=p_name,
                    reason="search-error",
                    detail=f"{type(exc).__name__}: {exc}",
                ))
                warnings.warn(
                    f"image provider {p_name!r} raised on query={query!r}: "
                    f"{type(exc).__name__}: {exc}",
                    RuntimeWarning, stacklevel=2,
                )
                continue

            if hit is None:
                trace.misses.append(ProviderMiss(
                    provider_kind=p_kind,
                    provider_name=p_name,
                    reason="no-hit",
                ))
                continue

            # Success.
            return ResolutionResult(
                hit=hit,
                provider_kind=p_kind,
                provider_name=p_name,
                slot_id=slot_id,
                query=query,
            )

        # All providers exhausted. If LLM slots were queued, raise pending error.
        if llm_pending_slots and deck_dir is not None:
            queue_path = deck_dir / ".image_provider_queue.jsonl"
            n = len(llm_pending_slots)
            raise LLMResolutionPending(
                f"{n} image {'query' if n == 1 else 'queries'} pending LLM resolution; "
                f"see {queue_path}.\n"
                f"Resolve them by writing {deck_dir / '.image_provider_resolved.jsonl'} "
                f"with one {{slot, path}} entry per query (JSONL), then re-run build.",
                queue_path=queue_path,
            )

        return trace


# ---------------------------------------------------------------------------
# Convenience: build a ProviderChain from brand config (handles both old
# singular $image_provider and new plural $image_providers).
# ---------------------------------------------------------------------------

def chain_from_brand_config(
    brand_config: "dict | list | None",
    brand_root: Path | None = None,
) -> "ProviderChain | None":
    """Return a :class:`ProviderChain` from a brand's image provider config.

    Handles three input shapes:
    - ``None`` → ``None`` (no chain; caller should use legacy single-provider path)
    - ``list`` → :meth:`ProviderChain.from_specs`
    - ``dict`` with ``"kind"`` → wrap in a single-element list (backwards compat)

    Returns ``None`` when ``brand_config`` is ``None`` or an empty list so
    callers can fall through to the legacy single-provider code path.
    """
    if brand_config is None:
        return None
    if isinstance(brand_config, list):
        if not brand_config:
            return None
        return ProviderChain.from_specs(brand_config, brand_root=brand_root)
    if isinstance(brand_config, dict) and "kind" in brand_config:
        # Backwards-compat: old $image_provider singleton → one-element chain.
        return ProviderChain.from_specs([brand_config], brand_root=brand_root)
    warnings.warn(
        f"image_providers: unrecognised brand_config shape {type(brand_config).__name__!r}; "
        "expected a list or a dict with 'kind'. Returning None.",
        RuntimeWarning, stacklevel=2,
    )
    return None


__all__ = [
    "BrandFolderProvider",
    "LLMResolutionPending",
    "LLMWebSearchProvider",
    "ProviderChain",
    "ProviderMiss",
    "ResolutionResult",
    "ResolutionTrace",
    "UnsplashProviderWrapper",
    "chain_from_brand_config",
]
