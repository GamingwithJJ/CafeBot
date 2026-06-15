"""
Golden test harness for TriviaMatching.

Run from repo root:
    python -m trivia_training.run_golden

Reads trivia_training/golden.jsonl, runs TriviaMatching.is_correct_answer on
each case, and reports accuracy.  Exits non-zero if any mismatch is found.

The golden set IS the spec — if a case is genuinely ambiguous, fix the case
(with a note) rather than silently adjusting thresholds.  If a threshold must
be changed to fix a real correctness bug, document it here.
"""

import json
import os
import sys

# Resolve repo root so this script runs correctly from any cwd.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)

import TriviaMatching  # noqa: E402 — inserted after path fixup

_GOLDEN_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "golden.jsonl"
)


def load_golden():
    """Load and parse golden.jsonl; skip blank lines and comment lines."""
    cases = []
    with open(_GOLDEN_PATH, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("//") or line.startswith("#"):
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"  WARNING: golden.jsonl line {lineno} parse error: {exc}", file=sys.stderr)
                continue
            cases.append((lineno, obj))
    return cases


def run():
    cases = load_golden()
    if not cases:
        print("ERROR: golden.jsonl is empty or missing.", file=sys.stderr)
        sys.exit(1)

    total = len(cases)
    passed = 0
    mismatches = []

    for lineno, obj in cases:
        guess = obj.get("guess", "")
        answers = obj.get("answers", [])
        expected = obj.get("expected")
        note = obj.get("note", "")

        if expected is None:
            print(f"  WARNING: line {lineno} missing 'expected' field — skipped", file=sys.stderr)
            total -= 1
            continue

        got = TriviaMatching.is_correct_answer(guess, answers)

        if got == expected:
            passed += 1
        else:
            v = TriviaMatching.verdict(guess, answers)
            mismatches.append({
                "line": lineno,
                "guess": guess,
                "answers": answers,
                "expected": expected,
                "got": got,
                "score": v["score"],
                "note": note,
            })

    accuracy = passed / total if total > 0 else 0.0

    print(f"TriviaMatching golden harness")
    print(f"  Thresholds: SHORT={TriviaMatching.SHORT_THRESHOLD}  MID={TriviaMatching.MID_THRESHOLD}  LONG={TriviaMatching.LONG_THRESHOLD}")
    print(f"  GRAY_BAND:  {TriviaMatching.GRAY_BAND}")
    print(f"  Total cases:  {total}")
    print(f"  Passed:       {passed}")
    print(f"  Accuracy:     {accuracy:.1%}")

    if mismatches:
        print(f"\n  *** {len(mismatches)} MISMATCH(ES) ***")
        for m in mismatches:
            flag = "FALSE_POS" if m["got"] else "FALSE_NEG"
            print(
                f"  [{flag}] line {m['line']}  score={m['score']:.3f}"
                f"\n    guess   : {m['guess']!r}"
                f"\n    answers : {m['answers']}"
                f"\n    expected: {m['expected']}  got: {m['got']}"
                f"\n    note    : {m['note']}"
            )
        print()
        sys.exit(1)
    else:
        print("\n  All cases passed.")
        sys.exit(0)


if __name__ == "__main__":
    run()
