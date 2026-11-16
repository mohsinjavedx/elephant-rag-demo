"""Catch missing package wiring and a CLI that silently drops source text."""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def test_prepare_runs_in_a_fresh_directory_without_the_main_project(tmp_path):
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-m", "elephant_rag", "prepare"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    output = tmp_path / "output" / "elephant-walkthrough"
    validation = json.loads((output / "01-validation.json").read_text(encoding="utf-8"))
    assert validation["page_count"] == 3
    assert validation["staged_file_deleted_after_context"]
    assert validation["staged_directory_deleted_after_context"]
    pages = json.loads((output / "03-normalized.json").read_text(encoding="utf-8"))["pages"]
    assert sum(len(p["removed_boundaries"]) for p in pages) == 6
    groups = json.loads((output / "04-chunks.json").read_text(encoding="utf-8"))
    for group in groups.values():
        for page in pages:
            covered = set()
            for chunk in group["chunks"]:
                if chunk["page_start"] != page["page_number"]:
                    continue
                start, end = chunk["char_start"], chunk["char_end"]
                assert page["raw_text"][start:end] == chunk["raw_text"]
                first = chunk["metadata"]["normalized_char_start"]
                last = chunk["metadata"]["normalized_char_end"]
                assert page["normalized_text"][first:last] == chunk["normalized_text"]
                covered.update(range(first, last))
            assert all(
                i in covered for i, c in enumerate(page["normalized_text"]) if not c.isspace()
            )


def test_report_exports_a_browser_page_from_saved_data_offline(tmp_path):
    output = tmp_path / "output"
    shutil.copytree(
        ROOT / "output" / "elephant-walkthrough",
        output / "elephant-walkthrough",
        ignore=shutil.ignore_patterns("*.html"),
    )
    shutil.copytree(ROOT / "output" / "pdf", output / "pdf")
    completed = subprocess.run(
        [sys.executable, "-m", "elephant_rag", "report"],
        cwd=tmp_path,
        env={**os.environ, "HF_HUB_OFFLINE": "1"},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    page = output / "elephant-walkthrough" / "index.html"
    assert page.is_file(), "report must export the working six-stage browser viewer"
    from html.parser import HTMLParser

    class ViewerParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.scripts = []
            self.is_dataset = False
            self.dataset = ""

        def handle_starttag(self, tag, attrs):
            if tag == "script":
                values = dict(attrs)
                self.scripts.append(values)
                self.is_dataset = values.get("id") == "elephant-data"

        def handle_endtag(self, tag):
            if tag == "script":
                self.is_dataset = False

        def handle_data(self, data):
            if self.is_dataset:
                self.dataset += data

    parsed = ViewerParser()
    parsed.feed(page.read_text(encoding="utf-8"))
    data = json.loads(parsed.dataset)
    assert len(data["chunks"]["teaching"]["chunks"]) >= 2
    assert len(data["embeddings"]["queries"]) == 5
    assert all("src" not in script for script in parsed.scripts), "viewer must work offline"


def test_view_serves_generated_output_without_exposing_project_files(tmp_path):
    output = tmp_path / "output" / "elephant-walkthrough"
    output.mkdir(parents=True)
    (output / "index.html").write_text("<h1>Saved lesson</h1>", encoding="utf-8")
    (tmp_path / "private.txt").write_text("outside the served directory", encoding="utf-8")
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", 0))
        port = candidate.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "elephant_rag", "view", "--port", str(port)],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        deadline = time.monotonic() + 15
        while True:
            try:
                with urlopen(f"http://127.0.0.1:{port}/", timeout=1) as response:
                    assert response.read() == b"<h1>Saved lesson</h1>"
                break
            except URLError:
                if process.poll() is not None or time.monotonic() >= deadline:
                    stdout, stderr = process.communicate(timeout=5)
                    raise AssertionError((stdout + stderr).decode()) from None
                time.sleep(0.05)
        try:
            urlopen(f"http://127.0.0.1:{port}/private.txt", timeout=1)
        except URLError as exc:
            assert getattr(exc, "code", None) == 404
        else:
            raise AssertionError("view exposed a file outside its output directory")
    finally:
        process.terminate()
        process.communicate(timeout=5)
