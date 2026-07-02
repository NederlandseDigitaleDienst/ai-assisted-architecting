# Taakrunner voor ai-assisted-architecting. `just` toont deze lijst.

# Op Windows draaien recipes in PowerShell (geen sh nodig)
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Eenmalige setup: venv, dependencies en pre-commit hooks
setup:
    uv sync
    uv run pre-commit install

# Integriteitschecks op het model
validate:
    uv run archi validate

# Views renderen naar Mermaid (views/) en NLDD-HTML (views/html/)
render:
    uv run archi render

# Serialisatie canoniek maken via de headless Archi CLI (doen vóór commit)
normalize:
    uv run archi normalize

# Aantallen per type, relaties en views
stats:
    uv run archi stats

# Testsuite
test:
    uv run pytest

# Model openen in Archi (os-bewust: open / Start-Process / xdg-open)
open:
    {{ if os() == "macos" { "open" } else if os() == "windows" { "Start-Process" } else { "xdg-open" } }} models/ado.archimate

# Gerenderde HTML-views lokaal serveren op http://localhost:8766
serve:
    uv run python -m http.server 8766 --directory views/html
