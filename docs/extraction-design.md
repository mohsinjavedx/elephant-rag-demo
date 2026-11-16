# Standalone elephant RAG demonstration

The user requested the complete elephant lesson as a separate project outside the main research assistant, suitable for pushing to GitHub. The existing walkthrough and its measured output must remain available, and all elephant-specific files and references must leave the original project.

Use a sibling directory named `elephant-rag-demo`. Copy only the required PDF validation, extraction, normalization, chunking and schema modules into its own `elephant_rag` Python package. Retain the licensed tokenizer vocabulary. Adapt the existing demonstration to this local package; do not import or require the original application, its environment files, frontend, database, or configuration.

Provide a Python 3.12 project, locked uv dependencies, an offline browser viewer with the existing six stage buttons, generated PDFs/Markdown/JSON, clear README and walkthrough, meaningful CLI/data verification, and GitHub CI. Preserve the existing chunking behavior and clearly document the overlap and model-token limitations. Real embeddings use the existing public BGE model and local ONNX CPU inference.

The source PDF, extraction, normalization, chunks, vectors and five retrieval examples must work from the new project. The first embedding run may download the public model; reading saved results, preparing the PDF and rendering the viewer must not require an internet connection. Model weights, virtual environments, caches and credentials are excluded from Git. Initialize a separate local Git repository, with no remote or publishing side effects.

The chosen approach copies the small dependency closure rather than depending on the original repository or rewriting its algorithms. This preserves the lesson and makes a GitHub checkout independently runnable. Verify the new project before removing source copies. Original application modules and its existing phase guides remain intact.

The user's existing instruction to proceed without permission questions applies; execution continues inline without an approval handoff.
