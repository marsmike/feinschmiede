"""BrandPack — typed domain object for a feinschliff brand directory.

Replaces the legacy `Brand` dataclass from `feinschmiede.brand_discovery`. A BrandPack
loads and caches `tokens.json`, provides token resolution by dotted path, and
delegates layout/compound discovery to the toolkit's discovery layer.

Usage::

    pack = BrandPack.load(Path("brands/feinschliff"))
    hex_color = pack.resolve_token("color.accent")   # "#C9A24A"
    compound = pack.find_compound("footer")          # FoundCompound or None

    # Theme-aware loading (new):
    theme = pack.theme("claude")                     # ThemePack
    theme = pack.default_theme                       # ThemePack for the default
    resolved = theme.tokens                          # merged Tokens (brand + theme)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FoundCompound:
    name: str
    path: Path
    origin: str  # "brand-local" | "toolkit"


# ---------------------------------------------------------------------------
# ThemePack
# ---------------------------------------------------------------------------

class ThemePack:
    """A color/font variant of a BrandPack.

    Resolved tokens = deep_merge(brand.tokens, theme.tokens). When the brand
    has no ``themes/`` directory, a synthetic ThemePack is created pointing at
    the brand's own ``tokens.json`` (so unmigrated packs work unchanged).

    Parameters are private; use ``BrandPack.theme(name)`` or
    ``BrandPack.default_theme`` to obtain instances.
    """

    def __init__(
        self,
        brand: "BrandPack",
        name: str,
        theme_root: Path | None,
        *,
        synthetic: bool = False,
    ) -> None:
        self._brand = brand
        self._name = name
        self._theme_root = theme_root
        self._synthetic = synthetic
        self._tokens_cache: Any | None = None

    @property
    def name(self) -> str:
        """Theme name, e.g. ``'default'`` or ``'claude'``."""
        return self._name

    @property
    def brand(self) -> "BrandPack":
        return self._brand

    @property
    def theme_root(self) -> Path | None:
        """Path to the theme directory (``themes/<name>/``), or None for synthetic."""
        return self._theme_root

    @property
    def tokens_path(self) -> Path | None:
        """Path to the theme's tokens.json, or None for synthetic."""
        if self._theme_root is None:
            return None
        p = self._theme_root / "tokens.json"
        return p if p.is_file() else None

    @property
    def tokens(self) -> Any:
        """Resolved Tokens (brand-level deep-merged with theme tokens).

        Lazily computed and cached. For synthetic themes (no ``themes/``
        directory), delegates to the brand's own token loading.
        """
        if self._tokens_cache is None:
            self._tokens_cache = self._resolve_tokens()
        return self._tokens_cache

    def _resolve_tokens(self) -> Any:
        from feinschmiede.dsl.tokens import load_tokens, Tokens
        from feinschmiede.jsonwalk import deep_merge

        if self._synthetic:
            # No themes/ — just load the brand tokens (extends chain already resolved)
            return load_tokens(self._brand.root)

        theme_tj = self._theme_root / "tokens.json" if self._theme_root else None
        if theme_tj is None or not theme_tj.is_file():
            return load_tokens(self._brand.root)

        # Brand tokens (resolves extends chain) then deep-merge theme on top.
        # We use load_tokens on brand root for the base (schema-validated, extends-resolved).
        # Then deep-merge the theme's raw tokens.json on top, and re-validate.
        brand_merged = load_tokens(self._brand.root)
        theme_raw = json.loads(theme_tj.read_bytes())
        combined = deep_merge(brand_merged.raw, theme_raw)
        # Re-validate the combined result against the schema.
        from feinschmiede.dsl.tokens import validate_tokens
        validate_tokens(combined, f"{self._brand.name}:{self._name}")
        return Tokens(raw=combined, brand_name=f"{self._brand.name}:{self._name}")

    @property
    def tokens_hash(self) -> str:
        """12-char SHA-1 of the combined (brand + theme) token bytes.

        Used as the diagram cache key. Two themes of the same brand produce
        different hashes. For synthetic themes, equals the brand's tokens_hash.
        """
        if self._synthetic:
            return self._brand.tokens_hash
        brand_tj = self._brand.root / "tokens.json"
        theme_tj = self._theme_root / "tokens.json" if self._theme_root else None
        h = hashlib.sha1()
        if brand_tj.is_file():
            h.update(brand_tj.read_bytes())
        if theme_tj is not None and theme_tj.is_file():
            h.update(theme_tj.read_bytes())
        return h.hexdigest()[:12]

    def __repr__(self) -> str:
        return f"ThemePack(brand={self._brand.name!r}, theme={self._name!r})"


# ---------------------------------------------------------------------------
# BrandPack
# ---------------------------------------------------------------------------

class BrandPack:
    """Typed domain object representing a brand pack directory.

    Parameters are private; use `BrandPack.load(root)` to construct.
    """

    def __init__(
        self,
        root: Path,
        tokens: dict[str, Any],
        tokens_hash: str,
        *,
        image_provider_config: dict | None = None,
    ) -> None:
        self._root = root
        self._tokens = tokens
        self._tokens_hash = tokens_hash
        self._image_provider_config = image_provider_config
        self._themes_cache: dict[str, ThemePack] | None = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, root: Path) -> "BrandPack":
        """Load a BrandPack from a brand directory.

        Parameters
        ----------
        root:
            Path to the brand directory (must contain `tokens.json`).

        Raises
        ------
        FileNotFoundError
            When `tokens.json` is absent.
        """
        tokens_path = root / "tokens.json"
        if not tokens_path.is_file():
            raise FileNotFoundError(
                f"BrandPack.load: {root!r} has no tokens.json"
            )
        raw_bytes = tokens_path.read_bytes()
        tokens = json.loads(raw_bytes)
        tokens_hash = hashlib.sha1(raw_bytes).hexdigest()[:12]
        return cls(root=root, tokens=tokens, tokens_hash=tokens_hash)

    # ------------------------------------------------------------------
    # Identity
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Brand directory name, e.g. ``'feinschliff'``."""
        return self._root.name

    # Alias kept for test parity with Brand.name
    @property
    def name(self) -> str:
        return self._root.name

    @property
    def root(self) -> Path:
        return self._root

    @property
    def tokens(self) -> dict[str, Any]:
        return self._tokens

    @property
    def tokens_hash(self) -> str:
        """12-char SHA-1 hex of tokens.json bytes."""
        return self._tokens_hash

    # ------------------------------------------------------------------
    # Sub-paths
    # ------------------------------------------------------------------

    @property
    def layouts_path(self) -> Path | None:
        """Brand-local layouts/ directory, or None when absent."""
        p = self._root / "layouts"
        return p if p.is_dir() else None

    @property
    def compounds_path(self) -> Path | None:
        """Brand-local compounds/ directory, or None when absent."""
        p = self._root / "compounds"
        return p if p.is_dir() else None

    # Convenience for callers that expect a direct Path (mirroring Brand)
    @property
    def tokens_path(self) -> Path | None:
        """Path to tokens.json if present."""
        p = self._root / "tokens.json"
        return p if p.is_file() else None

    @property
    def design_path(self) -> Path | None:
        """Path to DESIGN.md if present (carried by brand packs for human-readable design notes)."""
        p = self._root / "DESIGN.md"
        return p if p.is_file() else None

    # ------------------------------------------------------------------
    # Theme discovery
    # ------------------------------------------------------------------

    @property
    def _themes_dir(self) -> Path | None:
        p = self._root / "themes"
        return p if p.is_dir() else None

    def _build_themes(self) -> dict[str, ThemePack]:
        themes_dir = self._themes_dir
        if themes_dir is None:
            # No themes/ — synthesize a single "default" theme pointing at
            # the brand root's own tokens.json (back-compat for unmigrated packs).
            return {"default": ThemePack(self, "default", None, synthetic=True)}
        result: dict[str, ThemePack] = {}
        for entry in sorted(themes_dir.iterdir()):
            if entry.is_dir() and (entry / "tokens.json").is_file():
                result[entry.name] = ThemePack(self, entry.name, entry)
        if not result:
            # themes/ exists but is empty — treat same as absent
            return {"default": ThemePack(self, "default", None, synthetic=True)}
        return result

    @property
    def themes(self) -> dict[str, ThemePack]:
        """All themes for this brand, keyed by theme name.

        For brands without a ``themes/`` directory, returns ``{"default": <synthetic>}``.
        """
        if self._themes_cache is None:
            self._themes_cache = self._build_themes()
        return self._themes_cache

    @property
    def default_theme_name(self) -> str:
        """The default theme name, declared in tokens.json as ``$default_theme``.

        Falls back to ``"default"`` when absent.
        """
        declared = self._tokens.get("$default_theme")
        if isinstance(declared, str) and declared:
            return declared
        return "default"

    @property
    def default_theme(self) -> ThemePack:
        """The brand's default ThemePack."""
        name = self.default_theme_name
        themes = self.themes
        if name in themes:
            return themes[name]
        # Fallback: first theme alphabetically
        first = next(iter(themes.values()))
        return first

    def theme(self, name: str) -> ThemePack:
        """Return a named ThemePack, or raise ValueError with available themes.

        Parameters
        ----------
        name:
            Theme name, e.g. ``'default'``, ``'claude'``.

        Raises
        ------
        ValueError
            When the theme is not found for this brand.
        """
        themes = self.themes
        if name in themes:
            return themes[name]
        available = sorted(themes.keys())
        raise ValueError(
            f"theme '{name}' not found for brand '{self.name}'. "
            f"Available themes: {', '.join(available)}"
        )

    # ------------------------------------------------------------------
    # Token resolution
    # ------------------------------------------------------------------

    def resolve_token(self, dotted_path: str) -> Any | None:
        """Resolve a dotted key path against tokens.json.

        Example::

            pack.resolve_token("color.accent")   # "#C9A24A" or {"$value": "#C9A24A"}
            pack.resolve_token("missing.key")     # None

        Supports both bare strings and Design-Tokens ``{"$value": "..."}``
        objects at the leaf. Always returns the raw leaf value (not
        unwrapped) so callers can decide how to interpret $value wrappers.
        For plain hex extraction use ``brand_bridge.resolve()`` instead.
        """
        parts = dotted_path.split(".")
        node: Any = self._tokens
        for part in parts:
            if not isinstance(node, dict):
                return None
            if part not in node:
                return None
            node = node[part]
        return node

    # ------------------------------------------------------------------
    # Layout discovery
    #
    # NOTE: layout discovery (``find_layout`` / ``layout_table``) lived here
    # but pulled in ``feinschliff.layout_discovery`` — an engine→office
    # back-edge. The brand-local ``layouts_path`` (below) is the engine's
    # only layout responsibility; the toolkit-overlay precedence now lives
    # on the office side (``feinschliff.deck.picker``).
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Compound discovery
    # ------------------------------------------------------------------

    def find_compound(self, name: str) -> FoundCompound | None:
        """Locate a compound DSL file.

        Brand-local `compounds/` wins over toolkit bundled compounds.

        Parameters
        ----------
        name:
            Compound name, e.g. ``'footer'`` (without `.dsl`).

        Returns
        -------
        FoundCompound | None
        """
        # 1. Brand-local compounds/
        if self.compounds_path is not None:
            candidate = self.compounds_path / f"{name}.dsl"
            if candidate.is_file():
                return FoundCompound(name=name, path=candidate, origin="brand-local")
        # 2. Engine-bundled compounds/ (shipped inside the feinschmiede package)
        toolkit_compounds = Path(__file__).resolve().parents[1] / "compounds"
        candidate = toolkit_compounds / f"{name}.dsl"
        if candidate.is_file():
            return FoundCompound(name=name, path=candidate, origin="toolkit")
        return None

    # ------------------------------------------------------------------
    # Image provider config (extends-resolved, set by discover_brands)
    # ------------------------------------------------------------------

    @property
    def image_provider_config(self) -> dict | None:
        """Extends-resolved ``$image_provider`` block from tokens.json.

        None when the brand (and none of its parents) declares a provider.
        Set externally by ``discover_brands`` so the extends-walk logic
        stays in one place.
        """
        return self._image_provider_config

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"BrandPack(id={self.id!r}, root={self._root!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BrandPack):
            return NotImplemented
        return self._root == other._root and self._tokens_hash == other._tokens_hash

    def __hash__(self) -> int:
        return hash((self._root, self._tokens_hash))
