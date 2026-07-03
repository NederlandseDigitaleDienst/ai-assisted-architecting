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
    override = os.environ.get("ARCHI_APP")
    if override:
        # an explicit override must not silently fall through to defaults
        return override if os.path.exists(override) else None
    for candidate in ARCHI_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    return shutil.which("Archi")


def normalize(path) -> None:
    binary = find_archi_binary()
    if not binary:
        raise ModelError(
            "Archi niet gevonden. Installeer Archi (macOS: brew install "
            "--cask archi; Windows: winget install --id Archi.Archi -e) of "
            "zet de env var ARCHI_APP naar het pad van de Archi-binary.")
    absolute = os.path.abspath(path)
    with tempfile.TemporaryDirectory() as workspace:
        result = subprocess.run(
            [binary, "-application", "com.archimatetool.commandline.app",
             "-consoleLog", "-nosplash", "-data", workspace,
             "--loadModel", absolute, "--saveModel", absolute],
            capture_output=True, text=True)
    if result.returncode != 0:
        raise ModelError(
            "Archi-normalisatie mislukt:\n" + result.stdout + result.stderr)
