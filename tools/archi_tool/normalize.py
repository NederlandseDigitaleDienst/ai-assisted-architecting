"""Normalize a .archimate file through the headless Archi CLI.

Archi is the canonical serializer: a load + save roundtrip rewrites the file
exactly as Archi itself would, so git diffs stay small regardless of whether
the last edit came from this tool or from the Archi GUI. A throwaway
workspace (-data) avoids lock conflicts with a running Archi GUI.
"""
from __future__ import annotations

import os
import subprocess
import tempfile

from .model import ModelError

ARCHI_APP_DEFAULT = "/Applications/Archi.app/Contents/MacOS/Archi"


def find_archi_binary():
    binary = os.environ.get("ARCHI_APP", ARCHI_APP_DEFAULT)
    return binary if os.path.exists(binary) else None


def normalize(path) -> None:
    binary = find_archi_binary()
    if not binary:
        raise ModelError(
            "Archi niet gevonden. Installeer Archi in /Applications of zet "
            "de env var ARCHI_APP naar het pad van de Archi-binary.")
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
