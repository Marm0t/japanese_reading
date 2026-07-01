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
from generate_data import HIRA_2, KATA_2, entry, hira, parse, romaji  # noqa: E402

PHRASE_TARGET = 500
WORD_TARGET = 300
KATA_RE = re.compile(r"[ァ-ヺー]")
KANJI_RE = re.compile(r"[一-龯々]")
HIRA_ONLY_RE = re.compile(r"[ぁ-ゖ]+")
KATA_ONLY_RE = re.compile(r"[ァ-ヺ]+")
SAFE_JAPANESE_RE = re.compile(r"^[ぁ-ゖァ-ヺー一-龯々。、！？・\d]+$")
BAD_GLOSS = re.compile(r"(surname|given name|place name|archaic|obsolete|vulgar|derogatory|slang)", re.I)
BAD_BEGINNER_DOMAIN = re.compile(
    r"\b(legal|judicial|legislative|political|military|financial|economic|anatomical|medical|chemical|"
    r"linguistic|mathematical|philosophical|religious|computing|engineering|construction|geological|"
    r"historical|tax|investment|securities|corporate|parliament|government|regulation|administration)\b",
    re.I,
)
PUNCT = set("。、！？・「」『』〜～")
THEME_TERMS = {
    "animal", "pet", "dog", "puppy", "cat", "kitten", "bird", "fish", "horse", "cow", "pig", "sheep", "goat", "rabbit", "mouse", "rat",
    "bear", "panda", "monkey", "fox", "deer", "tiger", "lion", "elephant", "giraffe", "camel", "koala", "frog", "turtle", "snake", "lizard",
    "insect", "bug", "bee", "ant", "butterfly", "spider", "crab", "shrimp", "octopus", "whale", "dolphin", "squirrel", "chicken", "duck",
    "tree", "flower", "plant", "grass", "leaf", "leaves", "branch", "root", "seed", "fruit", "berry", "mushroom", "bamboo", "rose", "moss",
    "nature", "sky", "sun", "moon", "star", "cloud", "rain", "snow", "wind", "storm", "thunder", "weather", "river", "sea", "ocean", "lake",
    "pond", "mountain", "hill", "valley", "island", "forest", "wood", "field", "sand", "stone", "rock", "fire", "water", "ice", "air", "light",
    "shadow", "morning", "noon", "evening", "night", "today", "tomorrow", "yesterday", "spring", "summer", "autumn", "winter",
    "food", "meal", "breakfast", "lunch", "dinner", "rice", "bread", "noodle", "soup", "salad", "meat", "beef", "pork", "egg", "milk",
    "cheese", "butter", "sugar", "salt", "pepper", "tea", "coffee", "juice", "cake", "pie", "candy", "chocolate", "cookie", "apple", "orange",
    "lemon", "banana", "peach", "pear", "grape", "melon", "strawberry", "tomato", "potato", "carrot", "onion", "cabbage", "bean", "vegetable",
    "bowl", "plate", "dish", "cup", "glass", "spoon", "fork", "knife", "chopsticks", "kettle", "pot", "pan", "bottle", "kitchen",
    "home", "house", "room", "door", "window", "wall", "floor", "roof", "garden", "bath", "toilet", "bed", "desk", "table", "chair", "sofa", "shelf",
    "box", "bag", "basket", "clock", "watch", "lamp", "mirror", "key", "lock", "towel", "soap", "brush", "comb", "phone", "camera", "television",
    "radio", "computer", "remote control", "air conditioner", "refrigerator", "washing machine", "sewing machine", "umbrella", "money", "wallet",
    "clothes", "clothing", "shirt", "skirt", "dress", "coat", "jacket", "suit", "pants", "trousers", "sock", "shoe", "hat", "cap", "belt", "ribbon", "pajamas",
    "toy", "doll", "ball", "game", "puzzle", "kite", "card", "playing cards", "music", "song", "movie", "book", "picture", "photo", "photograph", "art",
    "piano", "guitar", "drum", "dance", "tennis", "golf", "baseball", "soccer", "camp", "picnic", "hobby", "school", "class", "student", "teacher",
    "pupil", "pen", "pencil", "eraser", "notebook", "paper", "letter", "textbook", "dictionary", "ruler", "scissors", "glue", "ink", "memo", "test",
    "family", "parent", "father", "mother", "dad", "mom", "brother", "sister", "uncle", "aunt", "grandfather", "grandmother", "husband", "wife", "child", "baby", "friend",
    "body", "head", "face", "hair", "eye", "ear", "nose", "mouth", "tooth", "teeth", "tongue", "neck", "shoulder", "arm", "hand", "finger", "chest", "back",
    "stomach", "leg", "foot", "feet", "heart", "skin", "voice", "shop", "store", "market", "park", "station", "airport", "hotel", "restaurant", "cafe",
    "hospital", "library", "museum", "zoo", "town", "city", "village", "road", "street", "bridge", "car", "bus", "train", "taxi", "bicycle", "motorcycle", "boat", "ship", "plane",
}
BASIC_ACTIONS = {
    "be", "have", "do", "make", "go", "come", "return", "stop", "start", "wait", "walk", "run", "jump", "swim", "fly", "sit", "stand", "sleep", "wake",
    "see", "look", "watch", "hear", "listen", "say", "speak", "talk", "ask", "answer", "read", "write", "draw", "sing", "dance", "play", "study", "learn", "teach",
    "eat", "drink", "cook", "wash", "clean", "cut", "open", "close", "put", "take", "bring", "carry", "hold", "give", "receive", "buy", "sell", "pay", "use",
    "wear", "enter", "leave", "meet", "call", "help", "show", "find", "lose", "catch", "throw", "pick", "choose", "know", "understand", "think", "remember", "forget",
    "like", "love", "want", "need", "live", "laugh", "cry", "smile", "rain", "snow", "shine", "grow", "fall", "turn", "touch", "push", "pull",
}
BASIC_QUALITIES = {
    "big", "small", "large", "little", "long", "short", "high", "low", "tall", "new", "old", "young", "good", "bad", "hot", "cold", "warm", "cool",
    "bright", "dark", "fast", "slow", "early", "late", "heavy", "light", "strong", "weak", "easy", "difficult", "hard", "soft", "sweet", "sour", "salty",
    "bitter", "delicious", "cute", "pretty", "beautiful", "clean", "dirty", "quiet", "noisy", "red", "blue", "white", "black", "yellow", "green", "round",
    "happy", "sad", "fun", "kind", "healthy", "hungry", "thirsty", "near", "far", "wide", "narrow", "right", "left", "same", "different",
}
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

HIRA_2_EXTRA = parse("""
うし|牛|cow
ぶた|豚|pig
やぎ|山羊|goat
くま|熊|bear
きつね|狐|fox
しか|鹿|deer
とら|虎|tiger
ぞう|象|elephant
うさぎ|兎|rabbit
ねずみ|鼠|mouse
かえる|蛙|frog
かめ|亀|turtle
へび|蛇|snake
とかげ|蜥蜴|lizard
あり|蟻|ant
はち|蜂|bee
くも|蜘蛛|spider
えび|海老|shrimp
いか|烏賊|squid
くじら|鯨|whale
いるか|海豚|dolphin
すずめ|雀|sparrow
からす|烏|crow
はと|鳩|pigeon
あひる|家鴨|duck
き|木|tree
は|葉|leaf
たね|種|seed
たけ|竹|bamboo
こけ|苔|moss
きのこ|茸|mushroom
ばら|薔薇|rose
たいよう|太陽|sun
ひかり|光|light
かげ|影|shadow
いけ|池|pond
すな|砂|sand
いし|石|stone
ほのお|炎|flame
りんご|林檎|apple
みかん|蜜柑|mandarin orange
ぶどう|葡萄|grape
いちご|苺|strawberry
すいか|西瓜|watermelon
やさい|野菜|vegetable
にんじん|人参|carrot
たまねぎ|玉葱|onion
だいこん|大根|daikon radish
きゅうり|胡瓜|cucumber
ぶたにく|豚肉|pork
とりにく|鶏肉|chicken meat
さとう|砂糖|sugar
こしょう|胡椒|pepper
おちゃ|お茶|tea
えんぴつ|鉛筆|pencil
けしごむ|消しゴム|eraser
ほん|本|book
えほん|絵本|picture book
てがみ|手紙|letter
ふで|筆|writing brush
はさみ|鋏|scissors
のり|糊|glue
かばん|鞄|bag
でんわ|電話|telephone
とけい|時計|clock
かがみ|鏡|mirror
ふとん|布団|futon
まくら|枕|pillow
たべる|食べる|to eat
きく|聞く|to listen
はなす|話す|to speak
いう|言う|to say
よむ|読む|to read
かく|書く|to write
えがく|描く|to draw
うたう|歌う|to sing
おどる|踊る|to dance
あそぶ|遊ぶ|to play
あるく|歩く|to walk
はしる|走る|to run
およぐ|泳ぐ|to swim
とぶ|飛ぶ|to fly
すわる|座る|to sit
たつ|立つ|to stand
ねる|寝る|to sleep
おきる|起きる|to wake up
まつ|待つ|to wait
あう|会う|to meet
いく|行く|to go
くる|来る|to come
かえる|帰る|to return home
あける|開ける|to open
しめる|閉める|to close
あらう|洗う|to wash
つかう|使う|to use
もつ|持つ|to hold
おく|置く|to put
とる|取る|to take
かう|買う|to buy
うる|売る|to sell
すき|好き|liked
きらい|嫌い|disliked
おいしい|美味しい|delicious
あまい|甘い|sweet
からい|辛い|spicy
にがい|苦い|bitter
あつい|暑い|hot
さむい|寒い|cold
つめたい|冷たい|cold to the touch
はやい|早い|early
おそい|遅い|slow
おおきい|大きい|big
ちいさい|小さい|small
ながい|長い|long
みじかい|短い|short
たかい|高い|high
ひくい|低い|low
おもい|重い|heavy
かるい|軽い|light
つよい|強い|strong
よわい|弱い|weak
あかるい|明るい|bright
くらい|暗い|dark
たのしい|楽しい|fun
かなしい|悲しい|sad
かわいい|可愛い|cute
きれい|綺麗|beautiful
""")

KATA_2_EXTRA = parse("""
バッグ||bag
マップ||map
キッズ||kids
ブック||book
フルーツ||fruit
ヨット||yacht
ロケット||rocket
クッキー||cookie
キッチン||kitchen
ドール||doll
ブロック||building block
バット||baseball bat
ラケット||racket
ケーキ||cake
ゲーム||game
コート||coat
コピー||copy
スープ||soup
スキー||skiing
ボール||ball
プール||swimming pool
ベッド||bed
ペット||pet
チーズ||cheese
カード||card
カレー||curry
シール||sticker
ジュース||juice
スーツ||suit
セーター||sweater
ゼリー||jelly
チーム||team
ニュース||news
ノート||notebook
バター||butter
ビール||beer
カップ||cup
コップ||cup
ギター||guitar
クリーム||cream
グループ||group
ケース||case
ショー||show
スカート||skirt
スポーツ||sport
タクシー||taxi
チケット||ticket
デート||date
アルバム||album
ウイルス||virus
ウエスト||waist
ガイド||guide
ガラス||glass
キロ||kilogram
クラス||class
グラフ||graph
サイレン||siren
サラダ||salad
タオル||towel
ダンス||dance
テンポ||tempo
ディスコ||disco
ドレス||dress
ナイフ||knife
ナイロン||nylon
ハウス||house
パン||bread
パンダ||panda
プリント||printout
ベンチ||bench
ホテル||hotel
ミニ||mini
メディア||media
モデル||model
ラジオ||radio
ランチ||lunch
レベル||level
レモン||lemon
ブラシ||brush
エンジン||engine
カメラ||camera
シングル||single
スタジオ||studio
スタンド||stand
テニス||tennis
デザイン||design
トイレ||toilet
トンネル||tunnel
ハンドル||steering wheel
バナナ||banana
バレエ||ballet
ミリ||millimeter
リズム||rhythm
リボン||ribbon
ダイヤ||diamond
チキン||chicken
パジャマ||pajamas
ビタミン||vitamin
ベランダ||balcony
ポスト||mailbox
ミサイル||missile
ミス||mistake
アルミ||aluminum
ハンサム||handsome
マラソン||marathon
サイン||signature
ドリル||drill
ネオン||neon
ピンポン||table tennis
テレビ||television
バイク||motorcycle
パンツ||pants
マスク||mask
ハンカチ||handkerchief
プロ||professional
バイト||part-time job
スタイル||style
ステレオ||stereo
ミシン||sewing machine
リモコン||remote control
エアコン||air conditioner
パソコン||personal computer
ピント||focus
ピアノ||piano
シャツ||shirt
ハム||ham
ビル||building
オレンジ||orange
グラス||drinking glass
トランプ||playing cards
オルガン||organ
アイロン||clothes iron
キャベツ||cabbage
ベルト||belt
トマト||tomato
ビデオ||video
ピン||pin
センス||good taste
テスト||test
ドラマ||television drama
カタカナ||katakana
スマホ||smartphone
アプリ||app
ウェブ||web
ジム||gym
ソファ||sofa
デスク||desk
ドラム||drum
フォト||photo
ボイス||voice
ランプ||lamp
コアラ||koala
コブラ||cobra
サウナ||sauna
デニム||denim
チェス||chess
チェロ||cello
チャイム||chime
ドリンク||drink
ノイズ||noise
""")


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


def theme_score(gloss, pos):
    """Return a positive score only for useful beginner vocabulary."""
    text = gloss.lower().strip()
    if BAD_GLOSS.search(text) or BAD_BEGINNER_DOMAIN.search(text):
        return 0
    score = 0
    for term in THEME_TERMS:
        if re.search(rf"(?<![a-z]){re.escape(term)}(?![a-z])", text):
            score = max(score, 120 + min(len(term), 20))
    if text.startswith("to "):
        first = re.match(r"to ([a-z]+)", text)
        if first and first.group(1) in BASIC_ACTIONS:
            score = max(score, 115)
    if set(re.findall(r"[a-z]+", text)) & BASIC_QUALITIES:
        score = max(score, 110)
    if score:
        if any("noun (common)" in value for value in pos): score += 15
        if any(value.startswith("Ichidan verb") or value.startswith("Godan verb") for value in pos): score += 15
        if any("adjective" in value for value in pos): score += 10
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
            ranked_glosses = sorted(((theme_score(value, pos), value) for value in glosses if len(value) <= 60), reverse=True)
            if not ranked_glosses or ranked_glosses[0][0] <= 0:
                node.clear(); continue
            topic_score, gloss = ranked_glosses[0]
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
                pools[course].append({"source_id": seq, "kana": reading, "kanji": None if no_kanji else written, "translation": gloss, "score": score, "topic_score": topic_score})
            node.clear()

    result = {}
    for course, candidates in pools.items():
        # Stable, high-frequency-first selection with one card per reading.
        candidates.sort(key=lambda x: (-x["topic_score"], -x["score"], len(x["translation"]), int(x["source_id"])))
        chosen, seen = [], set()
        for item in candidates:
            if item["kana"] in seen:
                continue
            seen.add(item["kana"]); chosen.append(item)
            if len(chosen) == WORD_TARGET:
                break
        if len(chosen) < 200:
            raise RuntimeError(f"Only {len(chosen)} suitable {course} words")
        result[course] = chosen
    return result


def load_curated_words():
    result = {}
    for course, rows in {
        # Explicit additions take precedence when a reading has several senses
        # (e.g. きく = "to listen" rather than 菊 = "chrysanthemum").
        "hiragana": [*HIRA_2_EXTRA, *HIRA_2],
        "katakana": [*KATA_2_EXTRA, *KATA_2],
    }.items():
        chosen, seen = [], set()
        for kana, kanji, translation, _custom_romaji in rows:
            if course == "katakana" and kana in {"ウイルス", "カルテ", "ミサイル", "リスク", "ワイン", "ビール"}:
                continue
            if kana in seen:
                continue
            advanced_mark = "っ" in kana or (course == "hiragana" and "ー" in kana)
            if not (2 <= len(kana) <= 4 or kana in {"き", "は"}) or advanced_mark:
                raise RuntimeError(f"Invalid curated level-2 word: {kana}")
            seen.add(kana)
            chosen.append({
                "source_id": f"{course}-{len(chosen) + 1:03d}",
                "kana": kana,
                "kanji": kanji,
                "translation": translation,
            })
        if len(chosen) < 200:
            raise RuntimeError(f"Only {len(chosen)} curated {course} words")
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
        if len(selected) == PHRASE_TARGET:
            break
    if len(selected) < PHRASE_TARGET:
        raise RuntimeError(f"Only {len(selected)} diverse {course} level-{level} phrases from {len(pool)} candidates")
    return selected


def write_words(course, rows):
    output = []
    prefix = f"{course}02"
    for index, row in enumerate(rows, 1):
        item = entry(prefix, index, row["kana"], row["kanji"], row["translation"])
        suffix = hashlib.sha1(row["kana"].encode("utf-8")).hexdigest()[:8]
        item["id"] = f"curated-{course}-{suffix}"
        item.update({"source": "curated", "sourceId": row["source_id"]})
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
    words = load_curated_words()
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
