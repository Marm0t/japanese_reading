#!/usr/bin/env python3
"""Validate all checked-in Yomu JSON files."""

import json
from pathlib import Path
import re

from generate_data import romaji

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "data").glob("*.json"))
assert len(files) == 8, f"expected 8 datasets, found {len(files)}"
all_ids = set()

for path in files:
    course, level_text = path.stem.split("-")
    level = int(level_text)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert rows and isinstance(rows, list), f"{path}: expected a non-empty array"
    if level == 2: assert len(rows) >= 200, f"{path}: expected at least 200 curated entries"
    if level > 2: assert len(rows) >= 500, f"{path}: expected at least 500 entries"
    seen_questions = set()
    for index, row in enumerate(rows):
        where = f"{path.name}[{index}]"
        assert set(row) <= {"id", "kana", "romaji", "kanji", "translation", "source", "sourceId"}, f"{where}: unknown field"
        assert row.get("id") and row["id"] not in all_ids, f"{where}: duplicate or missing id"
        all_ids.add(row["id"])
        assert row.get("kana") and row["kana"] not in seen_questions, f"{where}: duplicate or missing kana"
        seen_questions.add(row["kana"])
        assert isinstance(row.get("romaji"), list) and all(row["romaji"]), f"{where}: invalid romaji"
        assert all(re.fullmatch(r"[A-Za-z '\-]+", value) for value in row["romaji"]), f"{where}: romaji must be Latin"
        kana_words = row["kana"].split()
        for answer in row["romaji"]:
            answer_words = answer.split()
            if any("っ" in word or "ッ" in word for word in kana_words):
                assert len(answer_words) == len(kana_words), f"{where}: kana/romaji word count mismatch"
                for kana_word, answer_word in zip(kana_words, answer_words):
                    if "っ" in kana_word or "ッ" in kana_word:
                        assert answer_word == romaji(kana_word), f"{where}: missing or invalid small-tsu gemination"
        compact = row["kana"].replace(" ", "")
        if level == 1:
            assert "translation" not in row and "kanji" not in row, f"{where}: level 1 has hints"
        else:
            assert row.get("translation"), f"{where}: translation required"
            assert row.get("source") in {"curated", "JMdict", "Tatoeba"} and row.get("sourceId"), f"{where}: source metadata required"
        if level == 2:
            assert 2 <= len(compact) <= 4 or compact in {"き", "は"}, f"{where}: level 2 length"
            if course == "hiragana":
                assert "っ" not in compact and "ー" not in compact, f"{where}: advanced mark in hiragana level 2"
        if level == 4:
            assert len(row["kana"]) <= 30, f"{where}: sentence too long"
    print(f"{path.name}: {len(rows)} valid entries")

print(f"Total: {len(all_ids)} valid entries")
