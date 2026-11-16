"""Export a real, inspectable PDF -> chunks -> embeddings -> retrieval lesson.

Run from your desired output directory with ``elephant-rag all``.
Every pipeline module and template belongs to this standalone package.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

ROOT = Path.cwd()
OUT = ROOT / "output" / "elephant-walkthrough"
PDF_OUT = ROOT / "output" / "pdf"
SOURCE_PDF = PDF_OUT / "elephant-source.pdf"
REPORT_PDF = PDF_OUT / "elephant-processing-walkthrough.pdf"
MODEL = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
TEACHING = {"min_tokens": 35, "max_tokens": 65, "overlap_tokens": 12}
DEFAULT = {"min_tokens": 600, "max_tokens": 800, "overlap_tokens": 100}
SOURCES = [
    {"title": "San Diego Zoo: Elephant", "url": "https://animals.sandiegozoo.org/animals/elephant"},
    {"title": "BAAI embedding model card", "url": "https://huggingface.co/BAAI/bge-small-en-v1.5"},
]

# A short original teaching text, paraphrasing factual information from the zoo.
# Deliberate page breaks make provenance and repeated page furniture observable.
PAGES = [
    {
        "title": "The elephant's nose",
        "sections": [
            (
                "Nose and trunk",
                [
                    "An elephant's trunk combines its nose and upper lip. The trunk has "
                    "nostrils for breathing and smelling. It can also grasp food and "
                    "touch objects.",
                    "To drink, an elephant draws water into its trunk and then pours it into "
                    "its mouth. The trunk is flexible and contains no bones. It performs "
                    "different jobs from the elephant's teeth.",
                ],
            ),
        ],
    },
    {
        "title": "Teeth and legs",
        "sections": [
            (
                "Teeth and tusks",
                [
                    "Tusks are elongated incisor teeth. Elephants use tusks for digging "
                    "and defense. Inside the mouth, molars grind plant food.",
                    "New molars move forward from the back of the jaw as older ones wear "
                    "down. Tusks and chewing teeth have different roles.",
                ],
            ),
            (
                "Four legs",
                [
                    "An elephant has four legs. The legs support its large body and "
                    "allow it to walk. Legs provide movement; the trunk handles food.",
                ],
            ),
        ],
    },
    {
        "title": "Ears and body size",
        "sections": [
            (
                "Ears",
                [
                    "Elephant ears help release body heat. Flapping them helps cool "
                    "blood passing through their vessels. African elephants generally "
                    "have larger ears than Asian elephants.",
                ],
            ),
            (
                "Size",
                [
                    "Elephants are the largest living land mammals. Body size varies "
                    "with species, sex, and age. African savanna elephants are generally "
                    "larger than Asian elephants.",
                ],
            ),
        ],
    },
]

QUESTIONS = [
    "How does an elephant use its nose to drink water?",
    "What is the difference between elephant tusks and molars?",
    "How many legs does an elephant have?",
    "How do an elephant's ears help it cool down?",
    "Which elephants are generally larger than Asian elephants?",
]


def save(name: str, value: object) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def create_source() -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph

    PDF_OUT.mkdir(parents=True, exist_ok=True)
    pdf = Canvas(str(SOURCE_PDF), pagesize=A4, invariant=1)
    pdf.setTitle("Elephant field notes: anatomy teaching sample")
    pdf.setAuthor("Research Assistant - educational walkthrough")
    width, height = A4
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=12, leading=19)
    for index, page in enumerate(PAGES):
        pdf.setFillColor(colors.HexColor("#53625c"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(48, height - 31, "ELEPHANT FIELD NOTES")
        pdf.setFillColor(colors.HexColor("#203c31"))
        pdf.setFont("Helvetica-Bold", 24)
        pdf.drawString(48, height - 89, page["title"])
        y = height - 142
        for heading, paragraphs in page["sections"]:
            pdf.setFillColor(colors.HexColor("#203c31"))
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(48, y, heading)
            y -= 29
            pdf.setFillColor(colors.HexColor("#26312b"))
            for text in paragraphs:
                paragraph = Paragraph(text, body)
                _, used = paragraph.wrap(width - 96, height)
                paragraph.drawOn(pdf, 48, y - used)
                y -= used + 17
            y -= 22
        pdf.setFillColor(colors.HexColor("#53625c"))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(48, 27, f"Page {index + 1} of {len(PAGES)}")
        pdf.showPage()
    pdf.save()
    print(f"Created source PDF: {SOURCE_PDF.name}", flush=True)


def prepare() -> None:
    from elephant_rag.chunking.splitter import MarkdownChunker
    from elephant_rag.ingestion.extraction import PDFMarkdownExtractor
    from elephant_rag.ingestion.normalization import MarkdownNormalizer
    from elephant_rag.ingestion.validation import PDFValidator

    create_source()
    # Use the exact production classes. Keep the staged path only to verify cleanup.
    with SOURCE_PDF.open("rb") as stream:
        with PDFValidator().validate(stream, filename=SOURCE_PDF.name) as staged:
            staged_path = staged.path
            validation = {
                "filename": SOURCE_PDF.name,
                "size_bytes": staged.size_bytes,
                "page_count": staged.page_count,
                "checksum_sha256": staged.checksum,
                "temporary_name": staged.path.name,
                "temporary_path_pattern": "%TEMP%/research-pdf-*/<uuid>.pdf",
                "staged_file_existed_inside_context": staged.path.is_file(),
            }
            extracted = PDFMarkdownExtractor().extract(staged)
    validation["staged_file_deleted_after_context"] = not staged_path.exists()
    validation["staged_directory_deleted_after_context"] = not staged_path.parent.exists()
    document = MarkdownNormalizer().normalize(extracted)
    document_id = uuid5(NAMESPACE_URL, "research-pdf:" + extracted.checksum)
    save("01-validation.json", validation)
    save("02-extracted.json", asdict(extracted))
    save(
        "03-normalized.json",
        {"document_id": str(document_id), "pages": [asdict(p) for p in document.pages]},
    )
    for page in document.pages:
        (OUT / f"02-page-{page.page_number}-extracted.md").write_text(
            page.raw_text, encoding="utf-8"
        )
        (OUT / f"03-page-{page.page_number}-normalized.md").write_text(
            page.normalized_text, encoding="utf-8"
        )
    chunk_sets = {}
    for name, config in (("default", DEFAULT), ("teaching", TEACHING)):
        chunks = MarkdownChunker(**config).split(document, document_id=document_id)
        items = [chunk.model_dump(mode="json") for chunk in chunks]
        by_page = {p.page_number: p for p in document.pages}
        for i, item in enumerate(items):
            page = by_page[item["page_start"]]
            start = item["metadata"]["normalized_char_start"]
            end = item["metadata"]["normalized_char_end"]
            assert page.raw_text[item["char_start"] : item["char_end"]] == item["raw_text"]
            assert page.normalized_text[start:end] == item["normalized_text"]
            previous = (
                items[i - 1] if i and items[i - 1]["page_start"] == item["page_start"] else None
            )
            overlap_end = (
                min(end, previous["metadata"]["normalized_char_end"]) if previous else start
            )
            item["demonstration"] = {
                "label": f"{name[0].upper()}{i + 1:02}",
                "overlap_with_previous_text": page.normalized_text[start:overlap_end]
                if overlap_end > start
                else "",
                "overlap_start_inside_word": bool(
                    previous
                    and start
                    and page.normalized_text[start - 1].isalnum()
                    and page.normalized_text[start].isalnum()
                ),
            }
        # Check all non-whitespace source characters survived in at least one chunk.
        for page in document.pages:
            covered = set()
            for item in items:
                if item["page_start"] == page.page_number:
                    covered.update(
                        range(
                            item["metadata"]["normalized_char_start"],
                            item["metadata"]["normalized_char_end"],
                        )
                    )
            assert all(
                i in covered for i, char in enumerate(page.normalized_text) if not char.isspace()
            )
        chunk_sets[name] = {"settings": config, "chunks": items}
    save("04-chunks.json", chunk_sets)
    manifest = {
        "source_pdf": str(SOURCE_PDF.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(SOURCE_PDF.read_bytes()).hexdigest(),
        "document_id": str(document_id),
        "sources": SOURCES,
        "packages": {
            n: version(n) for n in ["pypdf", "pymupdf", "pymupdf4llm", "tiktoken", "reportlab"]
        },
        "scope": "Standalone educational PDF, chunking, embedding and retrieval pipeline.",
        "checks": {
            "chunk_raw_offsets_match": True,
            "chunk_normalized_offsets_match": True,
            "all_non_whitespace_covered": True,
        },
    }
    save("00-manifest.json", manifest)
    print(
        json.dumps(
            {
                "pages": len(document.pages),
                "removed_boundaries": sum(len(p.removed_boundaries) for p in document.pages),
                "chunks": {k: len(v["chunks"]) for k, v in chunk_sets.items()},
                "staged_pdf_deleted": validation["staged_file_deleted_after_context"],
            }
        ),
        flush=True,
    )


def embed() -> None:
    import numpy as np
    import onnxruntime as ort
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    chunks = load("04-chunks.json")
    revision = MODEL_REVISION
    print(f"Downloading/loading {MODEL} at {revision}", flush=True)
    tokenizer_file = hf_hub_download(MODEL, "tokenizer.json", revision=revision)
    onnx_file = hf_hub_download(MODEL, "onnx/model.onnx", revision=revision)
    tokenizer = Tokenizer.from_file(tokenizer_file)
    # Never truncate: verify the actual BERT tokenizer length before inference.
    tokenizer.no_truncation()
    tokenizer.no_padding()
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(
        onnx_file, sess_options=options, providers=["CPUExecutionProvider"]
    )
    input_names = {entry.name for entry in session.get_inputs()}
    output_names = [entry.name for entry in session.get_outputs()]
    print(json.dumps({"inputs": sorted(input_names), "outputs": output_names}), flush=True)

    def encode(text: str) -> dict:
        encoded = tokenizer.encode(text, add_special_tokens=True)
        if len(encoded.ids) > 512:
            raise ValueError(f"Embedding input exceeds model limit: {len(encoded.ids)} > 512")
        candidates = {
            "input_ids": np.array([encoded.ids], dtype=np.int64),
            "attention_mask": np.array([encoded.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([encoded.type_ids], dtype=np.int64),
        }
        outputs = session.run(None, {k: candidates[k] for k in input_names})
        # The publisher's BGE method uses the CLS token, then L2 normalization.
        hidden = outputs[output_names.index("last_hidden_state")]
        vector = hidden[0, 0].astype(np.float32)
        vector /= np.linalg.norm(vector)
        assert vector.shape == (384,) and np.isfinite(vector).all()
        return {
            "model_token_count_including_special_tokens": len(encoded.ids),
            "token_ids": encoded.ids,
            "token_pieces": encoded.tokens,
            "vector": vector.tolist(),
            "l2_norm": float(np.linalg.norm(vector)),
        }

    embedded_sets = {}
    query_records = [
        {"question": q, "embedding_input": QUERY_PREFIX + q, **encode(QUERY_PREFIX + q)}
        for q in QUESTIONS
    ]
    retrieval_sets = {}
    for name, chunk_set in chunks.items():
        records = []
        for chunk in chunk_set["chunks"]:
            records.append(
                {
                    "chunk_id": chunk["id"],
                    "label": chunk["demonstration"]["label"],
                    "embedding_input": chunk["normalized_text"],
                    **encode(chunk["normalized_text"]),
                }
            )
        embedded_sets[name] = records
        matrix = np.array([r["vector"] for r in records], dtype=np.float32)
        retrieval_sets[name] = []
        for query in query_records:
            scores = matrix @ np.array(query["vector"], dtype=np.float32)
            ranking = sorted(range(len(records)), key=lambda i: (-float(scores[i]), i))
            matches = []
            for rank, index in enumerate(ranking, start=1):
                chunk = chunk_set["chunks"][index]
                matches.append(
                    {
                        "rank": rank,
                        "label": records[index]["label"],
                        "chunk_id": chunk["id"],
                        "cosine_similarity": float(scores[index]),
                        "page": chunk["page_start"],
                        "char_start": chunk["char_start"],
                        "char_end": chunk["char_end"],
                        "text": chunk["normalized_text"],
                    }
                )
            retrieval_sets[name].append(
                {
                    "question": query["question"],
                    "top_k": min(3, len(matches)),
                    "all_ranked_matches": matches,
                }
            )
    save(
        "05-embeddings.json",
        {
            "model": MODEL,
            "revision": revision,
            "dimensions": 384,
            "model_max_tokens": 512,
            "runtime": "ONNX Runtime CPU",
            "pooling": "CLS, then L2 normalization",
            "query_prefix": QUERY_PREFIX,
            "truncation": False,
            "chunk_sets": embedded_sets,
            "queries": query_records,
            "packages": {
                n: version(n) for n in ["onnxruntime", "tokenizers", "huggingface_hub", "numpy"]
            },
            "onnx_sha256": sha256(Path(onnx_file).read_bytes()).hexdigest(),
        },
    )
    save(
        "06-retrieval.json",
        {
            "method": "Exact cosine similarity over all locally generated vectors",
            "query_rewriting": False,
            "reranking": False,
            "database_used": False,
            "chunk_sets": retrieval_sets,
        },
    )
    print(
        json.dumps(
            {
                "dimensions": 384,
                "embedded_chunks": {k: len(v) for k, v in embedded_sets.items()},
                "questions": len(query_records),
                "maximum_model_tokens": max(
                    r["model_token_count_including_special_tokens"]
                    for v in embedded_sets.values()
                    for r in v
                ),
            }
        ),
        flush=True,
    )


def report() -> None:
    import base64
    from html import escape
    from zipfile import ZIP_DEFLATED, ZipFile

    import pymupdf
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        KeepTogether,
        PageBreak,
        Paragraph,
        Preformatted,
        SimpleDocTemplate,
    )

    validation, extracted, normalized = (
        load("01-validation.json"),
        load("02-extracted.json"),
        load("03-normalized.json"),
    )
    chunks, embeddings, retrieval = (
        load("04-chunks.json"),
        load("05-embeddings.json"),
        load("06-retrieval.json"),
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle("DataText", fontName="Courier", fontSize=8, leading=11, spaceAfter=10)
    )
    styles.add(
        ParagraphStyle("SmallNote", fontName="Helvetica", fontSize=9, leading=13, spaceAfter=9)
    )
    for name in ["Title", "Heading1", "Heading2", "Heading3"]:
        styles[name].textColor = colors.HexColor("#203c31")
    styles["BodyText"].spaceAfter = 8
    story = []

    def p(text: str, style: str = "BodyText") -> None:
        story.append(Paragraph(escape(text), styles[style]))

    def keep_group(start: int) -> None:
        story[start:] = [KeepTogether(story[start:])]

    def code(text: str) -> None:
        # Preserve Markdown and its blank lines without extra paragraph spacing.
        story.append(Preformatted(text, styles["DataText"], maxLineLength=100))

    p("An elephant through the RAG pipeline", "Title")
    p("A walkthrough made from actual project output", "Heading2")
    p(
        "Read the source PDF, compare the exact extracted and normalized "
        "Markdown, inspect every chunk, and follow real vectors into search"
        " results."
    )
    p(
        "This standalone project owns validation, extraction, normalization, "
        "chunking, local embeddings and retrieval. It needs no application "
        "server, database or API key."
    )
    p("1. Source PDF and validation", "Heading1")
    p(
        f"Source: elephant-source.pdf. Pages: {validation['page_count']}. "
        f"Bytes: {validation['size_bytes']}. SHA-256: {validation['checksum_sha256']}",
        "SmallNote",
    )
    p(
        "The caller's PDF is retained. A UUID-named copy is staged "
        "privately in the operating system's temporary folder and deleted "
        "after native parsing closes."
    )
    p(
        "Verified temporary-file cleanup: "
        f"{validation['staged_file_deleted_after_context']}. "
        f"Text-layer counts per page: {extracted['text_density']['text_char_counts']}. "
        "OCR was not needed.",
        "SmallNote",
    )
    p("2. Exact extracted Markdown", "Heading1")
    p(
        "The following is parser output, not Markdown reconstructed by an "
        "LLM. Heading markers, line wrapping, repeated running headers and "
        "page counters are visible."
    )
    for page in extracted["pages"]:
        start_group = len(story)
        p(f"PDF page {page['page_number']}", "Heading2")
        code(page["raw_text"])
        keep_group(start_group)
    story.append(PageBreak())
    p("3. Exact normalized Markdown", "Heading1")
    p(
        "Only repeated boundary furniture is removed. Source sentences are "
        "not paraphrased, lowercased, spell-corrected or rewritten. Newline"
        " placeholders remain; raw Markdown stays available for citation "
        "offsets."
    )
    for page in normalized["pages"]:
        start_group = len(story)
        p(f"PDF page {page['page_number']}", "Heading2")
        for removed in page["removed_boundaries"]:
            value = page["raw_text"][removed["char_start"] : removed["char_end"]]
            p(
                f"Removed {removed['kind']}: {value!r}; "
                f"raw characters [{removed['char_start']}, {removed['char_end']}).",
                "SmallNote",
            )
        code(page["normalized_text"])
        keep_group(start_group)
    story.append(PageBreak())
    p("4. Every chunk and its boundaries", "Heading1")
    p(
        "The document is short. Defaults may leave a page below the "
        "600-token target, because chunks do not cross pages. The teaching "
        "run uses the same chunker with 35-65 tokens and up to 12 tokens of"
        " overlap so more splits are visible. Defaults remain 600-800 / "
        "overlap 100."
    )
    p(
        "Chunk token counts use cl100k_base. Embedding token counts later "
        "use BGE's own tokenizer; these counts differ."
    )
    for name, chunk_set in chunks.items():
        p(f"{name.title()} configuration: {chunk_set['settings']}", "Heading2")
        for chunk in chunk_set["chunks"]:
            start_group = len(story)
            label = chunk["demonstration"]["label"]
            p(
                f"{label} - page {chunk['page_start']}; "
                f"{chunk['metadata']['token_count']} chunker tokens",
                "Heading3",
            )
            p(
                f"Raw characters [{chunk['char_start']}, {chunk['char_end']}); "
                f"normalized [{chunk['metadata']['normalized_char_start']}, "
                f"{chunk['metadata']['normalized_char_end']}). ID: {chunk['id']}",
                "SmallNote",
            )
            code(chunk["normalized_text"])
            overlap = chunk["demonstration"]["overlap_with_previous_text"]
            p(
                f"Exact overlap with previous chunk: {overlap!r}"
                if overlap
                else "No overlap with a previous chunk on this page.",
                "SmallNote",
            )
            if chunk["demonstration"]["overlap_start_inside_word"]:
                p(
                    (
                        "Observed implementation detail: overlap begins inside a word. The "
                        "current overlap selector uses character offsets within a token "
                        "budget. This output is shown unchanged."
                    ),
                    "SmallNote",
                )
            keep_group(start_group)
    story.append(PageBreak())
    p("5. Real embeddings", "Heading1")
    p(
        f"Model: {MODEL}. Revision: {embeddings['revision']}. Runtime: ONNX CPU. "
        "Each chunk becomes a 384-number vector using CLS pooling and L2 normalization."
    )
    p(
        "These values were computed, not invented. Individual dimensions "
        "are learned features; a dimension is not labelled nose, ears or "
        "size. Full unrounded vectors, token IDs and token pieces are in "
        "05-embeddings.json."
    )
    p(
        "No input was truncated. Every input was checked against the "
        "model's 512-token maximum using its own tokenizer. The project's "
        "larger default budgets need that check for future longer "
        "documents."
    )
    for records in embeddings["chunk_sets"].values():
        for record in records:
            start_group = len(story)
            p(
                f"{record['label']}: "
                f"{record['model_token_count_including_special_tokens']} model tokens; "
                f"384 dimensions; L2 norm {record['l2_norm']:.6f}",
                "Heading3",
            )
            p("First 12 values (preview only):", "SmallNote")
            code(", ".join(f"{v:.7f}" for v in record["vector"][:12]))
            keep_group(start_group)
    story.append(PageBreak())
    p("6. Retrieval from those vectors", "Heading1")
    p(
        "Each question receives the model's retrieval prefix and is "
        "embedded by the same model. Exact cosine similarity ranks every "
        "candidate. Scores measure similarity, not probability or factual "
        "confidence. No query rewriting, reranking, database or "
        "answer-generating LLM is used."
    )
    p(f"Question prefix: {QUERY_PREFIX!r}", "SmallNote")
    p(
        "Below are all five questions with the full top-three retrieved "
        "passages for the teaching chunks. All candidates, both chunk "
        "configurations and full query vectors remain available in the JSON"
        " exports and interactive walkthrough."
    )
    for result in retrieval["chunk_sets"]["teaching"]:
        p(result["question"], "Heading2")
        for match in result["all_ranked_matches"][: result["top_k"]]:
            start_group = len(story)
            p(
                f"Rank {match['rank']}: {match['label']}, page {match['page']}, "
                f"cosine {match['cosine_similarity']:.6f}",
                "Heading3",
            )
            code(match["text"])
            keep_group(start_group)
    story.append(PageBreak())
    p("Inspect all data", "Heading1")
    p(
        "output/elephant-walkthrough contains per-page Markdown and "
        "complete validation, normalization, chunks, embedding and "
        "retrieval JSON. The guide in docs/walkthrough.md explains "
        "how to repeat the run."
    )
    for source in SOURCES:
        p(source["title"] + ": " + source["url"], "SmallNote")

    def furniture(canvas, doc):
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#53625c"))
        canvas.drawString(42, 22, "Elephant processing walkthrough - actual exported output")
        canvas.drawRightString(A4[0] - 42, 22, str(doc.page))

    doc = SimpleDocTemplate(
        str(REPORT_PDF),
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=38,
        bottomMargin=42,
        title="Elephant processing walkthrough",
        author="Research Assistant",
    )
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    preview_images = []
    qa_dir = ROOT / "tmp" / "pdfs" / "elephant-walkthrough"
    qa_dir.mkdir(parents=True, exist_ok=True)
    for pdf_path in (SOURCE_PDF, REPORT_PDF):
        with pymupdf.open(pdf_path) as rendered:
            for index, page in enumerate(rendered):
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25))
                png = pixmap.tobytes("png")
                (qa_dir / f"{pdf_path.stem}-{index + 1:02}.png").write_bytes(png)
                if pdf_path == SOURCE_PDF:
                    preview_images.append(
                        "data:image/png;base64," + base64.b64encode(png).decode("ascii")
                    )
    payload = {
        "manifest": load("00-manifest.json"),
        "validation": validation,
        "extraction": extracted,
        "normalization": normalized,
        "chunks": chunks,
        "embeddings": embeddings,
        "retrieval": retrieval,
        "source_images": preview_images,
    }
    template = Path(__file__).with_name("walkthrough.html").read_text(encoding="utf-8")
    packed = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    fragment = template.replace("__ELEPHANT_DATA__", packed)
    assert len(fragment.encode("utf-8")) < 1_000_000
    (OUT / "elephant-pipeline.html").write_text(fragment, encoding="utf-8")
    browser_template = Path(__file__).with_name("viewer.html").read_text(encoding="utf-8")
    (OUT / "index.html").write_text(
        browser_template.replace("__WALKTHROUGH_FRAGMENT__", fragment), encoding="utf-8"
    )
    with ZipFile(ROOT / "output" / "elephant-walkthrough-data.zip", "w", ZIP_DEFLATED) as bundle:
        for path in sorted(OUT.iterdir()):
            if path.suffix in {".json", ".md"} or path.name == "index.html":
                bundle.write(path, "data/" + path.name)
        for path in (SOURCE_PDF, REPORT_PDF):
            bundle.write(path, "pdf/" + path.name)
    print(f"Created walkthrough PDF: {REPORT_PDF.name}", flush=True)


def view(port: int, *, open_browser: bool) -> None:
    import webbrowser
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    if not (OUT / "index.html").is_file():
        raise FileNotFoundError("No browser walkthrough found. Run 'elephant-rag report' first.")
    handler = partial(SimpleHTTPRequestHandler, directory=str(OUT))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        address = f"http://127.0.0.1:{server.server_port}/"
        print(f"Elephant walkthrough: {address} (Ctrl+C to stop)", flush=True)
        if open_browser:
            webbrowser.open(address)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["prepare", "embed", "report", "all", "view"])
    parser.add_argument(
        "--port", type=int, default=8765, help="Loopback port for view (default 8765)"
    )
    parser.add_argument("--open", action="store_true", help="Open view in the default browser")
    args = parser.parse_args()
    try:
        if args.stage == "view":
            view(args.port, open_browser=args.open)
            return 0
        for stage, operation in (("prepare", prepare), ("embed", embed), ("report", report)):
            if args.stage in (stage, "all"):
                operation()
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"Could not complete {args.stage}: {exc}", file=sys.stderr)
        print(
            "Run 'elephant-rag all' from the project directory to build every stage.",
            file=sys.stderr,
        )
        return 2
    return 0
