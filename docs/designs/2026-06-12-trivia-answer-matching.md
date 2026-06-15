# Trivia Answer Matching Overhaul + Learned Gray-Zone Classifier

**Date:** 2026-06-12
**Status:** Approved for implementation (phases 1–3). Phase 2 (data enrichment) shelved by owner decision.

## Problem

`TriviaModule.is_correct_answer` grades free-text guesses against per-question answer lists
(93,277 questions across 22 category files in `Saves/trivia/`). Both error directions occur
and both matter to the owner:

- **False negatives:** correct answers rejected — typos, diacritics ("Pokémon"), number-form
  variants ("World War II" vs "World War 2" vs "WWII"), US/UK spellings, plurals, partial
  forms. Worst case: questions whose only stored answer is a long free-form sentence
  (e.g. `"outstanding heroism at guadalcanal during world war ii"`) that no realistic guess matches.
- **False positives:** fuzzy matcher (difflib, tiered 0.90/0.85/0.82) credits close-but-wrong
  guesses, especially short answers and lucky substrings.

## Constraints

- **Runtime is a low-resource Ubuntu server.** No heavyweight runtime deps: no
  scikit-learn/numpy/scipy imports in the bot process, no embedding models, no GPU.
  RapidFuzz (small compiled wheel) is acceptable. Dev machine is Windows.
- **No network calls during gameplay.** Grading must resolve locally in milliseconds —
  every message in an active trivia channel is checked.
- Question bank is imported but owner-modifiable (relevant to shelved phase 2).
- No existing test infrastructure in the repo.

## Considered approaches (and why rejected)

| Approach | Verdict | Why |
|---|---|---|
| Local embeddings (MiniLM/fastText similarity) | **Rejected** | Related-but-wrong answers ("Venus"/"Mars") embed as near-identical — directly worsens false positives. No open-source trivia bot uses this. |
| Runtime LLM grading (Haiku per-guess) | **Rejected** | ~600–950ms per check; Tier-1 rate limits (50 RPM) collapse under a channel spamming guesses. Cost fine (~$0.0001/check), operations not. |
| Offline LLM answer enrichment of the 93k bank | **Shelved (phase 2)** | The only fix for long free-form single answers and knowledge variants ("Teddy" → "Theodore Roosevelt"). Plan: resumable chunked job (~200 questions/chunk, ~470 chunks) driven by Claude Code on the owner's Max subscription — progress ledger, validation rules (alternate must share a content word with original; must not be longer), writes into the existing JSON files. Zero marginal cost. Revisit after phases 1–3 land. |
| Train a knowledge-bearing custom model | **Rejected** | Needs tens of thousands of labeled pairs; inherits embedding failure modes. |
| **Deterministic matcher overhaul + learned gray-zone classifier** | **Chosen** | Attacks both error directions; runtime cost ~zero; classifier is pure-Python inference from exported coefficients. |

## Chosen design

### Phase 1 — Matcher overhaul (deterministic, local)

New shared module **`TriviaMatching.py`** (repo root, beside the other modules) owning
normalization, feature extraction, and the verdict. `TriviaModule` imports it; so do the
offline trainer and review tooling. **One implementation — train/serve skew is the classic
silent killer of small-model setups.**

**Normalization pipeline** (applied to guesses and stored answers, in order):
1. Unicode NFKD fold + strip combining marks (stdlib `unicodedata`).
2. Lowercase; strip punctuation (as today).
3. Number canonicalization: number-words → digits via a small hand dict ("zero"–"twenty",
   tens, "hundred"/"thousand" — no `word2number` dep unless the golden set proves it needed);
   Roman numerals → digits only for standalone tokens that are valid numerals and not common
   English words ("i", "mix", "did" stay words; "ii", "vii", "xiv" convert).
4. US/UK spelling unification via a small mapping table (vendored dict, no dep).
5. Guarded plural fold: strip trailing "s"/"es" only when guess-word and answer-word differ by
   exactly that suffix. Never blind stemming.
6. Stop-word strip (as today).

**Matching passes** (RapidFuzz replaces difflib; `rapidfuzz` added to `requirements.txt`):
1. Exact: single-word answers → whole-word token match; multi-word → phrase substring (as today).
2. Order-independent token-set match (as today: 2–5 words, all ≥4 chars).
3. Scored pass over sliding windows: character ratio + `token_sort_ratio` + Jaro-Winkler.
   Tiered thresholds retained as the initial decision rule; short-answer tier tightened
   (research consensus: 0.85 too permissive, ~0.90 for short answers).
4. Numeric answers: exact-after-canonicalization only (as today, now catching "seven"/"VII").

**Gray-zone logger:** when the best score lands in the ambiguous band (initially
[0.70, 0.95]), append to `Saves/trivia_graylog.jsonl`: timestamp, guild id, question, answer
list, guess, feature vector, verdict given, matcher version. Append-only, no PII beyond what
trivia already stores. This is the future training corpus and costs only disk.

**Golden test set:** `trivia_training/golden.jsonl` — (guess, answer_list, expected_verdict)
cases, seeded ~200–300 from real bank questions covering every rule above plus known traps
("cat"/"bat", "16"/"6", Venus/Mars-style). A plain `python -m trivia_training.run_golden`
script reports accuracy; every threshold change is measured against it, not vibes.

### Phase 1.5 — `.trivia_review` labeling command

- `bot_admin` auth, listed under **Testing** in `COMMAND_MODULES` (house convention).
  Prefix + slash + help entry in `botMain.py`; implementation in `TriviaModule` (or
  `BotAdminModule` if cleaner at implementation time).
- Replays unlabeled gray-log entries one at a time as an embed (question, stored answers,
  the guess, what the bot decided) with ✅ correct / ❌ incorrect / ⏭ skip buttons.
  Writes labels to `Saves/trivia_labels.jsonl`.
- Bias guard: the queue serves a random mix of accepted-gray and rejected-gray samples,
  not just disputes — labeling only complaints trains a permissive model.

### Phase 3 — Classifier (after ~500+ labels accumulate)

- **Features** (computed by `TriviaMatching.extract_features`, the same function that logged
  them): char ratio, token_sort_ratio, token_set_ratio, Jaro-Winkler, length difference,
  word-count delta, per-word coverage, numeric-mismatch flag, answer length tier.
- **Training:** scikit-learn logistic regression (L2), run on the dev machine.
  `trivia_training/train.py` reads labels, trains, evaluates against the golden set
  (before/after report), exports `{weights, bias, feature_names, matcher_version}` to
  `Saves/trivia_model.json`. sklearn is a dev-only dep (`trivia_training/requirements.txt`),
  **never** in the bot's `requirements.txt`.
- **Inference:** ~15 lines of pure Python in `TriviaMatching` — dot product + sigmoid.
  Microseconds per guess. The model replaces only the gray-band decision; exact and token-set
  passes stay deterministic. If `trivia_model.json` is absent or its `feature_names` /
  `matcher_version` don't match the running code, fall back to hand thresholds — the bot
  never *requires* a model.
- **Operating point:** decision cutoff stored in the model JSON (default 0.5), adjustable
  without retraining to trade precision vs recall.
- **Cadence:** retrain only when meaningfully more labels exist; no drift pressure
  (trivia language is static). Expected: a few rounds early, then rare.

### Expected effectiveness (honest bounds)

- Phase 1 fixes whole classes of false negatives at zero false-positive cost (every
  normalization rule is an exact equivalence) and tightens short-answer false positives.
- The classifier polishes only the gray band — realistic target is cutting gray-zone
  mistakes by a third to half once ~1–2k labels exist. It adds **no knowledge**;
  "Holland"→"Netherlands" remains phase 2's job.

## Open questions

- Exact gray-band bounds and per-tier thresholds — to be tuned against the golden set
  during implementation, not guessed in this doc.
- Whether `.trivia_review` should also be invokable in DMs (it touches no per-guild state;
  `bot_admin` + global log suggests DM-friendly is fine — implementer's call per the
  permission-gating rules in CLAUDE.md).
- Gray-log rotation/size cap (JSONL grows unbounded; a simple size check or manual pruning
  is probably enough at this scale).
- Phase 2 enrichment: untouched until owner re-opens it.

## Task breakdown

1. `TriviaMatching.py`: normalization pipeline + ported 3-pass matcher on RapidFuzz +
   `extract_features` + hand-threshold verdict. `TriviaModule` switches to it. Add
   `rapidfuzz` to requirements.
2. `trivia_training/golden.jsonl` seed set + `run_golden.py` harness; tune initial thresholds
   against it.
3. Gray-zone logger wired into the verdict path.
4. `.trivia_review` command (prefix + slash + Testing help entry) writing
   `Saves/trivia_labels.jsonl`.
5. `trivia_training/train.py` (sklearn, dev-only) exporting `Saves/trivia_model.json`;
   pure-Python inference + fallback wired into `TriviaMatching`.
6. (Shelved) Phase 2 enrichment job design lives in this doc; no tasks until re-opened.
