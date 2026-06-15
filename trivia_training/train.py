"""
Offline trainer for the TriviaMatching gray-zone classifier.

Reads labeled gray-zone guesses from a JSONL file, trains an L2 logistic
regression over TriviaMatching feature vectors, evaluates accuracy before and
after against the golden set, and exports model coefficients to
Saves/trivia_model.json.

Dev-only — never runs on the bot host.  sklearn/numpy are NOT imported by
TriviaMatching or the bot runtime.

Usage:
    python -m trivia_training.train
    python -m trivia_training.train --labels path/to/labels.jsonl
    python -m trivia_training.train --labels path/to/labels.jsonl --cutoff 0.5

Output:
    Saves/trivia_model.json  — model weights/bias/metadata for Task-6 inference
"""

import argparse
import json
import math
import os
import sys
from typing import Optional

# ---------------------------------------------------------------------------
# Resolve repo root so this module works from any cwd.
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import TriviaMatching  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DEFAULT_LABELS_PATH = os.path.join(_REPO_ROOT, "Saves", "trivia_labels.jsonl")
_MODEL_PATH          = os.path.join(_REPO_ROOT, "Saves", "trivia_model.json")
_GOLDEN_PATH         = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "golden.jsonl"
)

# ---------------------------------------------------------------------------
# Training constants
# ---------------------------------------------------------------------------
MIN_LABELS = 50   # minimum usable labeled rows before training is attempted
DEFAULT_CUTOFF = 0.5


# ---------------------------------------------------------------------------
# Local label reader
# (TriviaMatching.load_labels() is Task-4's deliverable and may not exist yet;
#  implement reading locally so train.py is self-contained.)
# ---------------------------------------------------------------------------

def _read_labels(path: str) -> list:
    """
    Read labeled gray-zone records from a JSONL file.

    Tolerates:
    - Missing file → returns empty list (do not raise).
    - Malformed JSON lines → skip with a warning.

    Expected row schema:
        {
          "guess":           str,
          "answers":         [str, ...],
          "features":        {name: float, ...},   # optional; recompute if absent
          "label":           "correct" | "incorrect",
          "matcher_version": str,                   # optional but checked
          ... (other fields tolerated and ignored)
        }
    """
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  WARNING: labels line {lineno} skipped (JSON error: {exc})",
                      file=sys.stderr)
                continue
            rows.append(obj)
    return rows


# ---------------------------------------------------------------------------
# Feature vector extraction
# ---------------------------------------------------------------------------

def _get_feature_vector(row: dict) -> Optional[list]:
    """
    Return a feature vector (list of floats in FEATURE_NAMES order) for one row.

    Strategy:
    1. If the row has a "features" dict AND its matcher_version matches
       TriviaMatching.MATCHER_VERSION, reuse the stored vector — it was computed
       at log time by the same matcher, so there is no skew.
    2. Otherwise, recompute via TriviaMatching.extract_features (fallback).

    Returns None if the row is unusable (e.g. missing guess/answers).
    """
    guess   = row.get("guess")
    answers = row.get("answers")
    if not isinstance(guess, str) or not isinstance(answers, list) or not answers:
        return None

    stored_features  = row.get("features")
    stored_version   = row.get("matcher_version")
    use_stored       = (
        isinstance(stored_features, dict)
        and stored_version == TriviaMatching.MATCHER_VERSION
        and all(name in stored_features for name in TriviaMatching.FEATURE_NAMES)
    )

    if use_stored:
        return [float(stored_features[name]) for name in TriviaMatching.FEATURE_NAMES]

    # Fallback: recompute from the raw guess/answers.
    try:
        feat = TriviaMatching.extract_features(guess, answers)
        return [float(feat[name]) for name in TriviaMatching.FEATURE_NAMES]
    except Exception as exc:
        print(f"  WARNING: could not compute features for ({guess!r}, {answers}): {exc}",
              file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Golden-set evaluation helpers
# ---------------------------------------------------------------------------

def _load_golden() -> list:
    """Load golden.jsonl cases. Returns list of (guess, answers, expected) tuples."""
    if not os.path.exists(_GOLDEN_PATH):
        return []
    cases = []
    with open(_GOLDEN_PATH, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            guess   = obj.get("guess", "")
            answers = obj.get("answers", [])
            expected = obj.get("expected")
            if expected is None:
                continue
            cases.append((guess, answers, expected))
    return cases


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _model_predict(features: dict, weights: list, bias: float, cutoff: float) -> bool:
    """Apply logistic regression inference in pure Python."""
    dot = sum(
        weights[i] * float(features[name])
        for i, name in enumerate(TriviaMatching.FEATURE_NAMES)
    )
    prob = _sigmoid(dot + bias)
    return prob >= cutoff


def _eval_golden_hand(cases: list) -> float:
    """Evaluate golden set using TriviaMatching hand thresholds."""
    if not cases:
        return 0.0
    correct = sum(
        1 for guess, answers, expected in cases
        if TriviaMatching.is_correct_answer(guess, answers) == expected
    )
    return correct / len(cases)


def _eval_golden_model(cases: list, weights: list, bias: float, cutoff: float) -> float:
    """
    Evaluate golden set using the trained model for gray-band cases.

    For non-gray-band cases (score < GRAY_BAND[0] or > GRAY_BAND[1]) the hand
    verdict is authoritative and unchanged.  For gray-band cases, apply the
    trained logistic regression.
    """
    if not cases:
        return 0.0
    correct = 0
    for guess, answers, expected in cases:
        v = TriviaMatching.verdict(guess, answers)
        if v["in_gray_band"]:
            # Gray-band: let the model decide.
            pred = _model_predict(v["features"], weights, bias, cutoff)
        else:
            pred = v["correct"]
        if pred == expected:
            correct += 1
    return correct / len(cases)


# ---------------------------------------------------------------------------
# Main training routine
# ---------------------------------------------------------------------------

def train(labels_path: str = _DEFAULT_LABELS_PATH, cutoff: float = DEFAULT_CUTOFF):
    """
    Full training pipeline:
      1. Read labels.
      2. Build feature matrix X and label vector y.
      3. Guard: exit non-zero if fewer than MIN_LABELS usable rows.
      4. Train L2 logistic regression.
      5. Evaluate before/after on the golden set.
      6. Export model JSON to Saves/trivia_model.json.
    """
    # ------------------------------------------------------------------
    # 1. Read labels
    # ------------------------------------------------------------------
    print(f"Reading labels from: {labels_path}")
    rows = _read_labels(labels_path)
    print(f"  Raw rows read: {len(rows)}")

    # ------------------------------------------------------------------
    # 2. Build X, y
    # ------------------------------------------------------------------
    X = []
    y = []
    skipped = 0
    for row in rows:
        label = row.get("label")
        if label not in ("correct", "incorrect"):
            skipped += 1
            continue
        fvec = _get_feature_vector(row)
        if fvec is None:
            skipped += 1
            continue
        X.append(fvec)
        y.append(1 if label == "correct" else 0)

    print(f"  Usable rows: {len(X)}  (skipped: {skipped})")

    # ------------------------------------------------------------------
    # 3. Guard
    # ------------------------------------------------------------------
    if len(X) < MIN_LABELS:
        print(
            f"\nERROR: only {len(X)} usable labeled row(s); minimum is {MIN_LABELS}.\n"
            f"Collect more labels via .trivia_review before training.\n"
            f"No model written.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ------------------------------------------------------------------
    # 4. Train
    # ------------------------------------------------------------------
    # sklearn and numpy are imported HERE (dev-only; never at module level).
    from sklearn.linear_model import LogisticRegression  # noqa: PLC0415
    import numpy as np                                   # noqa: PLC0415

    X_arr = np.array(X, dtype=float)
    y_arr = np.array(y, dtype=int)

    clf = LogisticRegression(penalty="l2", solver="lbfgs", max_iter=1000)
    clf.fit(X_arr, y_arr)

    weights = clf.coef_[0].tolist()
    bias    = float(clf.intercept_[0])

    print(f"\nModel trained:")
    print(f"  Features : {TriviaMatching.FEATURE_NAMES}")
    print(f"  Weights  : {[round(w, 4) for w in weights]}")
    print(f"  Bias     : {round(bias, 4)}")
    print(f"  Cutoff   : {cutoff}")

    # ------------------------------------------------------------------
    # 5. Before/after golden eval
    # ------------------------------------------------------------------
    golden_cases = _load_golden()
    if golden_cases:
        acc_hand  = _eval_golden_hand(golden_cases)
        acc_model = _eval_golden_model(golden_cases, weights, bias, cutoff)
        delta     = acc_model - acc_hand
        print(f"\nGolden-set evaluation ({len(golden_cases)} cases):")
        print(f"  Hand-threshold accuracy : {acc_hand:.1%}")
        print(f"  Model accuracy          : {acc_model:.1%}")
        print(f"  Delta                   : {delta:+.1%}")
        if acc_model < acc_hand:
            print("  WARNING: model is worse than hand thresholds on the golden set.",
                  file=sys.stderr)
    else:
        print("\nWARNING: golden.jsonl not found or empty — skipping before/after eval.",
              file=sys.stderr)

    # ------------------------------------------------------------------
    # 6. Export model JSON
    # ------------------------------------------------------------------
    os.makedirs(os.path.dirname(_MODEL_PATH), exist_ok=True)
    model = {
        "weights":         weights,
        "bias":            bias,
        "feature_names":   list(TriviaMatching.FEATURE_NAMES),
        "matcher_version": TriviaMatching.MATCHER_VERSION,
        "cutoff":          cutoff,
    }
    with open(_MODEL_PATH, "w", encoding="utf-8") as fh:
        json.dump(model, fh, indent=2)
    print(f"\nModel written to: {_MODEL_PATH}")

    # Sanity check the written file.
    with open(_MODEL_PATH, encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded["feature_names"] == TriviaMatching.FEATURE_NAMES, "feature_names mismatch!"
    assert len(loaded["weights"]) == len(loaded["feature_names"]), "weights length mismatch!"
    print("  Sanity check passed.")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Train TriviaMatching gray-zone classifier and export model JSON."
    )
    parser.add_argument(
        "--labels",
        default=_DEFAULT_LABELS_PATH,
        help=f"Path to trivia_labels.jsonl (default: {_DEFAULT_LABELS_PATH})",
    )
    parser.add_argument(
        "--cutoff",
        type=float,
        default=DEFAULT_CUTOFF,
        help=f"Classification probability cutoff (default: {DEFAULT_CUTOFF})",
    )
    args = parser.parse_args()
    train(labels_path=args.labels, cutoff=args.cutoff)


if __name__ == "__main__":
    main()
