#!/usr/bin/env python3
"""Build levels 2-4 from reviewed JMdict and Tatoeba exports in ./tmp."""

import bz2
import gzip
import hashlib
import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tmp"
DATA = ROOT / "data"
sys.path.insert(0, str(TMP / "vendor"))
sys.path.insert(0, str(ROOT / "tools"))

from janome.tokenizer import Tokenizer  # noqa: E402
from generate_data import entry, hira, romaji  # noqa: E402

TARGET = 500
KATA_RE = re.compile(r"[ァ-ヺー]")
KANJI_RE = re.compile(r"[一-龯々]")
HIRA_ONLY_RE = re.compile(r"[ぁ-ゖ]+")
KATA_ONLY_RE = re.compile(r"[ァ-ヺ]+")
SAFE_JAPANESE_RE = re.compile(r"^[ぁ-ゖァ-ヺー一-龯々。、！？・\d]+$")
BAD_GLOSS = re.compile(r"(surname|given name|place name|archaic|obsolete|vulgar|derogatory|slang)", re.I)
PUNCT = set("。、！？・「」『』〜～")
BLOCKED_JMDICT = {
    "1296400", "1413140", "1444990", "1518120", "1410050", "1589190", "1579110", "1233560", "1580550", "1584690",
    "1054570", "1046810", "1121390", "1019210", "1042520", "1089090", "1098340", "1037560", "2154660", "1074260",
    "1040060", "1123880", "1023330", "1127070", "1015840", "1021920", "1021360", "1023840", "1028500", "1062920",
    "1105970", "2856157", "1080940", "1051440", "1064840", "1115100", "1144240", "1046820", "1139000", "1083820",
    "1144630", "1504900", "1586600", "1090270", "2842849",
}
BLOCKED_TATOEBA = {
    226201, 9628914, 9035024, 2182847, 8584585, 10306179, 162008, 10759983, 9963811,
    9101664, 10914822, 6849866, 9571553, 8452359, 158970, 182291, 11574620, 224201,
    10630165, 10736083, 192638, 11632683, 7357207,
}


def require_files():
    names = ["JMdict_e.gz", "jpn_sentences.tsv.bz2", "eng_sentences.tsv.bz2", "jpn-eng_links.tsv.bz2", "jpn_transcriptions.tsv.bz2"]
    missing = [name for name in names if not (TMP / name).exists()]
    if missing:
        raise SystemExit(f"Missing source files in tmp: {', '.join(missing)}")


def priority_score(tags):
    score = 0
    for tag in tags:
        if tag in {"news1", "ichi1", "spec1", "gai1"}: score += 100
        elif tag in {"news2", "ichi2", "spec2", "gai2"}: score += 50
        elif tag.startswith("nf"):
            try: score += max(1, 50 - int(tag[2:]))
            except ValueError: pass
    return score


def load_words():
    pools = {"hiragana": [], "katakana": []}
    with gzip.open(TMP / "JMdict_e.gz", "rb") as stream:
        for _, node in ET.iterparse(stream, events=("end",)):
            if node.tag != "entry":
                continue
            seq = node.findtext("ent_seq")
            if seq in BLOCKED_JMDICT:
                node.clear(); continue
            senses = node.findall("sense")
            glosses = [g.text.strip() for s in senses for g in s.findall("gloss") if g.text and g.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "eng") == "eng"]
            pos = {p.text or "" for s in senses for p in s.findall("pos")}
            if not glosses or any("proper noun" in p for p in pos):
                node.clear(); continue
            gloss = glosses[0]
            if BAD_GLOSS.search(gloss) or len(gloss) > 60:
                node.clear(); continue
            writings = [(k.findtext("keb"), priority_score([p.text or "" for p in k.findall("ke_pri")])) for k in node.findall("k_ele")]
            for reading_node in node.findall("r_ele"):
                reading = reading_node.findtext("reb", "")
                if not (2 <= len(reading) <= 4) or any(c in reading for c in "っッー"):
                    continue
                course = "hiragana" if HIRA_ONLY_RE.fullmatch(reading) else "katakana" if KATA_ONLY_RE.fullmatch(reading) else None
                if not course:
                    continue
                r_tags = [p.text or "" for p in reading_node.findall("re_pri")]
                score = priority_score(r_tags)
                if score <= 0:
                    continue
                restrictions = {x.text for x in reading_node.findall("re_restr")}
                choices = [(word, rank) for word, rank in writings if not restrictions or word in restrictions]
                written = max(choices, key=lambda pair: pair[1])[0] if choices else None
                # Prefer kana-only spelling when JMdict explicitly marks it so.
                no_kanji = reading_node.find("re_nokanji") is not None
                # Katakana ateji in JMdict are often historical curiosities, not modern spellings.
                if course == "katakana": written = None
                pools[course].append({"source_id": seq, "kana": reading, "kanji": None if no_kanji else written, "translation": gloss, "score": score})
            node.clear()

    result = {}
    for course, candidates in pools.items():
        # Stable, high-frequency-first selection with one card per reading.
        candidates.sort(key=lambda x: (-x["score"], len(x["translation"]), int(x["source_id"])))
        chosen, seen = [], set()
        for item in candidates:
            if item["kana"] in seen:
                continue
            seen.add(item["kana"]); chosen.append(item)
            if len(chosen) == TARGET:
                break
        if len(chosen) < TARGET:
            raise RuntimeError(f"Only {len(chosen)} suitable {course} words")
        result[course] = chosen
    return result


def load_tsv(path):
    with bz2.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield line.rstrip("\n").split("\t")


def transcription_to_kana(value):
    def expand(match):
        parts = match.group(1).split("|")
        return "".join(parts[1:]) if len(parts) > 1 else parts[0]
    value = re.sub(r"\[([^\]]+)\]", expand, value)
    return value if not KANJI_RE.search(value) else None


def normalize_kana(value):
    return re.sub(r"[\s。、！？・「」『』〜～]", "", value)


def kata_to_hira(value):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in value)


def tokenized_reading(tokenizer, text):
    groups = []
    group_romaji = []
    lemmas = []
    previous = None
    for token in tokenizer.tokenize(text):
        surface = token.surface
        pos = token.part_of_speech.split(",")
        if all(c in PUNCT for c in surface):
            if groups: groups[-1] += surface
            continue
        reading = token.reading
        if reading == "*":
            reading = surface
        # Preserve genuine katakana; render everything else as hiragana.
        if KATA_RE.search(surface) and not KANJI_RE.search(surface):
            rendered = surface
        else:
            rendered = kata_to_hira(reading)
        pronounced = {"は": "wa", "へ": "e", "を": "o"}.get(surface, romaji(rendered)) if pos[0] == "助詞" else romaji(rendered)
        attach = (
            pos[0] == "助動詞"
            or pos[1] in {"接尾", "非自立"}
            or (pos[0] == "助詞" and pos[1] == "接続助詞")
            or (
                token.base_form == "する"
                and previous is not None
                and (
                    "サ変接続" in previous.part_of_speech
                    or previous.part_of_speech.startswith("形容詞")
                )
            )
        )
        if attach and groups:
            groups[-1] += rendered
            group_romaji[-1] += pronounced
        else:
            groups.append(rendered)
            group_romaji.append(pronounced)
        if pos[0] not in {"助詞", "助動詞", "記号"}:
            lemmas.append(token.base_form if token.base_form != "*" else surface)
        previous = token
    return groups, lemmas, " ".join(group_romaji)


def load_sentences():
    links = defaultdict(list)
    english_ids = set()
    for left, right, *_ in load_tsv(TMP / "jpn-eng_links.tsv.bz2"):
        links[int(left)].append(int(right)); english_ids.add(int(right))

    english = {}
    for sid, _lang, text, *_ in load_tsv(TMP / "eng_sentences.tsv.bz2"):
        number = int(sid)
        if number in english_ids and 1 <= len(text) <= 100:
            english[number] = text

    transcriptions = {}
    for sid, _lang, script, editor, text, *_ in load_tsv(TMP / "jpn_transcriptions.tsv.bz2"):
        if script != "Hrkt" or not editor:
            continue
        kana = transcription_to_kana(text)
        if kana:
            transcriptions[int(sid)] = kana

    tokenizer = Tokenizer()
    candidates = []
    for sid, _lang, text, *_ in load_tsv(TMP / "jpn_sentences.tsv.bz2"):
        number = int(sid)
        if number in BLOCKED_TATOEBA:
            continue
        if number not in transcriptions or number not in links or not (3 <= len(text) <= 32):
            continue
        if not SAFE_JAPANESE_RE.fullmatch(text):
            continue
        translation = next((english[eid] for eid in links[number] if eid in english), None)
        if not translation:
            continue
        groups, lemmas, romanized = tokenized_reading(tokenizer, text)
        if not (2 <= len(groups) <= 12):
            continue
        kana = " ".join(groups)
        if any(group and group[0] in "ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ" for group in groups):
            continue
        if normalize_kana(kana_to_hiragana(kana)) != normalize_kana(kana_to_hiragana(transcriptions[number])):
            continue
        if len(kana) > 30:
            continue
        course = "katakana" if KATA_RE.search(text) else "hiragana"
        candidates.append({"source_id": number, "kana": kana, "kanji": text, "translation": translation, "groups": groups, "lemmas": lemmas, "course": course, "romaji": romanized})
    return candidates


def kana_to_hiragana(value):
    return kata_to_hira(value)


def shingles(value, size=3):
    value = normalize_kana(value)
    return {value[i:i + size] for i in range(max(1, len(value) - size + 1))}


def similarity(a, b):
    left, right = shingles(a), shingles(b)
    return len(left & right) / max(1, len(left | right))


def select_diverse(candidates, course, level):
    pool = []
    seen_kana = set()
    for item in candidates:
        if item["course"] != course or item["kana"] in seen_kana:
            continue
        words = [g for g in item["groups"] if not all(c in PUNCT for c in g)]
        if level == 3:
            if not (2 <= len(words) <= 4) or any(len(re.sub(r"[。、！？]", "", word)) > 5 for word in words):
                continue
        else:
            if len(words) < 5 or item["kanji"][-1:] not in "。！？":
                continue
        seen_kana.add(item["kana"]); pool.append(item)

    random.Random(20260701 + level + (10 if course == "katakana" else 0)).shuffle(pool)
    selected = []
    lemma_counts = Counter()
    for item in pool:
        content = [x for x in item["lemmas"] if len(x) > 1]
        if any(lemma_counts[x] >= 12 for x in content):
            continue
        if any(similarity(item["kana"], old["kana"]) > 0.62 for old in selected):
            continue
        selected.append(item)
        lemma_counts.update(set(content))
        if len(selected) == TARGET:
            break
    if len(selected) < TARGET:
        raise RuntimeError(f"Only {len(selected)} diverse {course} level-{level} phrases from {len(pool)} candidates")
    return selected


def write_words(course, rows):
    output = []
    prefix = f"{course}02"
    for index, row in enumerate(rows, 1):
        item = entry(prefix, index, row["kana"], row["kanji"], row["translation"])
        suffix = hashlib.sha1(row["kana"].encode("utf-8")).hexdigest()[:8]
        item["id"] = f"jmdict-{row['source_id']}-{suffix}"
        item.update({"source": "JMdict", "sourceId": int(row["source_id"])})
        output.append(item)
    (DATA / f"{course}-02.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_phrases(course, level, rows):
    output = []
    prefix = f"{course}{level:02d}"
    for index, row in enumerate(rows, 1):
        item = entry(prefix, index, row["kana"], row["kanji"], row["translation"], row["romaji"])
        item["id"] = f"tatoeba-{row['source_id']}"
        if any(not re.fullmatch(r"[A-Za-z '\-]+", value) for value in item["romaji"]):
            raise RuntimeError(f"Non-Latin romaji for {row['kana']}: {item['romaji']}")
        item.update({"source": "Tatoeba", "sourceId": row["source_id"]})
        output.append(item)
    (DATA / f"{course}-{level:02d}.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    require_files()
    words = load_words()
    for course in ("hiragana", "katakana"):
        write_words(course, words[course]); print(f"{course}-02: {len(words[course])}")
    sentences = load_sentences()
    print(f"Tatoeba candidates after reading checks: {len(sentences)}")
    for course in ("hiragana", "katakana"):
        for level in (3, 4):
            chosen = select_diverse(sentences, course, level)
            write_phrases(course, level, chosen)
            print(f"{course}-{level:02d}: {len(chosen)}")


if __name__ == "__main__":
    main()
