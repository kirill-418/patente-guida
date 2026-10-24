# AGENTS.md — Patente B study kit

Study material for the Italian driving **theory exam, category B** (patente B): the official quiz questions with answers, a dictionary of rare Italian words found in them (Italian → English / Russian), and a flip-card web app for learning that dictionary.

**Focus:** category B only. The AM, Superiori and Revisione quiz files exist in `quiz/` for completeness, but the vocabulary and the app use only the B list (`quiz/quiz-patente-AB.md`). Do not widen scope unless asked.

## Repository layout

| Path | What it is |
|---|---|
| `quiz/quiz-patente-AB.md` | All 7,020 official category A/B questions, grouped in 25 chapters, answer ✅ VERO / ❌ FALSO, with figures. **Source of truth for the vocabulary.** |
| `quiz/quiz-patente-{AM,Superiori,Revisione-AB,Revisione-AM,Revisione-Superiori}.md` | Other official lists (not used downstream). |
| `quiz/images/` | 962 figures extracted from the PDFs (`ab_*`, `am_*`, `sup_*`, `revab_*`, `revam_*`, `revsup_*`). |
| `vocab/vocabolario-rare-patente-B.md` | The dictionary: 1,637 entries in four tiers, with EN + RU translations and a quiz example each. |
| `app/index.html` | The flip-card app as a **standalone page** (full HTML document, data embedded, no build step at runtime). This is what servers and Docker serve. |
| `app/artifact.html` | The same page as a fragment (no `<!doctype>`/`<head>`), for publishing as a Claude Artifact, whose host adds the skeleton itself. |
| `app/template.html`, `app/data.json` | App source with a `/*DATA*/` placeholder, and a readable copy of the word payload (one word per line). |
| `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `docker/nginx.conf` | Run the app in nginx. See "Running with Docker". |
| `data/ab-questions.json` | Structured B questions: `id, text, answer, chapter, group, image, page`. |
| `data/vocab-final.json` | Final dictionary entries (input of the app build). |
| `data/lemma-stats-ab.json` | Per-lemma stats for the B list: questions using it, general-Italian frequency rank, forms seen. |
| `VERSION` | Current application version (`1.3.0`). |
| `tools/` | The pipeline scripts (see below). |

## Source data

- Official lists from the Ministero delle Infrastrutture e dei Trasporti, published on *Il Portale dell'Automobilista*: https://www.ilportaledellautomobilista.it/web/portale-automobilista/-/quiz-per-le-patenti-am-b-superiori-e-cqc
- The A/B file is `210926_Conseguimento A-B italiano.pdf` (586 pages). The `210926` in the name is historical; this is the list currently in force (in use since Dec 2021, no replacement announced as of 2026-10-17). The portal regenerated the PDF on 2026-09-17.
- The exam: 30 true/false statements, 20 minutes, at most 3 errors.
- PDFs are not committed (25 MB, re-downloadable). Question numbers (`id`) are the official ones and are stable references.
- Parsing note: the PDF text stream is **not** in reading order. `tools/parse.py` reconstructs rows from line positions (id column x<60, text x<330, answer x≥330) and assigns figures by vertical position. Validated: 7,020 unique ids, every row has text, answer and chapter. Two chapter titles are cut off in some places in the PDF and are re-joined by prefix in `tools/gen.py`.

## How words are selected — the dictionary (read this first)

A word enters the dictionary if **both** hold:

1. **Rare in general Italian.** Its lemma is **not in the top 5,000** lemmas of a general Italian frequency list, or is absent from it. List: OpenSubtitles 2018, `hermitdave/FrequencyWords` (`it_50k.txt`). Lemmas come from `simplemma` (Italian); the rank of a lemma is the rank of its best-ranked surface form.
2. **Present in the quiz.** It appears in **at least 1** question of the B list (counted once per question, over all its forms).

Then, in `tools/gen_vocab.py`:

- Models (see "Translation") fix the headword where the lemmatizer was wrong (`carreggiare` → `carreggiata`), and entries that end up with the same headword are **merged**; the question count is recomputed over the union of forms.
- **Excluded:** proper nouns (cities, regions, countries — e.g. Napoli, Stelvio, Alpi) and non-words/fragments (`sull`, `dall`, `zag`, typos). Words with **no driving meaning are kept** (the user may not know them either).
- **Manual additions:** `ASL`, `LSD`, `bull bar` (skipped by the translators, but they occur in questions).
- **Tiers** (by number of questions using the word): A ≥ 50 (63 words), B 10–49 (239), C 3–9 (432), D 1–2 (903). Entries are sorted by that count, descending, inside each tier. The app's level chips A–D use the same thresholds.
- Result: 3,149 distinct lemmas in the B list → 1,727 candidates → **1,637 entries**.

### Why these thresholds (history, so nobody re-litigates them)

The first draft was "outside the top 10,000 and ≥ 2 questions" (~700 words). The user checked it against words they remembered from real tests: `sovraccarico` (rank 9,757), `risarcimento` (6,396) and `sovrannumero` (1 question) were all missed. The rule was loosened to top 5,000 / ≥ 1 question, after which all seven test words (`allorché, restringimento, omologare, sovraccarico, sovrannumero, risarcimento, smaltimento`) were included.

### Known limitation (open)

Frequency measures how common a word is in conversation, **not whether its exam meaning is the everyday one**. Common words with a narrower exam meaning are missing, e.g. `scarico` (rank 4,159; exam: *exhaust*) and `impianto` (rank 3,243; exam: *system*, as in *impianto di scarico*). `manomissione` (rank 23,721) is in.

**Planned fix (not implemented, awaiting go-ahead):** a second inclusion criterion — screen every lemma in the top 5,000 that appears in ≥ 2 questions (~1,400 words) with a model that judges whether the exam sense differs from the everyday sense; add those (expected 150–300), each marked "everyday word, special meaning in the quiz". Existing words must not change; progress in the app is keyed by headword, so it survives an append.

## Translation

Translations were written by LLM subagents, one chunk of ~190 words each (`vocab/in/chunkN.json` → `vocab/out/chunkN.json`), with this contract per word: `lemma` (unchanged input), `head` (corrected dictionary headword), `pos`, `en`, `ru` (1–3 short options, **driving/exam sense first**, standard road-traffic terminology, e.g. carriageway / проезжая часть), `ex` (index of the best example), optional `note` (≤ 12 words), `skip`. Spot-checked by reading ~60 doubtful entries against their quiz sentences; **not reviewed by a native speaker** — treat as good, not guaranteed. The intermediate chunk files are not committed; `data/vocab-final.json` is the merged result.

## How the flip-card app picks a card

State: `known` (set of headwords), `learning` (set of headwords marked "New"), `levels` (subset of A–D, default all, never empty).

- **Deck** = every word whose level is selected **and** that is not in `known`. So the deck contains both never-seen words and words marked New.
- **Draw** = words not shown yet have priority. If there are any unseen words in the selected levels, the draw is uniform random over those unseen words only. Once every word in the selected levels has been shown at least once (all remaining cards are marked New), draws pick from the learning cards. If the candidate pool has more than one word, the card just shown is excluded from the next draw (no immediate repeat).
- **Know** (green): add to `known`, remove from `learning` → never drawn again (until Reset or Undo).
- **New** (red): add to `learning`, remove from `known` → stays in the deck and can come back at any later draw, including the very next one if the deck is small.
- **Undo** restores the previous status of the last ≤ 100 actions and shows that card again. Undo history is in memory only.
- Changing levels re-draws only if the current card falls outside the new selection. Deck empty → "Deck finished" screen.
- Counters shown (known / marked new / not seen yet / left) are computed **over the selected levels only**.
- Keys: Space/Enter flips, ← = New, → = Know.
- The card front shows the headword, an official quiz figure where needed, and the quiz question example for context. The card back shows translations (EN, RU), notes, and the official quiz answer (✅ VERO / ❌ FALSO) where the question was previously.
- The card back is filled in ~260 ms after the flip-back so the next answer never flashes during the animation.

## Persistence and sync

- Progress document, one per viewer: `{ known: [headword…], learning: [headword…], levels: ["A",…], updated: <ms epoch>, by: <session id> }`. Keys are headword strings.
- **Always** mirrored to `localStorage` under `parole-patente-b-v1`, and shown from there instantly on load.
- **On Claude Artifacts** (how it was first deployed) the `db` and `user` capabilities add cross-device sync at `data/users/<uid>/vocab`. Writes are debounced 500 ms, one at a time, retried after 8 s on failure. Conflict rule: **the document with the newer `updated` wins** (on load, and for live updates from another device; echoes of own writes are ignored via `by`). The first load uses `get()` (definitive) before subscribing, so an empty cache can never overwrite server data.
- There is **no review history/log** — only the current state. (An optional per-click review log was proposed; not approved/implemented.)

## Running with Docker

```sh
docker compose up -d --build     # then open http://localhost:8080
PORT=3000 docker compose up -d --build   # another port
docker compose down
```

The image is based on `python:3.12-alpine` running `docker/server.py`. It serves the flip-card app `app/index.html` with gzip, security headers (CSP, nosniff, no-referrer), and provides `/api/progress` with persistent storage on disk (mounted at `/data`, mapped to `./storage` on the host in `docker-compose.yml`). On container startup, progress is restored from `/data/progress.json`. Healthcheck queries `/health`.

## Deploying to a normal server

The app can be run via Docker or as a static file:

- **With Docker / `docker/server.py`:** Progress persists to disk (`/data/progress.json`) and synchronizes automatically between devices (phone and desktop) via `/api/progress`.
- **Pure static hosting:** Without the server API or Claude Artifacts, the code gracefully falls back to `localStorage` ("Saved in this browser only").
- **On Claude Artifacts:** Progress syncs via `window.claude` DB (`data/users/<uid>/vocab`).
- The only external request is Google Fonts (Barlow, Barlow Condensed) with system-font fallbacks.
- Use HTTPS in production. Do not add analytics that would record which words a user marks.

## Rebuilding things

Python 3 with `pymupdf` and `simplemma`; Node with `jsdom@24` for the test. The scripts in `tools/` were run from a scratch directory `work/` placed **inside the repo root** (they use relative paths like `../quiz/...`), in this order:

1. Download the PDFs into `work/dl/…` (URLs on the portal page above).
2. `python3 ../tools/parse.py dl/ab/ab.pdf out/img_ab ab_ out/ab.json` → structured questions + figures (repeat per list with prefixes `am_`, `sup_`, `revab_`, `revam_`, `revsup_`).
3. `python3 ../tools/gen.py` → `quiz/*.md` and `quiz/images/`.
4. `python3 ../tools/vocab.py` → `out/vocab.json` (lemma stats; needs `dl/freq/it_50k.txt` from https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/it/it_50k.txt).
5. `python3 ../tools/prep.py` → candidate words with examples, split in `vocab/in/chunk1..9.json`.
6. Translate chunks (LLM step, see above) into `vocab/out/chunk1..9.json`.
7. `python3 ../tools/gen_vocab.py` → `vocab/vocabolario-rare-patente-B.md`, `vocab/final.json` (copy it to `data/vocab-final.json`).
8. From the **repo root**: `python3 tools/build_app.py` → `app/data.json`, `app/index.html` (standalone), `app/artifact.html` (Claude Artifact fragment).
9. `NODE_PATH=<dir with jsdom> node tools/test_app.js` → behavioural test of `app/artifact.html` in jsdom with a fake db (known words never reappear, New words do, levels, undo, sync, reload, deck-finished).

Caveat: the scripts were written in a scratch session and their absolute paths were rewritten to the relative layout above afterwards; `build_app.py` and `test_app.js` were re-run after the move, the earlier pipeline steps were **not** re-run end-to-end from this layout. Check paths if one fails.

## Conventions

- Don't commit the source PDFs, virtualenvs, or any user progress data. The repo is public; it holds only official public quiz content and derived study material.
- When the user reports a word missing from the dictionary, check its lemma, general rank and quiz count in `data/lemma-stats-ab.json` first; it usually explains the miss (see the known limitation).
- Keep UI copy in English, dictionary notes short, and never present AI translations as verified.
