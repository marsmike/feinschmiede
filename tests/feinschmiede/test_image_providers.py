"""Tests for feinschmiede.image_providers — ProviderChain + provider classes."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschliff.io.image_providers import (
    BrandFolderProvider,
    LLMResolutionPending,
    LLMWebSearchProvider,
    ProviderChain,
    ProviderMiss,
    ResolutionResult,
    ResolutionTrace,
    UnsplashProviderWrapper,
    chain_from_brand_config,
)


# ---------------------------------------------------------------------------
# BrandFolderProvider
# ---------------------------------------------------------------------------

class TestBrandFolderProvider:
    def test_empty_dir_returns_none(self, tmp_path):
        provider = BrandFolderProvider(name="test", root=tmp_path)
        assert provider.resolve("cooking") is None

    def test_missing_dir_returns_none(self, tmp_path):
        provider = BrandFolderProvider(name="test", root=tmp_path / "nonexistent")
        assert provider.resolve("cooking") is None

    def test_exact_stem_match(self, tmp_path):
        img = tmp_path / "cooking.jpg"
        img.write_bytes(b"fake-image")
        provider = BrandFolderProvider(name="test", root=tmp_path)
        result = provider.resolve("cooking")
        assert result is not None
        assert result.url == img.as_uri()
        assert result.license == "internal-brand"
        assert "cooking.jpg" in result.attribution

    def test_token_overlap_match(self, tmp_path):
        (tmp_path / "smart-home-induction.jpg").write_bytes(b"x")
        (tmp_path / "oven-baking.png").write_bytes(b"x")
        provider = BrandFolderProvider(name="designkit", root=tmp_path)
        result = provider.resolve("induction hob cooking")
        assert result is not None
        # "induction" overlaps with "smart-home-induction.jpg"
        assert "induction" in result.url

    def test_no_token_overlap_returns_none(self, tmp_path):
        (tmp_path / "abstract-pattern.png").write_bytes(b"x")
        provider = BrandFolderProvider(name="test", root=tmp_path)
        result = provider.resolve("kitchen morning sunrise")
        assert result is None

    def test_correct_mime_for_suffix(self, tmp_path):
        (tmp_path / "photo.png").write_bytes(b"x")
        provider = BrandFolderProvider(name="test", root=tmp_path)
        result = provider.resolve("photo")
        assert result is not None
        assert result.mime == "image/png"

    def test_subdirectory_scanning(self, tmp_path):
        sub = tmp_path / "category"
        sub.mkdir()
        img = sub / "landscape.jpg"
        img.write_bytes(b"x")
        provider = BrandFolderProvider(name="test", root=tmp_path)
        result = provider.resolve("landscape")
        assert result is not None
        assert result.url == img.as_uri()


# ---------------------------------------------------------------------------
# UnsplashProviderWrapper
# ---------------------------------------------------------------------------

class TestUnsplashProviderWrapper:
    def test_stub_mode_returns_none(self, monkeypatch):
        # Without UNSPLASH_ACCESS_KEY, UnsplashProvider is in stub mode
        monkeypatch.delenv("UNSPLASH_ACCESS_KEY", raising=False)
        wrapper = UnsplashProviderWrapper()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            result = wrapper.resolve("kitchen sunrise")
        assert result is None

    def test_delegates_to_inner_provider(self, monkeypatch):
        from feinschliff.io.image_provider import ImageHit

        fake_hit = ImageHit(
            url="https://images.unsplash.com/photo-123",
            license="Unsplash License",
            attribution="Test Author on Unsplash",
            width=1920, height=1080,
            mime="image/jpeg",
        )

        def fake_search(query, *, count=1, hints=None):
            return [fake_hit]

        wrapper = UnsplashProviderWrapper()
        monkeypatch.setattr(wrapper._inner, "search", fake_search)
        result = wrapper.resolve("modern kitchen")
        assert result is not None
        assert result.url == fake_hit.url
        assert result.attribution == fake_hit.attribution


# ---------------------------------------------------------------------------
# LLMWebSearchProvider
# ---------------------------------------------------------------------------

class TestLLMWebSearchProvider:
    def test_queue_writes_jsonl(self, tmp_path):
        provider = LLMWebSearchProvider()
        provider.queue("slide-04.image_1", "BSH induction hob", tmp_path)
        queue_path = tmp_path / ".image_provider_queue.jsonl"
        assert queue_path.is_file()
        lines = [json.loads(l) for l in queue_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert lines[0]["slot"] == "slide-04.image_1"
        assert lines[0]["query"] == "BSH induction hob"

    def test_queue_appends_multiple(self, tmp_path):
        provider = LLMWebSearchProvider()
        provider.queue("slot-1", "query-1", tmp_path)
        provider.queue("slot-2", "query-2", tmp_path)
        queue_path = tmp_path / ".image_provider_queue.jsonl"
        lines = [json.loads(l) for l in queue_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# ProviderChain
# ---------------------------------------------------------------------------

class TestProviderChainEmptyChain:
    def test_empty_chain_returns_trace(self, tmp_path):
        chain = ProviderChain(providers=[])
        result = chain.resolve("kitchen", "slot-1", tmp_path)
        assert isinstance(result, ResolutionTrace)
        assert "no providers configured" in result.misses[0].reason

    def test_format_error_is_readable(self, tmp_path):
        chain = ProviderChain(providers=[])
        result = chain.resolve("kitchen", "slot-1", tmp_path)
        assert isinstance(result, ResolutionTrace)
        msg = result.format_error()
        assert "kitchen" in msg
        assert "slot-1" in msg


class TestProviderChainBrandFolder:
    def test_brand_folder_hit_returns_result(self, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir()
        img = assets / "kitchen.jpg"
        img.write_bytes(b"x")

        chain = ProviderChain(providers=[BrandFolderProvider("test", assets)])
        result = chain.resolve("kitchen", "slide-01.image_1", tmp_path)
        assert isinstance(result, ResolutionResult)
        assert result.provider_kind == "brand"
        assert result.hit.url == img.as_uri()

    def test_brand_folder_miss_falls_through_to_trace(self, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir()
        (assets / "abstract.png").write_bytes(b"x")

        chain = ProviderChain(providers=[BrandFolderProvider("test", assets)])
        result = chain.resolve("kitchen sunrise", "slot", tmp_path)
        assert isinstance(result, ResolutionTrace)
        assert len(result.misses) == 1
        assert result.misses[0].provider_kind == "brand"
        assert result.misses[0].reason == "no-hit"

    def test_first_hit_wins_stops_chain(self, tmp_path):
        assets1 = tmp_path / "assets1"
        assets1.mkdir()
        (assets1 / "kitchen.jpg").write_bytes(b"first")

        assets2 = tmp_path / "assets2"
        assets2.mkdir()
        (assets2 / "kitchen.png").write_bytes(b"second")

        chain = ProviderChain(providers=[
            BrandFolderProvider("first", assets1),
            BrandFolderProvider("second", assets2),
        ])
        result = chain.resolve("kitchen", "slot", tmp_path)
        assert isinstance(result, ResolutionResult)
        assert "assets1" in result.hit.url  # first provider wins


class TestProviderChainLLMWebSearch:
    def test_llm_provider_queues_and_raises_pending(self, tmp_path):
        chain = ProviderChain(providers=[LLMWebSearchProvider()])
        with pytest.raises(LLMResolutionPending) as exc_info:
            chain.resolve("BSH induction hob", "slide-04.image_1", tmp_path)
        exc = exc_info.value
        assert "LLM" in str(exc) or "pending" in str(exc).lower()
        assert (tmp_path / ".image_provider_queue.jsonl").is_file()

    def test_llm_provider_no_deck_dir_returns_trace(self):
        """Without deck_dir, LLM provider can't write queue or raise — returns trace."""
        chain = ProviderChain(providers=[LLMWebSearchProvider()])
        # deck_dir=None → can't queue or raise; returns trace with miss recorded
        result = chain.resolve("query", "slot", None)
        assert isinstance(result, ResolutionTrace)
        assert any(m.provider_kind == "llm_websearch" for m in result.misses)

    def test_resolved_file_bypasses_chain(self, tmp_path):
        """Pre-step: .image_provider_resolved.jsonl → bind without walking chain."""
        img = tmp_path / "resolved.jpg"
        img.write_bytes(b"resolved-image")

        resolved_path = tmp_path / ".image_provider_resolved.jsonl"
        resolved_path.write_text(
            json.dumps({"slot": "slide-04.image_1", "path": str(img)}) + "\n"
        )

        # Chain has only an LLM provider — but it should never be reached.
        chain = ProviderChain(providers=[LLMWebSearchProvider()])
        result = chain.resolve("BSH induction hob", "slide-04.image_1", tmp_path)
        assert isinstance(result, ResolutionResult)
        assert result.provider_kind == "llm_websearch"
        assert str(img) in result.hit.url or img.as_uri() == result.hit.url

    def test_resolved_file_partial_only_resolved_slots_bypass(self, tmp_path):
        """Resolved file covers slot-A but not slot-B; slot-B still walks chain."""
        img = tmp_path / "resolved.jpg"
        img.write_bytes(b"x")
        resolved_path = tmp_path / ".image_provider_resolved.jsonl"
        resolved_path.write_text(
            json.dumps({"slot": "slot-A", "path": str(img)}) + "\n"
        )

        chain = ProviderChain(providers=[LLMWebSearchProvider()])
        # slot-A is pre-resolved
        result_a = chain.resolve("query-a", "slot-A", tmp_path)
        assert isinstance(result_a, ResolutionResult)

        # slot-B must walk chain → LLM queues it and raises
        with pytest.raises(LLMResolutionPending):
            chain.resolve("query-b", "slot-B", tmp_path)


class TestProviderChainFromSpecs:
    def test_brand_kind_expands_brand_root(self, tmp_path):
        assets = tmp_path / "assets" / "designkit"
        assets.mkdir(parents=True)
        (assets / "induction.jpg").write_bytes(b"x")

        chain = ProviderChain.from_specs(
            [{"kind": "brand", "name": "designkit", "root": "$brand_root/assets/designkit"}],
            brand_root=tmp_path,
        )
        result = chain.resolve("induction", "slot", tmp_path)
        assert isinstance(result, ResolutionResult)
        assert result.provider_name == "brand:designkit"

    def test_unknown_kind_warns_and_skips(self, tmp_path):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            chain = ProviderChain.from_specs([{"kind": "foobar"}])
        assert any("foobar" in str(warning.message) for warning in w)
        # Unknown kind is skipped → empty chain
        assert len(chain) == 0

    def test_unsplash_kind_creates_wrapper(self):
        chain = ProviderChain.from_specs([{"kind": "unsplash"}])
        assert len(chain) == 1
        assert isinstance(chain._providers[0], UnsplashProviderWrapper)

    def test_llm_websearch_kind_creates_provider(self):
        chain = ProviderChain.from_specs([{"kind": "llm_websearch"}])
        assert len(chain) == 1
        assert isinstance(chain._providers[0], LLMWebSearchProvider)

    def test_full_chain_order(self, tmp_path):
        chain = ProviderChain.from_specs([
            {"kind": "brand", "name": "designkit", "root": str(tmp_path)},
            {"kind": "unsplash"},
            {"kind": "llm_websearch"},
        ], brand_root=tmp_path)
        assert len(chain) == 3
        assert isinstance(chain._providers[0], BrandFolderProvider)
        assert isinstance(chain._providers[1], UnsplashProviderWrapper)
        assert isinstance(chain._providers[2], LLMWebSearchProvider)


# ---------------------------------------------------------------------------
# chain_from_brand_config
# ---------------------------------------------------------------------------

class TestChainFromBrandConfig:
    def test_none_returns_none(self):
        assert chain_from_brand_config(None) is None

    def test_empty_list_returns_none(self):
        assert chain_from_brand_config([]) is None

    def test_singular_dict_wrapped_in_chain(self):
        cfg = {"kind": "unsplash", "config": {"orientation": "landscape"}}
        chain = chain_from_brand_config(cfg)
        assert chain is not None
        assert len(chain) == 1

    def test_list_builds_chain(self, tmp_path):
        specs = [
            {"kind": "brand", "name": "test", "root": str(tmp_path)},
            {"kind": "unsplash"},
        ]
        chain = chain_from_brand_config(specs, brand_root=tmp_path)
        assert chain is not None
        assert len(chain) == 2

    def test_invalid_shape_warns_returns_none(self):
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = chain_from_brand_config("not-a-dict-or-list")
        assert result is None
        assert any("unrecognised" in str(warning.message) for warning in w)


# ---------------------------------------------------------------------------
# ProviderChain.resolve — trace miss message
# ---------------------------------------------------------------------------

class TestResolutionTraceMissMessage:
    def test_trace_format_error_lists_all_providers(self, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir()
        # Empty folder → no matches
        chain = ProviderChain(providers=[
            BrandFolderProvider("test", assets),
        ])
        result = chain.resolve("something-obscure", "slot-X", tmp_path)
        assert isinstance(result, ResolutionTrace)
        msg = result.format_error()
        assert "something-obscure" in msg
        assert "slot-X" in msg
        assert "brand:test" in msg
