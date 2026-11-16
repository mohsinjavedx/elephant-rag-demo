# Elephant example: from PDF to retrieved evidence

This lesson runs this standalone project's own ingestion and chunking classes on a short original elephant document. It covers the nose/trunk, teeth/tusks, four legs, ears, and body size. Biological facts are paraphrased from [San Diego Zoo](https://animals.sandiegozoo.org/animals/elephant).

## Open the results

- [Interactive browser walkthrough with six stage buttons](../output/elephant-walkthrough/index.html) — open in a web browser. The buttons appear at the top; they are not inside the PDF or the application's frontend.
- [Complete data bundle: both PDFs, all Markdown and JSON exports](../output/elephant-walkthrough-data.zip)
- [Original three-page PDF](../output/pdf/elephant-source.pdf)
- [Printable processing walkthrough](../output/pdf/elephant-processing-walkthrough.pdf)
- [Validation and verified staging cleanup](../output/elephant-walkthrough/01-validation.json)
- [Complete extraction, including text-density checks](../output/elephant-walkthrough/02-extracted.json)
- [Complete normalization and source mappings](../output/elephant-walkthrough/03-normalized.json)
- [Every chunk in both configurations](../output/elephant-walkthrough/04-chunks.json)
- [Every chunk/query vector, token ID and token piece](../output/elephant-walkthrough/05-embeddings.json)
- [Every ranked retrieval candidate for all five questions](../output/elephant-walkthrough/06-retrieval.json)
- [Run provenance and package versions](../output/elephant-walkthrough/00-manifest.json)

The browser walkthrough includes the original PDF pages and lets you inspect each stage, each chunk, all 384 embedding values, and all retrieval candidates. Its HTML fragment is generated from [this template](../src/elephant_rag/walkthrough.html). The browser wrapper is packaged alongside it and works offline.

## 1. Validate the PDF and read its text layer

The PDF has three real text pages. `PDFValidator` checks its filename, type, signature, byte limit and structure. `PDFMarkdownExtractor` checks original native text density before extraction. No OCR is used. The private UUID-named PDF copy is deleted after parsing; the original PDF remains available.

## 2. Extract Markdown

The raw per-page outputs are saved unchanged:

- [Page 1](../output/elephant-walkthrough/02-page-1-extracted.md)
- [Page 2](../output/elephant-walkthrough/02-page-2-extracted.md)
- [Page 3](../output/elephant-walkthrough/02-page-3-extracted.md)

For example, page 1 starts with the running header, then Markdown headings:

```markdown
ELEPHANT FIELD NOTES

# **The elephant's nose**

## **Nose and trunk**
```

It ends with `Page 1 of 3`. Physical line wrapping can introduce blank lines inside prose. That is real parser output, not text reconstructed for the lesson.

## 3. Normalize Markdown

The repeated running header and page counter are removed from each page: six boundary removals in total. The actual elephant sentences stay unchanged. Newline placeholders remain, so the exported Markdown can begin and end with blank lines.

- [Normalized page 1](../output/elephant-walkthrough/03-page-1-normalized.md)
- [Normalized page 2](../output/elephant-walkthrough/03-page-2-normalized.md)
- [Normalized page 3](../output/elephant-walkthrough/03-page-3-normalized.md)

`source_spans` maps normalized offsets to the original extracted Markdown. Offsets are zero-based Unicode character positions, with exclusive ends; they are not PDF byte positions or on-page coordinates.

## 4. Split into chunks

Two runs use the same `MarkdownChunker` implementation:

- **Project defaults:** minimum 600, maximum 800, overlap up to 100 `cl100k_base` tokens. This short PDF produces three chunks, one per page. A short page may be below the minimum target because the implementation keeps chunks on a single page.
- **Teaching configuration:** minimum 35, maximum 65, overlap up to 12 tokens. This produces seven chunks labelled T01 through T07. Both configurations are included to compare large and small chunks on the same short PDF.

The teaching chunks contain 47, 51, 47, 40, 46, 46 and 49 chunker tokens respectively. The splitter prefers natural section and paragraph boundaries. The normalized text for T02 includes both the end of the preceding passage and the paragraph about drinking:

```text
smelling. It can also grasp food and touch objects.


To drink, an elephant draws water into its trunk and then pours it into its mouth. The trunk is

flexible and contains no bones. It performs different jobs from the elephant's teeth.
```

The first sentence is overlap from T01. Repeating context helps preserve meaning at a boundary. Each chunk also retains its original raw text, page number, exact character range and stable ID.

An implementation detail is visible in T07: its overlap begins with `els.` from `vessels.`. Chunk endings prefer natural boundaries, but the existing overlap-start selector works with character offsets within a token budget and can start inside a word. The lesson preserves and marks this behavior; it does not silently repair the output.

The run checks every chunk against its source slices and verifies that every non-whitespace character in the normalized document appears in at least one chunk.

## 5. Generate real embeddings

The script downloads the publisher's ONNX export of [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5), pins the resolved model revision in the export, and runs it locally on CPU. It uses the CLS output followed by L2 normalization, producing a real 384-number vector per chunk. Both configurations are embedded: ten chunk vectors altogether.

All five questions are embedded too. The exact question input includes the model's retrieval instruction prefix. All vectors, full numeric precision, token IDs and token pieces are included in the embedding export; the printable walkthrough shows numeric previews to keep it readable.

The embedding tokenizer differs from `cl100k_base`. The largest chunk input here is 113 model tokens including special tokens, safely below the model's 512-token limit. Truncation is disabled, and an explicit check rejects longer input. The project's 600–800 chunker-token defaults must be reconciled with model-specific input limits before production embedding of longer documents.

An embedding coordinate does not have a label such as “trunk” or “ear.” Meaning is distributed across the vector, and similarity compares whole vectors.

## 6. Retrieve passages

For each question, the demonstration compares its vector with every chunk vector using exact cosine similarity. The exports contain all candidates in descending order for both configurations. The browser lesson expands the top three and lets you inspect the rest.

For the teaching configuration, the first-ranked results are:

- Nose/drinking question → T02, page 1, similarity approximately 0.807297.
- Tusks versus molars → T03, page 2, approximately 0.818644.
- Number of legs → T05, page 2, approximately 0.815797.
- Ear cooling → T06, page 3, approximately 0.832069.
- Size comparison → T07, page 3, approximately 0.827141.

These are measured similarities, not probabilities or calibrated confidence scores. This small teaching example is not a retrieval quality benchmark. Query rewriting and reranking are disabled so the relationship between the original question, its embedding, the chunk vectors and the returned passages stays visible.

## Run it again

From this project's root directory:

```powershell
uv sync --frozen
uv run elephant-rag all
```

All dependencies are defined in this project's `pyproject.toml` and pinned in `uv.lock`. The first run downloads the public model to the normal Hugging Face cache. The script replaces only its own named lesson outputs under `output/pdf` and `output/elephant-walkthrough`.

Stages can also run separately with `prepare`, `embed` and `report`, in that order. `report` reads saved stage data and rebuilds the printable and browser walkthroughs. No database or API server is needed.

The entire pipeline belongs to this project. Retrieval uses local in-memory vectors; no database, API service, query rewriting, reranking or answer-generating LLM is involved.

[Back to the project README](../README.md)
