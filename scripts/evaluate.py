#!/usr/bin/env python3
"""Retrieval evaluation harness.

Measures top-1 and top-3 accuracy over a labelled set of paraphrased questions,
and checks that off-topic questions land below MIN_CONFIDENCE. Run it after any
change to the tokenizer, the scoring weights, or the knowledge base:

    python scripts/evaluate.py
    python scripts/evaluate.py --verbose     # show every failure
    python scripts/evaluate.py --sweep       # sweep the confidence threshold

Exits non-zero if accuracy or rejection rate regresses past the floors below, so
it can be wired into CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fundbot import guards  # noqa: E402
from fundbot.knowledge import get_retriever  # noqa: E402
from fundbot.retrieval import MIN_CONFIDENCE  # noqa: E402

MIN_TOP1 = 0.85
MIN_TOP3 = 0.95
MIN_REJECTION = 1.0
MIN_ANSWERED = 0.90

# Questions about other fund houses that retrieval alone would answer with a
# Mirae figure. These must be caught by the scope guard, not by confidence.
COMPETITOR_QUESTIONS = [
    "what is the expense ratio of HDFC Top 100 fund",
    "minimum sip for SBI bluechip fund",
    "exit load on Axis midcap fund",
    "what is the benchmark for Parag Parikh Flexi Cap",
    "riskometer of Nippon India small cap",
]

# Paraphrases a user would plausibly type, none copied verbatim from the
# knowledge base's own `questions` lists — otherwise this would only prove the
# index can find text it was handed.
LABELLED: list[tuple[str, str]] = [
    ("how much does the large cap fund cost me each year", "large_cap.expense_ratio"),
    ("annual fee on mirae large cap", "large_cap.expense_ratio"),
    ("if I pull out of large cap after 6 months what do I pay", "large_cap.exit_load"),
    ("cheapest monthly amount for large cap", "large_cap.sip_minimum"),
    ("one shot investment minimum large cap", "large_cap.lump_sum_minimum"),
    ("which index is large cap fund measured against", "large_cap.benchmark"),
    ("how dangerous is the large cap scheme", "large_cap.riskometer"),
    ("can I do quarterly instalments in large cap", "large_cap.sip_frequency"),
    ("what kind of scheme is mirae large cap", "large_cap.category"),

    ("yearly charges on flexi cap", "flexi_cap.expense_ratio"),
    ("redemption fee flexi cap within a year", "flexi_cap.exit_load"),
    ("least I can invest monthly in flexi cap", "flexi_cap.sip_minimum"),
    ("minimum one time amount flexi cap", "flexi_cap.lump_sum_minimum"),
    ("flexi cap tracks which index", "flexi_cap.benchmark"),
    ("risk rating of flexi cap fund", "flexi_cap.riskometer"),
    ("does flexi cap allow stp", "flexi_cap.sip_frequency"),

    ("what does the tax saver fund charge yearly", "elss.expense_ratio"),
    ("smallest monthly amount for tax saver", "elss.sip_minimum"),
    ("how long is money stuck in mirae elss", "elss.elss_lockin"),
    ("can I take money out of elss after 2 years", "elss.elss_lockin"),
    ("tax saver risk rating", "elss.riskometer"),
    ("which benchmark for mirae elss", "elss.benchmark"),

    ("yearly cost of the midcap scheme", "midcap.expense_ratio"),
    ("charge for exiting midcap early", "midcap.exit_load"),
    ("minimum monthly for midcap", "midcap.sip_minimum"),
    ("midcap fund tracks what index", "midcap.benchmark"),
    ("how risky is midcap", "midcap.riskometer"),
    ("what companies does midcap invest in", "midcap.category"),

    ("what does sip stand for", "general.what_is_sip"),
    ("meaning of expense ratio", "general.what_is_expense_ratio"),
    ("explain exit load to me", "general.what_is_exit_load"),
    ("what does net asset value mean", "general.what_is_nav"),
    ("what is an equity linked savings scheme", "general.what_is_elss"),
    ("why is a direct plan cheaper", "general.direct_vs_regular"),
    ("where do I get my capital gains statement", "general.statement_download"),
    ("do I need kyc before investing", "general.kyc"),
    ("tax on selling equity fund units", "general.equity_taxation"),
    ("what is a systematic withdrawal plan", "general.what_is_swp"),
    ("what is a systematic transfer plan", "general.what_is_stp"),
    ("how many risk categories does sebi define", "general.what_is_riskometer"),
    ("which funds can you answer about", "general.coverage"),
]

# Two flavours: unrelated questions, and finance-adjacent ones that share a lot
# of vocabulary with the corpus. The second group is the hard one — it is where a
# confidence threshold tuned on easy negatives quietly starts inventing answers.
OFF_TOPIC = [
    "how do I bake sourdough bread",
    "what is the capital of Mongolia",
    "who won the 2019 cricket world cup",
    "write me a python script to sort a list",
    "what is the weather tomorrow",
    "tell me a joke about accountants",
    "what is the share price of Reliance Industries",
    "how do I open a demat account",
    "what is the current repo rate",
    "explain how bitcoin mining works",
    "what are the trading hours of the NSE",
    "how do I file my income tax return online",
]


def evaluate(verbose: bool = False) -> tuple[float, float, float, float, float]:
    retriever = get_retriever()

    top1 = top3 = answered = 0
    failures: list[tuple[str, str, list[str]]] = []
    quiet: list[tuple[str, float, str]] = []

    for question, expected in LABELLED:
        hits = retriever.search(question, top_k=3)
        ids = [hit.document.id for hit in hits]
        confidence = hits[0].confidence if hits else 0.0
        if confidence >= MIN_CONFIDENCE:
            answered += 1
        else:
            quiet.append((question, confidence, expected))
        if ids[:1] == [expected]:
            top1 += 1
        if expected in ids:
            top3 += 1
        else:
            failures.append((question, expected, ids))

    rejected = 0
    leaks: list[tuple[str, float, str]] = []
    for question in OFF_TOPIC:
        hits = retriever.search(question, top_k=1)
        confidence = hits[0].confidence if hits else 0.0
        if confidence < MIN_CONFIDENCE:
            rejected += 1
        else:
            leaks.append((question, confidence, hits[0].document.id))

    # Scope guard: competitor-AMC questions must never reach retrieval.
    scoped = sum(1 for q in COMPETITOR_QUESTIONS if guards.check_scope(q) is not None)
    scope_rate = scoped / len(COMPETITOR_QUESTIONS)

    total = len(LABELLED)
    top1_rate = top1 / total
    top3_rate = top3 / total
    answered_rate = answered / total
    rejection_rate = rejected / len(OFF_TOPIC)

    print(f"Labelled questions : {total}")
    print(f"Top-1 accuracy     : {top1_rate:6.1%}  ({top1}/{total})   floor {MIN_TOP1:.0%}")
    print(f"Top-3 accuracy     : {top3_rate:6.1%}  ({top3}/{total})   floor {MIN_TOP3:.0%}")
    print(
        f"Answered (>= floor): {answered_rate:6.1%}  ({answered}/{total})   "
        f"floor {MIN_ANSWERED:.0%}"
    )
    print(
        f"Off-topic rejected : {rejection_rate:6.1%}  "
        f"({rejected}/{len(OFF_TOPIC)})   floor {MIN_REJECTION:.0%}"
    )
    print(
        f"Competitor scoped  : {scope_rate:6.1%}  "
        f"({scoped}/{len(COMPETITOR_QUESTIONS)})   floor 100%"
    )
    print(f"MIN_CONFIDENCE     : {MIN_CONFIDENCE}")

    if verbose and failures:
        print("\nMissed (expected not in top 3):")
        for question, expected, ids in failures:
            print(f"  {question!r}\n    want {expected}\n    got  {ids}")

    if verbose and quiet:
        print("\nCorrectly retrieved but below the confidence floor (answered 'I don't know'):")
        for question, confidence, expected in quiet:
            print(f"  {confidence:.4f}  {question!r}  (want {expected})")

    if leaks:
        print("\nOff-topic questions that cleared the threshold:")
        for question, confidence, doc_id in leaks:
            print(f"  {question!r} -> {doc_id} at {confidence:.4f}")

    return top1_rate, top3_rate, answered_rate, rejection_rate, scope_rate


def sweep() -> None:
    """Show how the threshold trades answered questions against false answers."""
    retriever = get_retriever()

    on_topic = [retriever.search(q, top_k=1) for q, _ in LABELLED]
    off_topic = [retriever.search(q, top_k=1) for q in OFF_TOPIC]

    def confidence(hits):
        return hits[0].confidence if hits else 0.0

    on_scores = [confidence(h) for h in on_topic]
    off_scores = [confidence(h) for h in off_topic]

    print(f"on-topic  confidence: min {min(on_scores):.4f}  max {max(on_scores):.4f}")
    print(f"off-topic confidence: min {min(off_scores):.4f}  max {max(off_scores):.4f}")
    print("\nthreshold   answered   false-answers")
    for step in range(0, 31):
        threshold = step / 100
        answered = sum(1 for s in on_scores if s >= threshold) / len(on_scores)
        false = sum(1 for s in off_scores if s >= threshold)
        marker = "  <- current" if abs(threshold - MIN_CONFIDENCE) < 0.005 else ""
        print(f"   {threshold:.2f}      {answered:6.1%}        {false}{marker}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="list every miss")
    parser.add_argument("--sweep", action="store_true", help="sweep MIN_CONFIDENCE")
    args = parser.parse_args()

    if args.sweep:
        sweep()
        return 0

    top1, top3, answered, rejection, scope = evaluate(verbose=args.verbose)
    ok = (
        top1 >= MIN_TOP1
        and top3 >= MIN_TOP3
        and answered >= MIN_ANSWERED
        and rejection >= MIN_REJECTION
        and scope >= 1.0
    )
    print("\n" + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
