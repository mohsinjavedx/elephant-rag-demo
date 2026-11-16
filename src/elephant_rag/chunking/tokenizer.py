"""An offline cl100k_base tokenizer; uploaded special-token strings are plain data."""

import base64
import json
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

import tiktoken


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    assets = Path(__file__).with_name("assets")
    config = json.loads((assets / "cl100k_base.json").read_text(encoding="utf-8"))
    data = (assets / "cl100k_base.tiktoken").read_bytes()
    if sha256(data).hexdigest() != config["sha256"]:
        raise RuntimeError("Bundled tokenizer checksum mismatch")
    ranks = {
        base64.b64decode(token): int(rank)
        for token, rank in (line.split() for line in data.splitlines())
    }
    return tiktoken.Encoding(
        name=config["name"],
        pat_str=config["pat_str"],
        mergeable_ranks=ranks,
        special_tokens=config["special_tokens"],
    )


def token_count(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))
