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

# Views naar Mermaid en NLDD-HTML, decks naar slides
render:
    uv run archi render

# Serialisatie canoniek maken via de headless Archi CLI (doen vóór commit)
normalize:
    uv run archi normalize

# Aantallen per type, relaties en views
stats:
    uv run archi stats

# Folderstructuur van het model met inhoud
tree:
    uv run archi tree

# Elementen tonen, optioneel gefilterd: `just list --type Capability`
list *args:
    uv run archi list {{ args }}

# Eén element met properties en relaties: `just show "Gegevensuitwisseling"`
show *args:
    uv run archi show {{ args }}

# Testsuite
test:
    uv run pytest

# Model openen in Archi (os-bewust: open / Start-Process / xdg-open)
open:
    {{ if os() == "macos" { "open" } else if os() == "windows" { "Start-Process" } else { "xdg-open" } }} models/ado.archimate

# Gerenderde HTML-views en slides lokaal serveren op http://localhost:8766
serve:
    uv run python -m http.server 8766 --directory views/html
