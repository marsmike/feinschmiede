# Installation

This page lists everything an end-user needs to install before any of
the `feinschmiede` plugins (`feinschliff`, `feinbild`, `feinklang`,
`feinschnitt`) will run. If you only use one plugin, skim to its row
in the table below.

Plugins install via Claude Code's plugin marketplace:

```bash
/plugin marketplace add marsmike/feinschmiede
/plugin install feinschliff@feinschmiede
```

The first time you invoke a plugin (e.g. `/deck "..."`), its `bin/`
launcher fetches a per-Python wheelhouse from the [rolling `latest`
release](https://github.com/marsmike/feinschmiede/releases/tag/latest),
builds a private venv under `~/.local/share/feinschmiede/<plugin>/`,
and execs the real CLI. Subsequent runs reuse the cached venv. The
launcher uses HTTP conditional GETs (`curl -z`) so it only
re-downloads when the upstream tarball changed.

## Prerequisites — system tools

| Tool | Required by | Install (macOS) | Install (Debian/Ubuntu) |
|---|---|---|---|
| **Python ≥ 3.11** | every plugin | `brew install python@3.12` | `apt-get install python3.12` |
| **`uv`** (preferred) | every plugin's launcher | `brew install uv` | <https://docs.astral.sh/uv/getting-started/installation/> |
| **`soffice`** (LibreOffice) | `feinschliff` (PDF/PNG verify renders) | `brew install --cask libreoffice` | `apt-get install libreoffice` |
| **`pdftoppm`** (Poppler) | `feinschliff` (verify PNGs) | `brew install poppler` | `apt-get install poppler-utils` |
| **`ffmpeg`** | `feinschnitt` (`/edit`, `/record`) | `brew install ffmpeg` | `apt-get install ffmpeg` |
| **Node + npm** | `feinschnitt` `/video` (Remotion) | `brew install node` | `apt-get install nodejs npm` |
| **`asciinema`** | `feinschnitt` `/record` | `brew install asciinema` | `apt-get install asciinema` |

macOS users: the system `/usr/bin/python3` is 3.9.6 and is **too old**.
The launcher probes for `python3.13`, `python3.12`, `python3.11`
explicitly and only falls back to `python3` if it is ≥ 3.11. After a
fresh Homebrew install, restart your shell so the new interpreter is on
PATH.

## API keys — what each plugin needs

The marketplace install is free. The plugins call paid third-party APIs
for LLM judgment, voice synthesis, and image generation. **No key is
needed for the deterministic parts** (deck rendering, DSL → PPTX, brand
chrome, slot validation, layout picking, diagram compile). Keys are
only checked when their feature actually runs.

| Plugin | Required for | Key | Get one at |
|---|---|---|---|
| `feinbild` | `/imagine` — pick **one** of: | `REPLICATE_API_KEY` **or** `GEMINI_API_KEY` | <https://replicate.com/account/api-tokens> · <https://aistudio.google.com/apikey> |
| `feinklang` | `/tts` | `ELEVENLABS_API_KEY` | <https://elevenlabs.io/app/settings/api-keys> |
| `feinschnitt` | `/edit` (Gemini transcript analyze) | `GEMINI_API_KEY` | <https://aistudio.google.com/apikey> |
| `feinschnitt` | `/video` (Remotion voiceover, optional) | `ELEVENLABS_API_KEY` | <https://elevenlabs.io/app/settings/api-keys> |

`feinbild`'s diagram skills (`/excalidraw`, `/svg`) are pure-deterministic
and need no API key. `feinschliff` itself is deterministic and needs no
API key — the renderer fills a brand-authored `master.pptx` from
`FillPlan` / `ClonePlan` entries; the optional LLM judgment lives in
sibling plugins and reads its key the same way.

## Where to put your keys

### Option A — `~/.env` file (recommended)

Every plugin (`feinschliff`, `feinklang`, `feinschnitt`, `feinbild`)
calls a small `load_home_env()` helper at CLI startup that reads
`~/.env` and populates `os.environ` for any key not already exported.
Format:

```sh
# ~/.env — one KEY=value per line. Lines may use `export KEY=value`.
# Lines starting with # are ignored.

ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=sk_...
GEMINI_API_KEY=AIza...
REPLICATE_API_KEY=r8_...
```

- Always set on the user's home directory (`~/.env`).
- Quotes around the value are stripped if the first and last char match.
- An **already-set** environment variable always wins — the file never
  overrides an exported variable.
- Keep this file out of git. The repo's root `.gitignore` already
  ignores `.env` and `.env.local`, but a user's home directory is your
  responsibility — never commit `~/.env`.

This is the same mechanism used by every plugin in this suite. There
is no separate `~/.config/feinschmiede/` directory; the load is from
your home.

### Option B — shell profile

If you prefer to export keys at shell startup (`~/.zshrc`,
`~/.bashrc`, `~/.profile`), do that instead. The plugins inherit the
environment from whatever process spawned them — typically Claude
Code, which inherits from your shell.

```sh
# ~/.zshrc
export ANTHROPIC_API_KEY="sk-ant-..."
```

After editing, **restart your terminal** (or `source ~/.zshrc`) so the
exported value is visible to the next process you launch. Claude Code
runs the plugin launcher in a non-login subshell — it does not re-read
`~/.zshrc` for you.

### Option C — Claude Code settings

You can also set environment variables in Claude Code's
`settings.json`:

```jsonc
// ~/.claude/settings.json
{
  "env": {
    "ANTHROPIC_API_KEY": "sk-ant-..."
  }
}
```

Claude Code injects these into every tool / subprocess it spawns,
including the plugin launchers. Useful when you want a key to apply
**only** while Claude Code is running. The value lands in the env of
the launcher subprocess, so the plugin sees it the same as Option A or
Option B.

### Option D — per-call shell prefix

For one-off use, prefix the slash command's underlying CLI:

```bash
ELEVENLABS_API_KEY=sk_... feinklang voices
```

This only works from a shell, not from inside Claude Code.

### What about Windows?

The plugin launchers are bash scripts (`bin/<plugin>`) and assume a
POSIX shell. On Windows you need WSL2 or Git Bash. Inside WSL2,
`~/.env` lives at your Linux home (`/home/<you>/.env`), not your
Windows profile. The same loader picks it up.

## Verification

After installation, run a smoke render. The `feinschliff` launcher is
a venv-Python shim — it execs `python "$@"` once the bundled wheelhouse
is provisioned, so a one-liner that imports the public surface and
exits 0 confirms the install:

```bash
feinschliff -c "from feinschliff import FillPlan, render; print('ok')"
```

If you see `ok`, the wheelhouse fetched, the venv built, and the
public surface imports. First run prints the provisioning steps to
stderr; subsequent runs are instant.

For sibling plugins, invoke their CLI's bare help:

```bash
feinbild --help
feinklang --help
feinschnitt --help
```

Each launcher shares the same bootstrap path, so a working `--help`
confirms the install.

## Troubleshooting

### `no wheelhouse URL for py39 in wheels-manifest.json`

Your `python3` resolves to Python 3.9 (macOS default). Install Python
3.11+ via Homebrew and restart your shell. The launcher will find
`python3.12` (or higher) automatically.

### `wheelhouse not available locally and could not be fetched`

Network blocked or GitHub releases unavailable. Manual install:

```bash
curl -fL https://github.com/marsmike/feinschmiede/releases/download/latest/feinschliff-wheels-py312.tar.gz \
  | tar xz -C ~/.local/share/feinschmiede/feinschliff/wheels-latest/wheels
```

### `[FAIL]  brand-pack: Base brand pack 'feinschliff' not found`

The plugin install is incomplete — either `FEINSCHLIFF_BRAND_PATH` is
set to a wrong directory, or the marketplace install corrupted. Try:

```bash
/plugin uninstall feinschliff@feinschmiede
/plugin install feinschliff@feinschmiede
```

### `Error: ELEVENLABS_API_KEY environment variable is not set`

You ran `/tts` without a key. Add it to `~/.env` (Option A above) or
export it in your shell.

### `GEMINI_API_KEY not set in ~/.env`

Same as above for `/edit` (feinschnitt).

