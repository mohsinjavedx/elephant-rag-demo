# Elephant RAG Demo

A standalone learning project that shows an elephant PDF becoming Markdown, normalized text, chunks, real embeddings and retrieved passages. It has its own Python package and dependencies. No database, API key, Node.js or other project is required.

## View the saved lesson

Open `output/elephant-walkthrough/index.html` in a browser. The six stage buttons are at the top. The PDFs and complete Markdown/JSON exports are included in `output`.

## Rebuild

Install Python 3.12 and [uv](https://docs.astral.sh/uv/getting-started/installation/). From this project directory:

```powershell
uv sync --frozen
uv run elephant-rag all
uv run elephant-rag view --open
```

The last command opens `http://127.0.0.1:8765/`. Stop it with Ctrl+C. Use `--port 8766` if that port is occupied. You can also double-click the saved HTML without starting Python.

The first embedding run downloads the public `BAAI/bge-small-en-v1.5` ONNX model to your normal Hugging Face cache. Its revision is pinned. Inference runs on your CPU; the PDF and questions are not sent to a hosted inference service. Once model files are cached, `HF_HUB_OFFLINE=1` enables offline embedding too. No model weights are included in Git.

## Run one stage at a time

```powershell
uv run elephant-rag prepare  # Create PDF, validate, extract, normalize, chunk
uv run elephant-rag embed    # Create real vectors and rank the five questions
uv run elephant-rag report   # Rebuild printable and browser walkthroughs from saved data
uv run elephant-rag view --open
```

Run commands from the directory where you want `output/` to be created. `prepare` and `report` do not need the embedding model or an internet connection. Saved results are committed so you can explore the lesson immediately after cloning.

## What you can inspect

1. Original three-page elephant PDF and validation checks.
2. Exact page-by-page Markdown from PyMuPDF4LLM.
3. Normalized Markdown with removed headers/footers and exact source mappings.
4. Default versus teaching chunks, token budgets, overlap and page/character provenance.
5. Every model token, token ID and all 384 numeric values per chunk/question embedding.
6. Every cosine-ranked passage for five example questions.

The original/default configuration produces three chunks. Smaller teaching settings produce seven. The lesson exposes one overlap that starts inside a word; that behavior is retained for transparency. Embedding inputs are checked with the model's tokenizer against its 512-token limit, with truncation disabled. Larger chunk budgets must be reconciled with that limit for longer documents.

Read [the full walkthrough](docs/walkthrough.md) for actual text examples, measured rankings and limitations.

The [original lesson snapshot](docs/archive/original-elephant-example.zip) preserves the demo files before extraction. It is historical reference; the runnable package and viewer are the independent versions in this repository.

## Project structure

```text
src/elephant_rag/
  __main__.py             # python -m elephant_rag entry point
  walkthrough.py          # Stage orchestration, PDF generation, embeddings, retrieval, CLI
  walkthrough.html        # Stage controls and data inspector
  viewer.html             # Offline browser document and styles
  ingestion/              # Validation, text-density checks, extraction, normalization
  chunking/               # Markdown blocks, splitting, offline tokenizer and assets
  schemas/                # Chunk data and provenance validation
output/
  pdf/                    # Source PDF and printable walkthrough
  elephant-walkthrough/   # Browser viewer, complete JSON and per-page Markdown
  elephant-walkthrough-data.zip
docs/                     # Lesson, provenance and extraction notes
scripts/check_browser.py  # Optional offline browser interaction check
tests/                    # CLI, text provenance, vectors and ranking checks
.github/workflows/        # Automated checks when pushed to GitHub
pyproject.toml            # Dependencies and elephant-rag command
uv.lock                   # Reproducible dependency versions
```

## Verify

```powershell
uv run pytest -q
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv build
```

Optional browser checks:

```powershell
uv sync --frozen --group browser
uv run playwright install chromium
uv run python scripts/check_browser.py
```

## GitHub

This directory is its own local Git repository. Add your new empty GitHub repository as the remote, then push:

```powershell
git remote add origin https://github.com/YOUR-USERNAME/elephant-rag-demo.git
git push -u origin main
```

Virtual environments, model caches, temporary renders and credentials are ignored. The generated PDFs, lesson data and offline viewer are deliberately included. Third-party tokenizer attribution and license are preserved in `src/elephant_rag/chunking/assets`; source and model attribution are recorded in the lesson and its manifest.
# elephant-rag-demo
# elephant-rag-demo
# elephant-rag-demo
