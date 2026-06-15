"""``feinschliff doctor`` — first-run install diagnostic.

Probes the environment for common missing deps and prints plain-English
fixes so the user can resolve issues in ~30 seconds.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DoctorCheck:
    name: str        # short slug, kebab-case
    status: str      # "ok" | "warn" | "fail"
    message: str     # one-line headline
    hint: str | None  # multi-line fix instructions (None for ok)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_python_version() -> DoctorCheck:
    vi = sys.version_info
    major, minor = vi[0], vi[1]
    ok = (major, minor) >= (3, 11)
    if ok:
        micro = vi[2]
        return DoctorCheck("python-version", "ok", f"Python {major}.{minor}.{micro}", None)
    return DoctorCheck(
        "python-version",
        "fail",
        f"Python {major}.{minor} is too old (3.11+ required)",
        "Install Python 3.12 via Homebrew:\n"
        "  brew install python@3.12\n"
        "Then reopen your shell so `python3` resolves to the new version.",
    )


def _check_wheelhouse() -> DoctorCheck:
    data_dir = os.environ.get("DATA_DIR") or os.environ.get("CLAUDE_PLUGIN_DATA", "")
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("PLUGIN_ROOT", "")

    # The launcher (gen_launchers.py) caches the fetched rolling-latest
    # wheelhouse at $DATA_DIR/wheels-latest/wheels/. Check that path first.
    if data_dir:
        rolling = os.path.join(data_dir, "wheels-latest", "wheels")
        if os.path.isdir(rolling):
            whl_files = [f for f in os.listdir(rolling) if f.endswith(".whl")]
            if len(whl_files) >= 5:
                return DoctorCheck(
                    "wheelhouse",
                    "ok",
                    f"Rolling wheelhouse cached ({len(whl_files)} wheels)",
                    None,
                )

    # Check local plugin-root wheels/ fallback (dev / pre-bundled installs).
    if plugin_root:
        local_wheels = os.path.join(plugin_root, "wheels")
        if os.path.isdir(local_wheels):
            whl_files = [f for f in os.listdir(local_wheels) if f.endswith(".whl")]
            if len(whl_files) >= 5:
                return DoctorCheck(
                    "wheelhouse",
                    "ok",
                    f"Local plugin wheelhouse found ({len(whl_files)} wheels)",
                    None,
                )

    # If DATA_DIR is not set at all we're likely in a dev checkout — the
    # wheelhouse is a plugin-install artifact, not needed for development.
    if not data_dir and not plugin_root:
        return DoctorCheck(
            "wheelhouse",
            "warn",
            "DATA_DIR not set; wheelhouse check skipped (dev mode assumed)",
            "The wheelhouse is required for plugin installs only.\n"
            "Set DATA_DIR and CLAUDE_PLUGIN_ROOT when deploying as a plugin.",
        )

    # Try to read the manifest for a helpful URL
    release_hint = ""
    manifest_candidates: list[str] = []
    if plugin_root:
        manifest_candidates.append(os.path.join(plugin_root, "wheels-manifest.json"))
    for candidate in manifest_candidates:
        if os.path.isfile(candidate):
            try:
                manifest = json.loads(open(candidate).read())  # noqa: SIM115
                release_url = manifest.get("release_url") or manifest.get("url") or ""
                if release_url:
                    release_hint = (
                        f"\nDownload the wheels archive from:\n"
                        f"  {release_url}\n"
                        f"Then extract it to the wheelhouse directory and re-run:\n"
                        f"  curl -L {release_url} | tar -xz -C \"$DATA_DIR\""
                    )
            except Exception:
                pass
            break

    return DoctorCheck(
        "wheelhouse",
        "fail",
        "No wheelhouse found (offline wheel cache missing)",
        "The wheelhouse supplies Python packages for plugin installs.\n"
        "Run the plugin's bin/<name> launcher once — it fetches the rolling "
        "wheelhouse from the GitHub release into $DATA_DIR/wheels-latest/wheels/." + release_hint,
    )


def _check_venv_bootstrap() -> DoctorCheck:
    data_dir = os.environ.get("DATA_DIR", "")
    if not data_dir:
        return DoctorCheck(
            "venv-bootstrap",
            "warn",
            "DATA_DIR not set; cannot check venv location",
            "Set DATA_DIR to your data directory so the venv path can be probed.",
        )
    venv_bin = os.path.join(data_dir, "venv", "bin", "feinschliff")
    if os.path.isfile(venv_bin):
        return DoctorCheck("venv-bootstrap", "ok", "Plugin venv is ready", None)
    return DoctorCheck(
        "venv-bootstrap",
        "warn",
        "Plugin venv not yet created",
        "The venv is created automatically on the first `feinschliff` invocation. "
        "Run any feinschliff command to trigger bootstrap.",
    )


def _check_api_key() -> DoctorCheck:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return DoctorCheck("anthropic-api-key", "ok", "ANTHROPIC_API_KEY is set", None)
    return DoctorCheck(
        "anthropic-api-key",
        "warn",
        "ANTHROPIC_API_KEY is not set",
        "LLM-backed features (deck verify, claim-evidence, ghost-deck …) will fail.\n"
        "Add to your shell profile:\n"
        "  export ANTHROPIC_API_KEY=sk-ant-…",
    )


def _check_soffice() -> DoctorCheck:
    if shutil.which("soffice"):
        return DoctorCheck("soffice", "ok", "LibreOffice (soffice) found on PATH", None)
    return DoctorCheck(
        "soffice",
        "warn",
        "soffice not found (LibreOffice missing)",
        "Required for `deck verify` PDF/PNG rendering.\n"
        "Install via Homebrew:\n"
        "  brew install --cask libreoffice",
    )


def _check_pdftoppm() -> DoctorCheck:
    if shutil.which("pdftoppm"):
        return DoctorCheck("pdftoppm", "ok", "pdftoppm found on PATH", None)
    return DoctorCheck(
        "pdftoppm",
        "warn",
        "pdftoppm not found (poppler missing)",
        "Required for PDF → PNG slide rendering.\n"
        "Install via Homebrew:\n"
        "  brew install poppler",
    )


def _check_brand_pack() -> DoctorCheck:
    try:
        from feinschmiede.brand_discovery import find_brand
        find_brand("feinschliff")
        return DoctorCheck("brand-pack", "ok", "Base brand pack 'feinschliff' found", None)
    except ValueError as e:
        return DoctorCheck(
            "brand-pack",
            "fail",
            f"Base brand pack missing: {e}",
            "The 'feinschliff' brand pack was not found on FEINSCHLIFF_BRANDS_PATH.\n"
            "Ensure the pack is installed and that FEINSCHLIFF_BRANDS_PATH (or the\n"
            "default brands/ directory) contains a 'feinschliff' subdirectory.",
        )
    except Exception as e:
        return DoctorCheck(
            "brand-pack",
            "fail",
            f"Brand discovery error: {e}",
            "Check that the feinschmiede package is correctly installed.",
        )


def _check_master_template() -> DoctorCheck:
    try:
        from feinschmiede.master_template import load_catalog  # noqa: F401
        return DoctorCheck(
            "master-template",
            "ok",
            "Master-template renderer available (feinschliff render-master)",
            None,
        )
    except ImportError as e:
        return DoctorCheck(
            "master-template",
            "fail",
            f"Master-template renderer missing: {e}",
            "Reinstall feinschmiede>=0.4 — the master_template module powers\n"
            "`feinschliff render-master` for brand packs that ship a real .pptx master.",
        )


def _check_builder_optional() -> DoctorCheck:
    try:
        import feinschliff_builder  # noqa: F401
        return DoctorCheck(
            "feinschliff-builder-optional",
            "ok",
            "feinschliff-builder is installed. Optional — only needed for authoring new brand packs.",
            None,
        )
    except ImportError:
        return DoctorCheck(
            "feinschliff-builder-optional",
            "ok",
            "feinschliff-builder not installed. Optional — only needed for authoring new brand packs.",
            None,
        )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def run_doctor() -> list[DoctorCheck]:
    """Run all checks and return results (all run; no short-circuit)."""
    return [
        _check_python_version(),
        _check_wheelhouse(),
        _check_venv_bootstrap(),
        _check_api_key(),
        _check_soffice(),
        _check_pdftoppm(),
        _check_brand_pack(),
        _check_master_template(),
        _check_builder_optional(),
    ]


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _is_tty() -> bool:
    return sys.stdout.isatty()


def _prefix(status: str) -> str:
    use_color = _is_tty()
    if status == "ok":
        return "\033[32m[OK]\033[0m" if use_color else "[OK]"
    if status == "warn":
        return "\033[33m[WARN]\033[0m" if use_color else "[WARN]"
    return "\033[31m[FAIL]\033[0m" if use_color else "[FAIL]"


def format_checks(checks: list[DoctorCheck]) -> str:
    lines: list[str] = []
    for c in checks:
        lines.append(f"{_prefix(c.status)}  {c.name}: {c.message}")
        if c.hint:
            for hint_line in c.hint.splitlines():
                lines.append(f"       {hint_line}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------


def cmd_doctor(args) -> int:
    checks = run_doctor()

    if getattr(args, "json", False):
        import json as _json
        payload = [
            {"name": c.name, "status": c.status, "message": c.message, "hint": c.hint}
            for c in checks
        ]
        print(_json.dumps(payload, indent=2))
        return 0

    print(format_checks(checks))

    has_fail = any(c.status == "fail" for c in checks)
    has_warn = any(c.status == "warn" for c in checks)

    if has_fail:
        return 1
    if has_warn:
        return 2
    return 0
