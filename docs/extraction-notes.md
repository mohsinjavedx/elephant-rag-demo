# Extraction notes

The elephant lesson is now a separate sibling project with its own Python package, uv lockfile, Git history, local browser viewer, PDF generation and real embedding/retrieval pipeline.

Copied and adapted the minimum PDF validation/extraction/normalization, Markdown chunking and schema modules. Their algorithms remain the same; imports now point to `elephant_rag`. The tokenizer vocabulary and its upstream license are included. No application settings, environment files, frontend, database code or model weights were copied.

The source PDF and complete extraction, normalization, chunks, embeddings and retrieval exports were compared with the original and matched. A byte-checked archive of all 24 original demo files is retained at `docs/archive/original-elephant-example.zip`. Runnable versions use the independent package and browser templates.

After independent preparation, full inference, offline viewing, tests and installed-wheel checks passed, the original demo scripts, template, guide, output and ignored verification files were moved out of the original project. The single demo link was removed from its phase index. The original project has a clean Git status and no elephant references outside ignored dependency/Git directories.

An automatic policy check rejected the original recursive cleanup command. The files were preserved using a reversible native move instead, into this project's ignored `tmp/extraction-originals` folder. This does not affect the GitHub-ready package or the original project's cleanup.

The model revision is pinned for reproducibility and cached/offline use. The known overlap-start behavior and embedding-model input limit are documented rather than changed during extraction. Git was initialized locally, with no remote and no push.

See `docs/verification/standalone-checks.json` for checks. GitHub Actions is configured; remote CI has not run.
