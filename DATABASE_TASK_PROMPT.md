# Quick prompt for Yomu database work

Use this file to start a fresh chat with Codex or another coding model without pasting the project history.

## General prompt

```text
We are working on Yomu — a Japanese kana-reading trainer.

Before changing anything, read these files completely:
- DATABASE_GUIDE.md
- tools/validate_data.py
- tools/build_large_corpus.py

The learning data is in data/*.json. Preserve the existing application behavior and JSON schema. Japanese naturalness and beginner usefulness matter more than reaching a round record count.

For every changed card, verify:
- kana, kanji, romaji and English translation describe exactly the same reading and meaning;
- the Japanese is natural and contemporary;
- word spaces are pedagogically useful;
- the card belongs to the selected course and level;
- it is not obscure, archaic, vulgar, offensive, overly technical or dependent on missing context;
- IDs remain stable and unique.

Do not edit generated JSON alone when its source is in tools/build_large_corpus.py. Update the source list or generation rule, rebuild the affected dataset, and run:

python3 tools/validate_data.py

Do not regenerate or rewrite unrelated levels. Summarize changed counts and any judgment calls at the end.
```

## Add or replace vocabulary

Append this to the general prompt:

```text
Improve level 2 for [hiragana/katakana]. Add or replace approximately [NUMBER] cards in these themes: [THEMES]. Prefer animals, nature, food, home, school, clothes, toys, family, body, transport, basic actions and basic qualities. Review the complete resulting level-2 list for accidental specialist or adult-oriented vocabulary before finishing.
```

## Make phrases or sentences more lively

Append this to the general prompt:

```text
Review level [3/4] for [hiragana/katakana] and replace dry, repetitive, formal or context-dependent material with approximately [NUMBER] independent, lively everyday examples.

Prefer situations involving home, friends, animals, food, weather, school, hobbies, travel and ordinary conversation. Avoid Cartesian template combinations. Limit repeated content words and sentence structures. Keep all original level-length rules. Preserve source attribution for retained Tatoeba material and manually verify every replacement.
```

## Language review only

Append this to the general prompt:

```text
Review [FILE OR LEVEL] without editing it first. Report only problematic cards as:

ID | severity | field | problem | suggested fix | confidence

Prioritize incorrect readings, particle pronunciation, romaji, mismatched translations, unnatural Japanese, broken word boundaries and unsuitable beginner material. Separate systematic generator bugs from isolated bad cards. After the report, wait for approval before applying fixes.
```

## Apply an existing review

Append this to the general prompt:

```text
Read [REVIEW FILE]. Verify its claims against the current JSON and source generator. Fix systematic causes in the generator instead of patching hundreds of generated records. Blocklist or replace confirmed isolated bad cards. Do not blindly apply low-confidence suggestions. Rebuild only affected datasets, validate everything, and write a short resolution report while preserving the original review as an audit record.
```

