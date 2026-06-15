"""Tests for `feinschliff doctor`."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

import feinschmiede.brand_discovery as _bd  # noqa: F401  # pre-import so patch targets cached module

from feinschliff.cli.doctor import _check_python_version, _check_soffice, _check_brand_pack

REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"


def test_doctor_runs_clean_in_dev_env():
    """Subprocess smoke test: exit 0 or 2; [OK] shown for key checks."""
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "doctor"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # 0 = all OK, 2 = some WARNs but no FAILs
    assert proc.returncode in (0, 2), (
        f"doctor exited {proc.returncode}:\n{proc.stdout}\n{proc.stderr}"
    )
    # python-version must be OK (we're running in a 3.11+ dev env)
    assert "[OK]" in proc.stdout
    assert "python-version" in proc.stdout
    # brand-pack must be OK (feinschliff brand ships with the package)
    assert "brand-pack" in proc.stdout
    # Find the brand-pack line and verify it is OK
    brand_line = next(
        (line for line in proc.stdout.splitlines() if "brand-pack" in line),
        None,
    )
    assert brand_line is not None
    assert "[OK]" in brand_line, f"Expected [OK] for brand-pack, got: {brand_line}"


def test_doctor_reports_python_version():
    """When sys.version_info is patched to (3, 9), python-version must FAIL."""
    import feinschliff.cli.doctor as doctor_mod

    fake_version = (3, 9, 0, "final", 0)

    with patch.object(doctor_mod.sys, "version_info", fake_version):
        check = _check_python_version()

    assert check.status == "fail"
    assert "3.9" in check.message
    assert check.hint is not None
    assert "brew install python@3.12" in check.hint


def test_doctor_handles_missing_soffice():
    """When shutil.which returns None for soffice, the check must WARN with the brew hint."""
    import feinschliff.cli.doctor as doctor_mod

    orig_which = shutil.which

    def fake_which(name):
        if name == "soffice":
            return None
        return orig_which(name)

    with patch.object(doctor_mod.shutil, "which", fake_which):
        check = _check_soffice()

    assert check.status == "warn"
    assert check.hint is not None
    assert "brew install --cask libreoffice" in check.hint


def test_doctor_handles_missing_brand_pack():
    """When find_brand raises ValueError, brand-pack must FAIL."""
    # Patch at the module level used by the local `from ... import` inside
    # _check_brand_pack so no fresh import occurs during the test.
    with patch(
        "feinschmiede.brand_discovery.find_brand",
        side_effect=ValueError("brand not found: feinschliff"),
    ):
        check = _check_brand_pack()

    assert check.status == "fail"
    assert check.hint is not None


def test_doctor_json_output():
    """--json flag must emit a parseable JSON array with the expected check names."""
    proc = subprocess.run(
        ["uv", "run", "feinschliff", "doctor", "--json"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    # Accept any exit code — JSON must still be valid regardless
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        pytest.fail(f"doctor --json output is not valid JSON: {exc}\n{proc.stdout}")

    assert isinstance(data, list)
    names = {item["name"] for item in data}
    expected = {
        "python-version",
        "wheelhouse",
        "venv-bootstrap",
        "anthropic-api-key",
        "soffice",
        "pdftoppm",
        "brand-pack",
        "master-template",
        "feinschliff-builder-optional",
    }
    assert expected == names, f"Check name mismatch: {names}"

    # Each item must have the required keys
    for item in data:
        assert "name" in item
        assert "status" in item
        assert item["status"] in ("ok", "warn", "fail")
        assert "message" in item
        assert "hint" in item  # may be null
