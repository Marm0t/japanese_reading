#!/usr/bin/env python3
"""Validate all checked-in Yomu JSON files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = sorted((ROOT / "data").glob("*.json"))
assert len(files) == 8, f"expected 8 datasets, found {len(files)}"
all_ids = set()

for path in files:
    course, level_text = path.stem.split("-")
    level = int(level_text)
    rows = json.loads(path.read_text(encoding="utf-8"))
    assert rows and isinstance(rows, list), f"{path}: expected a non-empty array"
    if level > 1: assert len(rows) >= 100, f"{path}: expected at least 100 entries"
    seen_questions = set()
    for index, row in enumerate(rows):
        where = f"{path.name}[{index}]"
        assert set(row) <= {"id", "kana", "romaji", "kanji", "translation", "source", "sourceId"}, f"{where}: unknown field"
        assert row.get("id") and row["id"] not in all_ids, f"{where}: duplicate or missing id"
        all_ids.add(row["id"])
        assert row.get("kana") and row["kana"] not in seen_questions, f"{where}: duplicate or missing kana"
        seen_questions.add(row["kana"])
        assert isinstance(row.get("romaji"), list) and all(row["romaji"]), f"{where}: invalid romaji"
        compact = row["kana"].replace(" ", "")
        if level == 1:
            assert "translation" not in row and "kanji" not in row, f"{where}: level 1 has hints"
        else:
            assert row.get("translation"), f"{where}: translation required"
        if level == 2:
            assert 2 <= len(compact) <= 4, f"{where}: level 2 length"
            assert "っ" not in compact and "ッ" not in compact and "ー" not in compact, f"{where}: advanced mark in level 2"
        if level == 4:
            assert len(row["kana"]) <= 30, f"{where}: sentence too long"
    print(f"{path.name}: {len(rows)} valid entries")

print(f"Total: {len(all_ids)} valid entries")
