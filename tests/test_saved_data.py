"""Validate the recorded evidence and measured vector scores without a model download."""

import json
import math
from pathlib import Path

import pytest

OUTPUT = Path(__file__).resolve().parents[1] / "output" / "elephant-walkthrough"


def read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("configuration", ["default", "teaching"])
def test_recorded_rankings_match_the_real_vectors(configuration):
    embeddings = read("05-embeddings.json")
    retrieval = read("06-retrieval.json")["chunk_sets"][configuration]
    records = embeddings["chunk_sets"][configuration]
    by_id = {record["chunk_id"]: record for record in records}
    for record in records + embeddings["queries"]:
        vector = record["vector"]
        assert len(vector) == 384
        assert all(math.isfinite(value) for value in vector)
        assert math.sqrt(sum(value * value for value in vector)) == pytest.approx(1, abs=1e-5)
        assert 0 < len(record["token_ids"]) <= 512
        assert len(record["token_ids"]) == len(record["token_pieces"])
    for query, results in zip(embeddings["queries"], retrieval, strict=True):
        matches = results["all_ranked_matches"]
        assert len({match["chunk_id"] for match in matches}) == len(records)
        scores = [match["cosine_similarity"] for match in matches]
        assert scores == sorted(scores, reverse=True)
        for match in matches:
            record = by_id[match["chunk_id"]]
            assert match["text"] == record["embedding_input"]
            similarity = sum(a * b for a, b in zip(record["vector"], query["vector"], strict=True))
            assert match["cosine_similarity"] == pytest.approx(similarity, abs=1e-6)


@pytest.mark.parametrize(
    ("question_index", "evidence"),
    [
        (0, "pours it into its mouth"),
        (1, "molars grind plant food"),
        (2, "four legs"),
        (3, "cool blood"),
        (4, "savanna elephants"),
    ],
)
def test_best_saved_passage_contains_evidence_for_the_question(question_index, evidence):
    result = read("06-retrieval.json")["chunk_sets"]["teaching"][question_index]
    assert evidence in result["all_ranked_matches"][0]["text"]
