# Yomu — Kana Reading

A static Japanese reading trainer inspired by a first reading book. Read a hiragana or katakana prompt, type its romaji, then reveal the natural Japanese spelling and English meaning.

Yomu includes four levels, separate hiragana and katakana courses, optional spaces between words, Learn and Exam modes, response timing, local statistics and non-repeating random question selection.

## Run locally

```bash
python3 server.py
```

Open <http://localhost:8000>. To use another port: `python3 server.py 8080`.

The app has no build step and can be deployed directly to GitHub Pages.

## Database

The eight JSON datasets live in `data/`. To rebuild and validate them:

```bash
python3 tools/generate_data.py
python3 tools/build_large_corpus.py
python3 tools/validate_data.py
```

Read [DATABASE_GUIDE.md](DATABASE_GUIDE.md) before changing or extending the learning material.
