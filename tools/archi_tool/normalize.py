"""Normalize a .archimate file through the headless Archi CLI.

Archi is the canonical serializer: a load + save roundtrip rewrites the file
exactly as Archi itself would, so git diffs stay small regardless of whether
the last edit came from this tool or from the Archi GUI. A throwaway
workspace (-data) avoids lock conflicts with a running Archi GUI.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .model import ModelError

ARCHI_CANDIDATES = [
    "/Applications/Archi.app/Contents/MacOS/Archi",   # macOS
    r"C:\Program Files\Archi\Archi.exe",              # Windows (winget/inno, machine scope)
    # Windows Inno installer without admin rights falls back to user scope;
    # %LOCALAPPDATA% stays unexpanded (and never matches) on other platforms
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Archi\Archi.exe"),
    "/opt/Archi/Archi",                               # Linux tgz
]


def find_archi_binary():
    """Locate an already-available Archi binary. Returns None if none is
    found; fetching a cached copy is handled separately by normalize()."""
    override = os.environ.get("ARCHI_APP")
    if override:
        # an explicit override must not silently fall through to defaults
        return override if os.path.exists(override) else None
    for candidate in ARCHI_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    # a previously downloaded engine in the per-user cache, before any PATH
    # lookup, so a fetched engine always wins
    from .engine import cached_binary
    cached = cached_binary()
    if cached:
        return str(cached)
    on_path = shutil.which("Archi")
    # on case-insensitive filesystems (macOS, Windows) which("Archi") can match
    # our own `archi` entry point; reject it so we never drive ourselves
    if on_path and not _is_own_entry_point(on_path):
        return on_path
    return None


def _is_own_entry_point(path) -> bool:
    """True when ``path`` is this package's own `archi` CLI rather than the
    real Archi desktop app (a case-insensitive PATH collision)."""
    ours = shutil.which("archi")
    if ours and os.path.exists(ours) and os.path.exists(path):
        return os.path.samefile(ours, path)
    return False


def normalize(path, *, download=True) -> None:
    binary = find_archi_binary()
    if not binary and download:
        # nothing installed and downloading is allowed: fetch the pinned
        # engine into the per-user cache (once), then use it
        from .engine import download_engine
        binary = str(download_engine())
    if not binary:
        raise ModelError(
            "Archi niet gevonden. Haal de engine op met `archi setup`, "
            "installeer Archi zelf (macOS: brew install --cask archi; "
            "Windows: winget install --id Archi.Archi -e), of zet de env var "
            "ARCHI_APP naar het pad van de Archi-binary.")
    absolute = os.path.abspath(path)
    with tempfile.TemporaryDirectory() as workspace:
        result = subprocess.run(
            [binary, "-application", "com.archimatetool.commandline.app",
             "-consoleLog", "-nosplash", "-data", workspace,
             "--loadModel", absolute, "--saveModel", absolute],
            capture_output=True, text=True)
    if result.returncode != 0:
        output = result.stdout + result.stderr
        if "gtk_init_check" in output or "No more handles" in output:
            # Archi's command-line app still needs an X display on Linux; on a
            # headless host it must run under a virtual framebuffer
            raise ModelError(
                "Archi kon geen X-display openen (headless Linux). Draai "
                "normalize onder een virtueel scherm, bijvoorbeeld:\n"
                "  xvfb-run -a archi normalize\n"
                "(installeer xvfb, bv. `apt-get install xvfb`). Op een "
                "desktop met display is dit niet nodig.")
        raise ModelError("Archi-normalisatie mislukt:\n" + output)
