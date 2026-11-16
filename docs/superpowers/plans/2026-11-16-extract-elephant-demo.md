# Standalone Elephant Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Move the entire elephant lesson out of the research assistant into a GitHub-ready sibling project that runs independently.

**Architecture:** A local `elephant_rag` package owns the existing PDF ingestion and chunking modules, demo generator and HTML templates. A uv-managed CLI builds the sample, embeds chunks, ranks queries, exports PDFs/data and opens a local static viewer.

**Tech Stack:** Python 3.12, uv, PyMuPDF/PyMuPDF4LLM, pypdf, tiktoken, Pydantic, ReportLab, ONNX Runtime, Hugging Face Hub, tokenizers, NumPy, pytest, Ruff.

**Spec:** `docs/extraction-design.md`

## Global Constraints

- New root: `C:\MOHSIN\LLM projects\elephant-rag-demo`, outside the original repository.
- No runtime imports, paths, environment or database dependency on the original project.
- Preserve real outputs and current chunking algorithms; do not bundle model weights or secrets.
- Verify the destination before removing elephant-specific originals; leave application code intact.
- User already authorized action without confirmation; no remote push or publication requested.

## Review Focus

- A checkout in a different directory must have all tokenizer and HTML assets.
- Saved-data viewing/report rendering must work without Hugging Face access.
- CLI preparation must retain all normalized text with valid source offsets and remove staged PDFs.
- Browser stage buttons must work from a local file and at a narrow width.
- Original-project cleanup must touch only elephant-specific artifacts and their exact documentation links.

### Task 1: Standalone package and independent preparation

**Files:** `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `src/elephant_rag/**`, `tests/test_cli.py`.

**Interfaces:** Owns `python -m elephant_rag prepare`; produces PDFs and stage 01–04 exports without importing `app`.

- [x] Write CLI acceptance test: run `prepare` in a fresh output directory and assert three text pages, removed boundaries, retained content and cleaned staging.
- [x] Run before implementation; expected failure: CLI package is unavailable.
- [x] Copy only ingestion/chunking/schema modules and assets, adapt imports and generator, add the CLI and locked project dependencies.
- [x] Run the preparation acceptance test; expected pass.

### Task 2: Complete walkthrough, reproducibility and GitHub packaging

**Files:** browser templates, `docs/walkthrough.md`, `README.md`, CI, saved `output/**`, `tests/test_saved_data.py`.

**Interfaces:** Consumes stage 01–04 data; `all` generates every stage; `report` rebuilds PDFs and viewer from saved data. `view` serves only generated output on loopback.

- [x] Add acceptance test for a browser document produced by `report`, using saved vectors without network access.
- [x] Keep all existing elephant artifacts; adapt guide paths and package templates. Export the browser viewer as part of each report run, without a Codex skill dependency.
- [x] Run `uv sync --frozen`, `uv run elephant-rag all`, the full new-project test suite, Ruff, a wheel/install smoke check, and a browser stage-control check. Expected: all pass.
- [x] Add README, reproducibility notes, provenance, CI, and local Git initialization. Do not create a remote or push.

### Task 3: Remove source demo and verify separation

**Files:** original elephant scripts/template, guide/link, output files and ignored QA artifacts.

**Interfaces:** Requires the independently verified new project; original application modules are retained unchanged.

- [x] Compare original and destination source PDF/data exports; preserve every demo file in the destination.
- [x] Remove exact elephant-specific original files/directories using checked absolute paths; remove only the elephant guide index entry.
- [x] Scan original tracked and untracked content for elephant references, inspect Git status/diff, and recheck new-project CLI/tests/viewer. Expected: no elephant artifacts remain in the original project; the standalone lesson works.
- [x] Perform one final independent review under the executing-plans skill; address material findings and report the destination and run command.
