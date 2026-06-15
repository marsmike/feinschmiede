"""Engine-side ``feinschliff.verify.llm.rubric`` contract:
verify never constructs an LLM client and never calls one. The
orchestrating Claude in the active session is the judge.

Mirror in ``tests/feinschliff-builder/test_verify_llm_client_guard.py``
for the builder-side rubric.
"""
import pytest

from feinschliff.verify.llm import rubric


def test_client_always_raises_regardless_of_env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://gateway.example.com")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "tok-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-or-test")
    with pytest.raises(SystemExit, match="does not construct an LLM client"):
        rubric._client()


def test_client_raises_when_env_completely_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_BASE_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit, match="orchestrating Claude is the judge"):
        rubric._client()


def test_judge_always_raises_and_points_at_prompt_artifact_contract():
    with pytest.raises(SystemExit, match="needs-orchestrator-judgment"):
        rubric._judge("anything")
