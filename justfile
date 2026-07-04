# Taakrunner voor de archi-cli-tool. `just` toont deze lijst.

# Op Windows draaien recipes in PowerShell (geen sh nodig)
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

default:
    @just --list

# Eenmalige setup: venv, dependencies en pre-commit hooks
setup:
    uv sync
    uv run pre-commit install

# Testsuite
test:
    uv run pytest

# Toon de CLI in actie op het testfixture-model
demo:
    uv run archi --model tests/fixtures/klein-model.archimate stats

# Bouw de distributies en controleer de metadata (vóór een release)
build:
    rm -rf dist
    uv build
    uv run --with twine python -m twine check dist/*
