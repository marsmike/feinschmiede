"""Mirrors tests/feinschliff-builder/test_verify_llm_client_guard.py for the
engine-side ``feinschliff.verify.llm.rubric`` module — same gateway contract
(refuse direct api.anthropic.com calls; require ANTHROPIC_BASE_URL).
"""
import sys

import pytest

from feinschliff.verify.llm import rubric


def test_client_missing_anthropic_exits_with_friendly_message(monkeypatch):
    rubric._client.cache_clear()
    monkeypatch.setitem(sys.modules, "anthropic", None)
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    with pytest.raises(SystemExit, match="anthropic library not installed"):
        rubric._client()


def test_client_refuses_when_base_url_missing(monkeypatch):
    pytest.importorskip("anthropic")
    rubric._client.cache_clear()
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-or-test")
    with pytest.raises(SystemExit, match="ANTHROPIC_BASE_URL not set"):
        rubric._client()


def test_client_missing_credential_exits_with_friendly_message(monkeypatch):
    pytest.importorskip("anthropic")
    rubric._client.cache_clear()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="ANTHROPIC_AUTH_TOKEN nor ANTHROPIC_API_KEY"):
        rubric._client()


def test_client_routes_via_gateway_with_auth_token(monkeypatch):
    pytest.importorskip("anthropic")
    rubric._client.cache_clear()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = rubric._client()
    assert str(client.base_url).rstrip("/") == "https://gateway.example.com"


def test_client_routes_via_gateway_with_api_key_fallback(monkeypatch):
    pytest.importorskip("anthropic")
    rubric._client.cache_clear()
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-or-test")
    client = rubric._client()
    assert str(client.base_url).rstrip("/") == "https://gateway.example.com"
