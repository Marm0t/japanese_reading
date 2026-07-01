#!/usr/bin/env python3
"""Build Yomu's reviewed JSON datasets from the compact source lists below."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

BASE = {
    "あ":"a","い":"i","う":"u","え":"e","お":"o","か":"ka","き":"ki","く":"ku","け":"ke","こ":"ko",
    "さ":"sa","し":"shi","す":"su","せ":"se","そ":"so","た":"ta","ち":"chi","つ":"tsu","て":"te","と":"to",
    "な":"na","に":"ni","ぬ":"nu","ね":"ne","の":"no","は":"ha","ひ":"hi","ふ":"fu","へ":"he","ほ":"ho",
    "ま":"ma","み":"mi","む":"mu","め":"me","も":"mo","や":"ya","ゆ":"yu","よ":"yo","ら":"ra","り":"ri",
    "る":"ru","れ":"re","ろ":"ro","わ":"wa","を":"o","ん":"n","が":"ga","ぎ":"gi","ぐ":"gu","げ":"ge","ご":"go",
    "ざ":"za","じ":"ji","ず":"zu","ぜ":"ze","ぞ":"zo","だ":"da","ぢ":"ji","づ":"zu","で":"de","ど":"do",
    "ば":"ba","び":"bi","ぶ":"bu","べ":"be","ぼ":"bo","ぱ":"pa","ぴ":"pi","ぷ":"pu","ぺ":"pe","ぽ":"po",
    "ゔ":"vu"
}
SMALL = {"ゃ":"ya", "ゅ":"yu", "ょ":"yo", "ぁ":"a", "ぃ":"i", "ぅ":"u", "ぇ":"e", "ぉ":"o"}

def hira(text):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in text)

def romaji(text):
    text = hira(text)
    out, i = [], 0
    foreign = {"ふぁ":"fa", "ふぃ":"fi", "ふぇ":"fe", "ふぉ":"fo", "てぃ":"ti", "でぃ":"di", "うぃ":"wi", "うぇ":"we", "うぉ":"wo", "しぇ":"she", "じぇ":"je", "ちぇ":"che"}
    while i < len(text):
        c = text[i]
        if c == " ": out.append(" "); i += 1; continue
        if c in "。、！？": i += 1; continue
        if c == "っ":
            if i + 1 < len(text):
                nxt = BASE.get(text[i + 1], "")
                out.append("t" if nxt.startswith("ch") else nxt[:1])
            i += 1; continue
        if c == "ー":
            if out:
                for ch in reversed("".join(out)):
                    if ch in "aeiou": out.append(ch); break
            i += 1; continue
        if text[i:i + 2] in foreign:
            out.append(foreign[text[i:i + 2]]); i += 2; continue
        sound = BASE.get(c, "")
        if i + 1 < len(text) and text[i + 1] in SMALL and sound:
            glide = SMALL[text[i + 1]]
            if sound.endswith("i"):
                sound = sound[:-1] + glide
            elif c in "しじちぢ":
                sound = {"し":"sh", "じ":"j", "ち":"ch", "ぢ":"j"}[c] + glide[1:]
            i += 1
        out.append(sound or c); i += 1
    value = "".join(out)
    # Particles are written as kana but pronounced differently.
    words = value.split(" ")
    source_words = hira(text).split(" ")
    for n, source in enumerate(source_words):
        if source == "は": words[n] = "wa"
        elif source == "へ": words[n] = "e"
        elif source == "を": words[n] = "o"
    return " ".join(words)

def parse(block):
    rows = []
    for line in block.strip().splitlines():
        parts = [part.strip() for part in line.split("|")]
        rows.append((parts + [None] * 4)[:4])
    return rows

def entry(prefix, number, kana, kanji=None, translation=None, custom_romaji=None):
    reading = custom_romaji or romaji(kana)
    variants = [reading]
    # Accept the common IME spelling and Hepburn n-apostrophe distinction alike.
    if "n'" in reading: variants.append(reading.replace("n'", "n"))
    if "ー" in kana:
        variants.extend([reading.replace("oo", "ou"), reading.replace("aa", "a").replace("ii", "i").replace("uu", "u").replace("ee", "e").replace("oo", "o")])
        variants = list(dict.fromkeys(variants))
    return {k: v for k, v in {
        "id": f"{prefix}-{number:03d}", "kana": kana, "romaji": variants,
        "kanji": kanji or None, "translation": translation or None
    }.items() if v is not None}

def write(name, rows):
    payload = [entry(name.replace("-", ""), i, *row) for i, row in enumerate(rows, 1)]
    (DATA / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def level_one(script):
    base = list(BASE)
    digraph_stems = "きぎしじちぢにひびぴみり"
    signs = base + [stem + small for stem in digraph_stems for small in "ゃゅょ"]
    if script == "katakana": signs = ["".join(chr(ord(c) + 0x60) for c in sign) for sign in signs]
    return [(sign, None, None, None) for sign in signs]

HIRA_2 = parse("""
あさ|朝|morning
あし|足|foot
あめ|雨|rain
いえ|家|house
いぬ|犬|dog
うえ|上|above
うみ|海|sea
うま|馬|horse
えき|駅|station
おか|丘|hill
おと|音|sound
かお|顔|face
かぎ|鍵|key
かさ|傘|umbrella
かぜ|風|wind
かに|蟹|crab
かみ|紙|paper
かわ|川|river
きく|菊|chrysanthemum
きた|北|north
くち|口|mouth
くに|国|country
くも|雲|cloud
くり|栗|chestnut
こえ|声|voice
ここ|此処|here
こめ|米|rice
さかな|魚|fish
さる|猿|monkey
しお|塩|salt
した|下|below
しま|島|island
そと|外|outside
そら|空|sky
たこ|蛸|octopus
たに|谷|valley
たまご|卵|egg
つき|月|moon
つの|角|horn
てら|寺|temple
とり|鳥|bird
なか|中|inside
なし|梨|pear
なつ|夏|summer
なべ|鍋|pot
にく|肉|meat
にし|西|west
ねこ|猫|cat
はこ|箱|box
はし|橋|bridge
はな|花|flower
はね|羽|feather
はる|春|spring
ひがし|東|east
ひと|人|person
ふね|船|boat
ふゆ|冬|winter
へや|部屋|room
ほし|星|star
まち|町|town
まど|窓|window
みず|水|water
みせ|店|shop
みち|道|road
みみ|耳|ear
むし|虫|insect
むら|村|village
もり|森|forest
やま|山|mountain
ゆき|雪|snow
ゆめ|夢|dream
よる|夜|night
りす|栗鼠|squirrel
わに|鰐|crocodile
あお|青|blue
あか|赤|red
しろ|白|white
くろ|黒|black
すし|寿司|sushi
そば|蕎麦|soba noodles
うどん|饂飩|udon noodles
まめ|豆|bean
もも|桃|peach
くさ|草|grass
えだ|枝|branch
いす|椅子|chair
つくえ|机|desk
さら|皿|plate
かべ|壁|wall
にわ|庭|garden
あね|姉|older sister
あに|兄|older brother
おとうと|弟|younger brother
いもうと|妹|younger sister
ちち|父|father
はは|母|mother
こども|子供|child
からだ|体|body
こころ|心|heart
ことば|言葉|word
""")

KATA_2 = parse("""
アイス||ice cream
アジア||Asia
アニメ||anime
アロエ||aloe
イタリア||Italy
インク||ink
ウイルス||virus
エアコン||air conditioner
エコ||eco-friendly
エプロン||apron
オイル||oil
オペラ||opera
カカオ||cacao
カメラ||camera
アクセル||accelerator
アプリ||app
アルミ||aluminum
ガイド||guide
ガラス||glass
キウイ||kiwi fruit
キロ||kilogram
クイズ||quiz
クラブ||club
グラス||drinking glass
イベント||event
エリア||area
コアラ||koala
コイン||coin
ココア||cocoa
オアシス||oasis
ゴム||rubber
サイン||sign
サラダ||salad
オクラ||okra
ジャム||jam
オルガン||organ
カナダ||Canada
カルテ||medical chart
ガム||chewing gum
キムチ||kimchi
クラゲ||jellyfish
ソファ||sofa
タイプ||type
タオル||towel
ケバブ||kebab
ゴリラ||gorilla
テスト||test
テレビ||television
テント||tent
ドア||door
トマト||tomato
ドレス||dress
ナイフ||knife
サウナ||sauna
サドル||saddle
バイク||motorcycle
バス||bus
パスタ||pasta
パン||bread
パンダ||panda
ジム||gym
ピアノ||piano
ビデオ||video
ビル||building
セダン||sedan
ベルト||belt
ペン||pen
ホテル||hotel
ボタン||button
ポスト||mailbox
マスク||mask
ミルク||milk
メモ||memo
メロン||melon
ラジオ||radio
リボン||ribbon
レモン||lemon
ワイン||wine
タイヤ||tire
キャベツ||cabbage
キャンプ||camping
ダンス||dance
クラス||class
チリ||Chile
デニム||denim
ドラマ||television drama
ナイロン||nylon
ハム||ham
バナナ||banana
パイ||pie
パネル||panel
ビキニ||bikini
ビザ||visa
ピザ||pizza
フィルム||film
プラン||plan
ベンチ||bench
ミシン||sewing machine
メディア||media
リスク||risk
""")

HIRA_ADJ = parse("""
あかい|赤い|red
あおい|青い|blue
しろい|白い|white
くろい|黒い|black
おおきい|大きい|big
ちいさい|小さい|small
あたらしい|新しい|new
ふるい|古い|old
あかるい|明るい|bright
くらい|暗い|dark
あつい|熱い|hot
つめたい|冷たい|cold
たかい|高い|tall
ひくい|低い|low
ながい|長い|long
みじかい|短い|short
おもい|重い|heavy
かるい|軽い|light
きれいな|綺麗な|beautiful
しずかな|静かな|quiet
""")
HIRA_NOUNS = parse("""
はな|花|flower
そら|空|sky
いえ|家|house
みち|道|road
やま|山|mountain
""")

KATA_3 = parse("""
アイスクリーム||ice cream
アナウンサー||announcer
アパート||apartment
アメリカ||the United States
アルバイト||part-time job
アルバム||album
エスカレーター||escalator
エレベーター||elevator
オートバイ||motorcycle
オレンジ||orange
カレンダー||calendar
カーテン||curtain
カラオケ||karaoke
カリフォルニア||California
ガソリン||gasoline
キーボード||keyboard
キロメートル||kilometer
クリスマス||Christmas
コンピューター||computer
コンビニ||convenience store
サンドイッチ||sandwich
サングラス||sunglasses
シャワー||shower
シャンプー||shampoo
スーパー||supermarket
スケジュール||schedule
スプーン||spoon
スマートフォン||smartphone
セーター||sweater
センチメートル||centimeter
ターミナル||terminal
ダイニング||dining room
チョコレート||chocolate
デパート||department store
テーブル||table
テニスコート||tennis court
トイレットペーパー||toilet paper
トースター||toaster
ドライバー||driver
ドラマ||television drama
ニュースサイト||news website
ネクタイ||necktie
ノートパソコン||laptop computer
バスケットボール||basketball
バスルーム||bathroom
パスポート||passport
パソコン||personal computer
ハンバーガー||hamburger
ピクニック||picnic
ビジネス||business
フィルム||film
フォーク||fork
プラットホーム||platform
プレゼント||present
プロジェクト||project
ベランダ||balcony
ボールペン||ballpoint pen
ポケット||pocket
マフラー||scarf
マンション||apartment building
ミュージアム||museum
ミルクティー||milk tea
メニュー||menu
モノレール||monorail
ヨーグルト||yogurt
レストラン||restaurant
レポート||report
ワイシャツ||dress shirt
ワイヤレス||wireless
インターネット||internet
イヤホン||earphones
ウェブサイト||website
エンジニア||engineer
オーストラリア||Australia
オムライス||omelet rice
カプチーノ||cappuccino
キャラクター||character
キャンセル||cancellation
コミュニケーション||communication
コンサート||concert
サービス||service
ジャケット||jacket
スニーカー||sneakers
スーツケース||suitcase
スタジアム||stadium
ストロベリー||strawberry
セキュリティ||security
ソフトウェア||software
タイトル||title
ダウンロード||download
デザート||dessert
トレーニング||training
ドキュメント||document
ハイキング||hiking
バレーボール||volleyball
プログラム||program
ヘッドホン||headphones
ホワイトボード||whiteboard
マヨネーズ||mayonnaise
ミーティング||meeting
""")

def hira_level3():
    rows = []
    for adj, adj_k, adj_en, _ in HIRA_ADJ:
        for noun, noun_k, noun_en, _ in HIRA_NOUNS:
            rows.append((f"{adj} {noun}", f"{adj_k}{noun_k}", f"{adj_en} {noun_en}", None))
    return rows

HIRA_SUBJECTS = parse("""
わたし|私|I
ちち|父|my father
はは|母|my mother
あに|兄|my older brother
あね|姉|my older sister
おとうと|弟|my younger brother
いもうと|妹|my younger sister
ともだち|友達|my friend
せんせい|先生|the teacher
こども|子供|the child
いぬ|犬|the dog
ねこ|猫|the cat
とり|鳥|the bird
がくせい|学生|the student
みんな|皆|everyone
""")
HIRA_PREDICATES = parse("""
みず を のみます。|水を飲みます。|drinks water
ほん を よみます。|本を読みます。|reads a book
え を かきます。|絵を描きます。|draws a picture
うち へ かえります。|家へ帰ります。|goes home
こうえん で あそびます。|公園で遊びます。|plays in the park
はやく おきます。|早く起きます。|gets up early
ゆっくり あるきます。|ゆっくり歩きます。|walks slowly
まいにち べんきょうします。|毎日勉強します。|studies every day
""")

KATA_SUBJECTS = parse("""
アンナ||Anna
マリア||Maria
ケン||Ken
ジョン||John
エミ||Emi
トム||Tom
スタッフ||the staff member
シェフ||the chef
ガイド||the guide
ドライバー||the driver
チーム||the team
バンド||the band
ロボット||the robot
パンダ||the panda
コアラ||the koala
""")
KATA_PREDICATES = parse("""
コーヒー を のみます。|コーヒーを飲みます。|drinks coffee
テレビ を みます。|テレビを見ます。|watches television
メール を かきます。|メールを書きます。|writes an email
ホテル へ いきます。|ホテルへ行きます。|goes to the hotel
バス で かえります。|バスで帰ります。|returns by bus
テニス を します。|テニスをします。|plays tennis
ピアノ を ひきます。|ピアノを弾きます。|plays the piano
レストラン で たべます。|レストランで食べます。|eats at a restaurant
""")

def sentences(subjects, predicates, prefix_kanji=True):
    rows = []
    for sub, sub_k, sub_en, _ in subjects:
        for pred, pred_k, pred_en, _ in predicates:
            if len(rows) == 100: return rows
            kana = f"{sub} は {pred}"
            kanji = f"{sub_k or sub}は{pred_k or pred.replace(' ', '')}"
            if sub_en == "I":
                pred_en = {"drinks":"drink", "reads":"read", "draws":"draw", "goes":"go", "plays":"play", "gets":"get", "walks":"walk", "studies":"study"}.get(pred_en.split()[0], pred_en.split()[0]) + (" " + " ".join(pred_en.split()[1:]) if len(pred_en.split()) > 1 else "")
            english = f"{sub_en} {pred_en}."
            rows.append((kana, kanji, english[0].upper() + english[1:], None))
    return rows

def validate(name, rows):
    ids = set()
    for i, row in enumerate(rows, 1):
        kana = row[0]
        ident = f"{name}-{i}"
        assert ident not in ids; ids.add(ident)
        assert romaji(kana), f"missing romaji: {kana}"
        level = int(name[-2:])
        compact = kana.replace(" ", "")
        if level == 2:
            assert 2 <= len(compact) <= 4, (name, kana, len(compact))
            assert "っ" not in hira(kana) and "ー" not in kana, (name, kana)
            assert row[2], (name, kana, "translation required")
        if level == 4: assert len(kana) <= 30, (name, kana, len(kana))

def main():
    DATA.mkdir(exist_ok=True)
    datasets = {
        "hiragana-01": level_one("hiragana"), "katakana-01": level_one("katakana"),
        "hiragana-02": HIRA_2, "katakana-02": KATA_2,
        "hiragana-03": hira_level3(), "katakana-03": KATA_3,
        "hiragana-04": sentences(HIRA_SUBJECTS, HIRA_PREDICATES),
        "katakana-04": sentences(KATA_SUBJECTS, KATA_PREDICATES),
    }
    for name, rows in datasets.items():
        if name.endswith(("02", "03", "04")): assert len(rows) == 100, (name, len(rows))
        validate(name, rows); write(name, rows)
        print(f"{name}: {len(rows)} entries")

if __name__ == "__main__": main()
