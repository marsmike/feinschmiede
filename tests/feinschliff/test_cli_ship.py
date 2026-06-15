import argparse
import json
import subprocess
from pathlib import Path

from feinschliff.cli import ship

REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"


def test_ship_runs_build_verify_quality_and_emits_consolidated_report(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "brand: feinschliff\n"
        f"out: {tmp_path / 'deck.pptx'}\n"
        "slides:\n"
        f"  - layout: {REPO_ROOT / 'brands' / 'feinschliff' / 'layouts' / 'executive-summary.slide.dsl'}\n"
        f"    content_file: {Path(__file__).resolve().parent / 'fixtures' / 'verify_quality' / 'executive-summary-content.yaml'}\n"
    )
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "ship", str(plan), "-o", str(tmp_path / "deck.pptx")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    report_path = tmp_path / "ship_report.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text())
    assert report["verdict"] == "pass"
    assert set(report["gates"]) >= {"build", "verify", "verify-quality"}
    for gate in report["gates"].values():
        assert gate["status"] in {"pass", "skipped"}


def test_tool_prefers_console_script_on_path(monkeypatch):
    monkeypatch.setattr(ship.shutil, "which", lambda name: f"/usr/local/bin/{name}")
    assert ship._tool("feinschliff-builder", "verify", "deck.pptx") == [
        "feinschliff-builder", "verify", "deck.pptx",
    ]


def test_tool_uv_fallback_never_resolves_callers_cwd(monkeypatch):
    monkeypatch.setattr(ship.shutil, "which", lambda name: None)
    cmd = ship._tool("feinschliff-builder", "verify", "deck.pptx")
    assert cmd[:2] == ["uv", "run"]
    assert "--project" in cmd or "--no-project" in cmd
    # Never a bare `uv run <tool>` that lets uv sync the caller's cwd project.
    assert cmd[2] != "feinschliff-builder"
    if "--project" in cmd:
        project = Path(cmd[cmd.index("--project") + 1])
        assert (project / "pyproject.toml").is_file()


def test_ship_skips_gates_when_uv_cannot_spawn_builder(tmp_path, monkeypatch):
    def fake_run(argv, cwd=None):
        if "feinschliff-builder" in argv:
            return 2, "", "error: Failed to spawn: `feinschliff-builder`"
        return 0, "", ""

    monkeypatch.setattr(ship, "_run", fake_run)
    args = argparse.Namespace(
        plan=tmp_path / "plan.yaml", output=tmp_path / "deck.pptx",
        llm=False, json_out=False, examples_out=None,
    )
    assert ship.cmd_ship(args) == 2
    report = json.loads((tmp_path / "ship_report.json").read_text())
    assert report["verdict"] == "incomplete"
    assert report["gates"]["verify"]["status"] == "skipped"
    assert report["gates"]["verify-quality"]["status"] == "skipped"


def test_ship_fails_when_build_aborts(tmp_path):
    plan = tmp_path / "plan.yaml"
    plan.write_text(
        "brand: feinschliff\n"
        f"out: {tmp_path / 'deck.pptx'}\n"
        "slides:\n"
        f"  - layout: {REPO_ROOT / 'brands' / 'feinschliff' / 'layouts' / 'executive-summary.slide.dsl'}\n"
        f"    content_file: {tmp_path / 'does-not-exist.yaml'}\n"
    )
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "ship", str(plan), "-o", str(tmp_path / "deck.pptx")],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert proc.returncode != 0
    report_path = tmp_path / "ship_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        assert report["verdict"] == "fail"
        assert report["gates"]["build"]["status"] == "fail"
