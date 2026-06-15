"""
TriviaMatching — shared answer-grading module.

Used by TriviaModule (bot), the golden harness and offline trainer
(trivia_training/), and the gray-zone logger. All matching and feature
logic lives here so there is no train/serve skew.

No heavy ML-library imports — runs on the low-resource bot host with stdlib +
rapidfuzz only.
"""

import re
import os
import json
import unicodedata
import functools
import math
from datetime import datetime, timezone

from rapidfuzz import fuzz as _fuzz
from rapidfuzz.distance import JaroWinkler as _JW


# ---------------------------------------------------------------------------
# Version — bump when normalization / feature-extraction semantics change.
# Graylog, labels, and model JSON all carry this value for skew detection.
# ---------------------------------------------------------------------------
MATCHER_VERSION = "1"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Stop words stripped after other normalization (copied from TriviaModule.py).
_STRIP_WORDS = {"the", "a", "an", "of", "and", "in", "on", "at", "to", "for"}

# Single-token number-word → digit string.
# Compositional parsing ("twenty one" → 21) is intentionally not attempted;
# real cases can be added here if the golden set demands it (see plan risk note).
_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20",
    "thirty": "30", "forty": "40", "fifty": "50",
    "sixty": "60", "seventy": "70", "eighty": "80", "ninety": "90",
    "hundred": "100", "thousand": "1000",
}

# English words that happen to be valid Roman-numeral strings — leave them alone.
# Only standalone tokens that are valid numerals AND not here AND length ≥ 2 get
# converted (so bare single-letter i/v/x/l/c/d/m all stay as words).
_ROMAN_COMMON_WORDS = {
    "i", "mix", "did", "mid", "civic", "dim", "ill", "mild", "will",
    "mill", "fill", "film", "lid", "slim", "vim", "vim", "civil",
    "livid", "mimic", "mix", "dill", "mill",
}

# Valid Roman numeral pattern (only uppercase after normalization we work lowercase;
# the token will already be lowercase here, so we define the set for lowercase).
_ROMAN_RE = re.compile(r"^m{0,4}(cm|cd|d?c{0,3})(xc|xl|l?x{0,3})(ix|iv|v?i{0,3})$")

def _roman_to_int(s: str) -> int:
    """Convert a lowercase Roman numeral string to int. Returns 0 for empty."""
    val = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
    result, prev = 0, 0
    for ch in reversed(s):
        v = val.get(ch, 0)
        if v < prev:
            result -= v
        else:
            result += v
        prev = v
    return result

def _is_roman(token: str) -> bool:
    """True if token is a non-empty valid Roman numeral string (lowercase)."""
    if not token or token in _ROMAN_COMMON_WORDS:
        return False
    if len(token) < 2:
        # Single letters are too ambiguous (i, v, x, etc.) — leave as-is.
        return False
    return bool(_ROMAN_RE.match(token))

# UK→US spelling map (~20 common entries; apply per-word at normalize time).
_UK_US_MAP = {
    "colour": "color", "colours": "colors",
    "theatre": "theater", "theatres": "theaters",
    "organise": "organize", "organised": "organized", "organises": "organizes",
    "defence": "defense", "defences": "defenses",
    "offence": "offense", "offences": "offenses",
    "centre": "center", "centres": "centers",
    "grey": "gray",
    "aeroplane": "airplane", "aeroplanes": "airplanes",
    "honour": "honor", "honours": "honors",
    "behaviour": "behavior",
    "flavour": "flavor",
    "neighbour": "neighbor",
    "realise": "realize", "recognised": "recognized",
    "licence": "license",
    "maths": "math",
}

# Tier thresholds for the fuzzy pass.
# Finalized in Task 2 against golden.jsonl (255 curated cases):
#   SHORT=0.90 (unchanged) — short answers need high confidence to avoid
#               accepting near-miss single words ("cat" vs "bat" = 0.0 pass).
#   MID=0.85   (unchanged) — mid-length answers; typos score 0.88-0.96.
#   LONG=0.86  (raised from 0.82) — eliminates three false positives seen at
#               0.82: "voting rights" vs "voting rights for women" (0.831),
#               "first place shooter" vs "first person shooter" (0.833), and
#               "cold stove league" vs "the hot stove league" (0.853).
#               Real typo cases all score >= 0.889 at this tier.
SHORT_THRESHOLD = 0.90   # norm_answer len ≤ 6
MID_THRESHOLD   = 0.85   # norm_answer len 7–12
LONG_THRESHOLD  = 0.86   # norm_answer len > 12

# Gray band: scores in this range are logged for human review / model training.
# Lower bound 0.70 catches borderline near-misses; upper 0.95 captures anything
# that passed via fuzzy (clear exact/token-set passes score 1.0).
GRAY_BAND = (0.70, 0.95)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def normalize(s: str) -> str:
    """
    Full normalization pipeline:
      (a) NFKD + strip combining marks (diacritic fold: é→e, pokémon→pokemon)
      (b) lowercase + strip non-word/non-space chars
      (c) per-token number-word→digit, then gated Roman-numeral→digit
      (d) per-token UK→US spelling
      (e) stop-word strip
    Plural fold is NOT applied here — it is applied pairwise in the matcher.
    """
    # (a) diacritic fold
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # (b) lowercase + punctuation strip
    s = s.lower()
    s = re.sub(r"[^\w\s]", "", s)
    # (c) number-word and Roman canonicalization per token
    tokens = s.split()
    out = []
    for tok in tokens:
        if tok in _NUMBER_WORDS:
            out.append(_NUMBER_WORDS[tok])
        elif _is_roman(tok):
            out.append(str(_roman_to_int(tok)))
        else:
            # (d) UK→US
            out.append(_UK_US_MAP.get(tok, tok))
    # (e) stop-word strip
    out = [w for w in out if w not in _STRIP_WORDS]
    return " ".join(out)


def _normalize_tokens(s: str) -> list:
    """Return the post-normalization token list without re-splitting the joined string."""
    norm = normalize(s)
    return norm.split() if norm else []


@functools.lru_cache(maxsize=2048)
def normalize_answer(answer: str) -> str:
    """Cached normalization for stored answers (repeat frequently within a session)."""
    return normalize(answer)


# ---------------------------------------------------------------------------
# Plural fold helper (pairwise guard — never blind-stem)
# ---------------------------------------------------------------------------

def _plural_eq(a: str, b: str) -> bool:
    """True if a and b are equal or differ only by a trailing 's' or 'es'."""
    if a == b:
        return True
    if a + "s" == b or b + "s" == a:
        return True
    if a + "es" == b or b + "es" == a:
        return True
    return False


def _token_lists_match(guess_tokens: list, answer_tokens: list) -> bool:
    """
    True when every answer token finds a plural-equal partner in the guess tokens.
    Used for the token-set pass (order-independent subset check).
    """
    guess_set = set(guess_tokens)
    for atk in answer_tokens:
        if not any(_plural_eq(atk, gt) for gt in guess_set):
            return False
    return True


def _token_seq_contains(guess_tokens: list, answer_tokens: list) -> bool:
    """
    True when answer_tokens appear as a contiguous subsequence inside guess_tokens,
    with plural fold applied pairwise per token.

    This is the word-boundary-safe replacement for the raw string-substring check
    in Pass 1 multi-word matching.  It prevents 'babe ruthless' matching 'babe ruth'
    (the tokens ['babe', 'ruth'] are NOT a contiguous run of ['babe', 'ruthless']
    even though the string 'babe ruth' is a substring of 'babe ruthless').
    """
    aw = len(answer_tokens)
    gw = len(guess_tokens)
    if aw == 0:
        return True
    if gw < aw:
        return False
    for i in range(gw - aw + 1):
        if all(_plural_eq(answer_tokens[j], guess_tokens[i + j]) for j in range(aw)):
            return True
    return False


# ---------------------------------------------------------------------------
# Pass 3 scoring — RapidFuzz
# ---------------------------------------------------------------------------

def _sliding_window_score(guess_tokens: list, answer_tokens: list) -> float:
    """
    Best score over all windows of `len(answer_tokens)` in guess_tokens,
    combining char ratio, token_sort_ratio, and Jaro-Winkler.
    Combiner: max(char_ratio, token_sort_ratio) with JW as a tiebreak boost.
    Documented as tunable — the weights here are the initial hand-chosen values.
    Returns 0.0 if there are no valid windows.
    """
    window_size = len(answer_tokens)
    n = len(guess_tokens)
    if n == 0 or window_size == 0:
        return 0.0
    answer_str = " ".join(answer_tokens)
    best = 0.0
    for i in range(max(1, n - window_size + 1)):
        window = " ".join(guess_tokens[i: i + window_size])
        cr  = _fuzz.ratio(answer_str, window) / 100.0
        tsr = _fuzz.token_sort_ratio(answer_str, window) / 100.0
        jw  = _JW.normalized_similarity(answer_str, window)
        # Primary: best of char ratio and token_sort; JW adds a small boost
        # to handle transpositions that the others miss.
        combined = max(cr, tsr) * 0.85 + jw * 0.15
        if combined > best:
            best = combined
    return best


# ---------------------------------------------------------------------------
# Core _score function
# ---------------------------------------------------------------------------

def _score(guess_tokens: list, answer_tokens: list):
    """
    Run all passes for a single (guess, answer) pair.
    Returns (passed: bool, score: float, pass_name: str).
      pass_name: "exact" | "token_set" | "numeric" | "fuzzy" | "none"
    """
    if not answer_tokens:
        return False, 0.0, "none"

    window_size = len(answer_tokens)
    answer_str = " ".join(answer_tokens)
    guess_str  = " ".join(guess_tokens)

    # --- Pass 1: exact ---
    if window_size == 1:
        # Single-word answer: whole-word membership (prevents "6" matching "16").
        if any(_plural_eq(answer_tokens[0], gt) for gt in guess_tokens):
            return True, 1.0, "exact"
    else:
        # Multi-word: contiguous token-subsequence match (word-boundary safe).
        # This replaces the previous raw `answer_str in guess_str` string-substring
        # check, which was not word-boundary safe: e.g. "babe ruth" matched
        # "babe ruthless" because the string "babe ruth" is a substring of
        # "babe ruthless".  The token-subsequence check requires that the answer's
        # token sequence appears as a contiguous run in the guess's tokens, with
        # plural fold applied per-pair.
        if _token_seq_contains(guess_tokens, answer_tokens):
            return True, 1.0, "exact"
        # Order-independent fallback: every answer word present in guess (unordered).
        # Catches reversed phrasing like "pepper and salt" matching "salt and pepper".
        if _token_lists_match(guess_tokens, answer_tokens):
            return True, 1.0, "exact"

    # --- Pass 2: token-set (order-independent) ---
    if 2 <= window_size <= 5 and all(len(w) >= 4 for w in answer_tokens):
        if _token_lists_match(guess_tokens, answer_tokens):
            return True, 1.0, "token_set"

    # --- Pass 4: numeric exact ---
    is_numeric = answer_str.replace(" ", "").isdigit()
    if is_numeric:
        # Numeric answers must match exactly — no fuzzy.
        if guess_str.replace(" ", "") == answer_str.replace(" ", ""):
            return True, 1.0, "numeric"
        return False, 0.0, "numeric"

    # --- Pass 3: scored sliding-window fuzzy ---
    answer_len = len(answer_str)
    if answer_len < 4:
        return False, 0.0, "none"

    score = _sliding_window_score(guess_tokens, answer_tokens)

    if answer_len <= 6:
        threshold = SHORT_THRESHOLD
    elif answer_len <= 12:
        threshold = MID_THRESHOLD
    else:
        threshold = LONG_THRESHOLD

    return score >= threshold, score, "fuzzy"


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

# Canonical ordered list — feature vectors and model weights use this exact order.
FEATURE_NAMES = [
    "char_ratio",         # rapidfuzz char ratio against best-matching answer
    "token_sort_ratio",   # rapidfuzz token_sort_ratio against best-matching answer
    "token_set_ratio",    # rapidfuzz token_set_ratio (subset-sensitive)
    "jaro_winkler",       # Jaro-Winkler similarity
    "len_diff",           # abs(len(guess_norm) - len(answer_norm)) / max(1, max_len)
    "word_count_delta",   # abs(#words_guess - #words_answer) / max(1, max_words)
    "word_coverage",      # fraction of answer words present in guess (plural-tolerant)
    "numeric_mismatch",   # 1.0 if one side is numeric and the other is not
    "answer_len_tier",    # 0 = short (≤6), 1 = mid (7-12), 2 = long (>12)
]


def extract_features(guess: str, answer) -> dict:
    """
    Compute all features for a (guess, answer) pair.
    `answer` may be a single string or a list of acceptable answers; when a list
    is given the best-scoring answer (highest _score) is used for feature
    computation so the dict always describes the winning candidate.
    Returns a dict whose keys are exactly FEATURE_NAMES, in order.
    """
    if isinstance(answer, list):
        # Pick best answer by _score before computing features.
        guess_tokens = _normalize_tokens(guess)
        best_ans   = answer[0] if answer else ""
        best_score = -1.0
        for a in answer:
            atoks = _normalize_tokens(normalize_answer(a))
            _, sc, _ = _score(guess_tokens, atoks)
            if sc > best_score:
                best_score = sc
                best_ans   = a
        answer = best_ans
    guess_norm  = normalize(guess)
    answer_norm = normalize_answer(answer)

    guess_toks  = guess_norm.split()  if guess_norm  else []
    answer_toks = answer_norm.split() if answer_norm else []

    guess_str_n  = guess_norm
    answer_str_n = answer_norm

    # Char-level ratios against the full normalised strings.
    cr  = _fuzz.ratio(answer_str_n, guess_str_n) / 100.0          if answer_str_n else 0.0
    tsr = _fuzz.token_sort_ratio(answer_str_n, guess_str_n) / 100.0 if answer_str_n else 0.0
    tse = _fuzz.token_set_ratio(answer_str_n, guess_str_n) / 100.0  if answer_str_n else 0.0
    jw  = _JW.normalized_similarity(answer_str_n, guess_str_n)     if answer_str_n else 0.0

    gl  = len(guess_str_n)
    al  = len(answer_str_n)
    max_len   = max(1, gl, al)
    len_diff  = abs(gl - al) / max_len

    gw        = len(guess_toks)
    aw        = len(answer_toks)
    max_words = max(1, gw, aw)
    wcd       = abs(gw - aw) / max_words

    # Word coverage: fraction of answer words found in guess (plural-tolerant).
    if aw == 0:
        coverage = 0.0
    else:
        matched = sum(
            1 for atk in answer_toks
            if any(_plural_eq(atk, gt) for gt in guess_toks)
        )
        coverage = matched / aw

    # Numeric mismatch: 1.0 when exactly one side is purely numeric.
    g_num = guess_str_n.replace(" ", "").isdigit() if guess_str_n else False
    a_num = answer_str_n.replace(" ", "").isdigit() if answer_str_n else False
    num_mismatch = 1.0 if (g_num != a_num) else 0.0

    if al <= 6:
        len_tier = 0
    elif al <= 12:
        len_tier = 1
    else:
        len_tier = 2

    return {
        "char_ratio":       cr,
        "token_sort_ratio": tsr,
        "token_set_ratio":  tse,
        "jaro_winkler":     jw,
        "len_diff":         len_diff,
        "word_count_delta": wcd,
        "word_coverage":    coverage,
        "numeric_mismatch": num_mismatch,
        "answer_len_tier":  float(len_tier),
    }


# ---------------------------------------------------------------------------
# score_best
# ---------------------------------------------------------------------------

def score_best(guess: str, acceptable_answers: list):
    """
    Run _score against every answer and return the result for the best one.
    Returns (best_score: float, best_answer: str, features: dict).
    If acceptable_answers is empty, returns (0.0, "", {name: 0.0 ...}).
    """
    if not acceptable_answers:
        empty_feat = {name: 0.0 for name in FEATURE_NAMES}
        return 0.0, "", empty_feat

    guess_tokens = _normalize_tokens(guess)

    best_passed  = False
    best_score   = 0.0
    best_answer  = acceptable_answers[0]
    best_pass    = "none"

    for answer in acceptable_answers:
        answer_tokens = _normalize_tokens(normalize_answer(answer))
        passed, score, pass_name = _score(guess_tokens, answer_tokens)
        # Prefer passing answers; among equal-pass-status, take highest score.
        if (passed and not best_passed) or (passed == best_passed and score > best_score):
            best_passed = passed
            best_score  = score
            best_answer = answer
            best_pass   = pass_name

    features = extract_features(guess, best_answer)
    return best_score, best_answer, features


# ---------------------------------------------------------------------------
# Model inference — pure Python (Task 6)
# ---------------------------------------------------------------------------

MODEL_PATH = "Saves/trivia_model.json"


@functools.lru_cache(maxsize=1)
def _load_model():
    """
    Lazy, cached loader for the exported logistic-regression model.

    Reads MODEL_PATH once, validates:
      - feature_names == FEATURE_NAMES  (exact list equality)
      - matcher_version == MATCHER_VERSION

    Returns the parsed dict on success, or None on:
      - missing file
      - JSON parse error
      - validation mismatch

    Never raises.  Call reload_model() to clear the cache (e.g. after the
    trainer writes a new file, or in tests).
    """
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        with open(MODEL_PATH, encoding="utf-8") as f:
            m = json.load(f)
        if m.get("feature_names") != FEATURE_NAMES:
            return None
        if m.get("matcher_version") != MATCHER_VERSION:
            return None
        return m
    except Exception:
        return None


def reload_model() -> None:
    """Clear the cached model so the next verdict() call re-reads MODEL_PATH."""
    _load_model.cache_clear()


def _predict_proba(model: dict, features: dict) -> float:
    """
    Pure-Python logistic-regression inference.

    Computes dot(weights, feature_vector) + bias through a stdlib sigmoid.
    Feature vector is assembled in FEATURE_NAMES order from the features dict.
    No heavy ML libraries — the bot host may not have them (stdlib math only).
    """
    weights = model["weights"]
    bias    = model["bias"]
    dot = sum(weights[i] * features.get(FEATURE_NAMES[i], 0.0)
              for i in range(len(FEATURE_NAMES)))
    # Sigmoid: 1 / (1 + exp(-(dot + bias)))
    return 1.0 / (1.0 + math.exp(-(dot + bias)))


# ---------------------------------------------------------------------------
# verdict
# ---------------------------------------------------------------------------

def verdict(guess: str, acceptable_answers: list) -> dict:
    """
    Grade a guess against the list of acceptable answers.

    Returns:
      {
        "correct":      bool,
        "score":        float,
        "best_answer":  str,
        "features":     dict,
        "in_gray_band": bool,
        "source":       "hand" | "model",
      }

    Decision path:
      - Passes 1 (exact), 2 (token_set), and 4 (numeric) are deterministic hard-True
        regardless of whether a model is loaded.  These are not subject to model
        override because they are exact/structural matches with no score ambiguity.
      - Pass 3 (fuzzy) / gray decision: the model replaces the hand decision ONLY
        when a valid model is loaded AND in_gray_band is True (score in GRAY_BAND).
        Outside the band the hand verdict is deterministic (clear accept or clear
        reject) and the model is not consulted.  source="model" therefore implies
        both a loaded model and an in-band score; source="hand" in all other cases.

    in_gray_band is computed from the raw best_score against GRAY_BAND regardless
    of the decision source, so gray-zone logging continues unaffected.
    """
    if not acceptable_answers:
        return {
            "correct": False, "score": 0.0, "best_answer": "",
            "features": {n: 0.0 for n in FEATURE_NAMES},
            "in_gray_band": False, "source": "hand",
        }

    # Delegate answer selection and feature extraction to score_best — single
    # implementation of the loop (previously duplicated verbatim here).
    best_score, best_answer, features = score_best(guess, acceptable_answers)

    # Re-run _score on the winning answer to get the pass verdict and pass_name.
    # This is a single O(1) call rather than re-iterating over all answers.
    guess_tokens  = _normalize_tokens(guess)
    answer_tokens = _normalize_tokens(normalize_answer(best_answer))
    hard_correct, _, pass_name = _score(guess_tokens, answer_tokens)

    # in_gray_band is always computed from the raw score, independent of source.
    in_gray = GRAY_BAND[0] <= best_score <= GRAY_BAND[1]

    # Passes 1/2/4 (exact, token_set, numeric) are hard-True — model does not apply.
    if pass_name in ("exact", "token_set", "numeric"):
        return {
            "correct":      hard_correct,
            "score":        best_score,
            "best_answer":  best_answer,
            "features":     features,
            "in_gray_band": in_gray,
            "source":       "hand",
        }

    # Pass-3 / gray decision: model replaces ONLY the gray-band decision.
    # The model is consulted when a valid model is loaded AND the score falls
    # inside [GRAY_BAND[0], GRAY_BAND[1]].  Outside the band the hand verdict
    # is deterministic (clear accept above the band, clear reject below), so
    # the model cannot improve on it and should not override it.
    model = _load_model()
    if model is not None and in_gray:
        correct = _predict_proba(model, features) >= model["cutoff"]
        source  = "model"
    else:
        correct = hard_correct   # hand tier-threshold (or out-of-band clear decision)
        source  = "hand"

    return {
        "correct":      correct,
        "score":        best_score,
        "best_answer":  best_answer,
        "features":     features,
        "in_gray_band": in_gray,
        "source":       source,
    }


# ---------------------------------------------------------------------------
# Public boolean API (drop-in replacement for TriviaModule.is_correct_answer)
# ---------------------------------------------------------------------------

def is_correct_answer(guess: str, acceptable_answers: list) -> bool:
    """Boolean wrapper around verdict — preserves the existing call-site API."""
    return verdict(guess, acceptable_answers)["correct"]


# ---------------------------------------------------------------------------
# Gray-zone JSONL logger
# ---------------------------------------------------------------------------

GRAYLOG_PATH = "Saves/trivia_graylog.jsonl"


def log_gray(guild_id: str, question: str, answers: list, guess: str, result: dict) -> None:
    """
    Append one JSON line to GRAYLOG_PATH when result["in_gray_band"] is True.

    Fields written:
      ts              ISO-8601 UTC timestamp
      guild_id        string (empty string in DMs)
      question        the question text
      answers         list of acceptable answers
      guess           the player's guess
      features        feature dict from result
      verdict         bool — what the matcher decided
      matcher_version MATCHER_VERSION

    The write is wrapped in try/except so a logging failure never breaks grading.
    """
    if not result.get("in_gray_band"):
        return
    try:
        os.makedirs("Saves", exist_ok=True)
        record = {
            "ts":              datetime.now(timezone.utc).isoformat(),
            "guild_id":        str(guild_id),
            "question":        question,
            "answers":         list(answers),
            "guess":           guess,
            "features":        result.get("features", {}),
            "verdict":         bool(result.get("correct", False)),
            "matcher_version": MATCHER_VERSION,
        }
        with open(GRAYLOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Label store — human-reviewed labels for model training
# ---------------------------------------------------------------------------

LABELS_PATH = "Saves/trivia_labels.jsonl"


def append_label(entry: dict, label: str) -> None:
    """
    Append a labeled row to LABELS_PATH.

    Writes all original entry fields verbatim plus:
      label        "correct" | "incorrect"
      labeled_ts   ISO-8601 UTC timestamp

    The trainer (trivia_training/train.py) expects fields: guess, answers,
    features, label, matcher_version — all preserved from the graylog entry.
    Wrapped in try/except so a write failure never crashes the caller.
    """
    try:
        os.makedirs("Saves", exist_ok=True)
        row = dict(entry)
        row["label"] = label
        row["labeled_ts"] = datetime.now(timezone.utc).isoformat()
        with open(LABELS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def load_graylog() -> list:
    """
    Read all records from GRAYLOG_PATH.
    Returns an empty list if the file does not exist.
    Skips malformed (non-JSON) lines silently.
    """
    rows = []
    if not os.path.exists(GRAYLOG_PATH):
        return rows
    try:
        with open(GRAYLOG_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return rows


def load_labels() -> list:
    """
    Read all labeled rows from LABELS_PATH.
    Returns an empty list if the file does not exist.
    Skips malformed lines silently.
    Each row is a raw dict compatible with the trivia_training reader which
    expects: guess, answers, features, label, matcher_version.
    """
    rows = []
    if not os.path.exists(LABELS_PATH):
        return rows
    try:
        with open(LABELS_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return rows
