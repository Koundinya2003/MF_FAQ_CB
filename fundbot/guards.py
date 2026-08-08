"""Input guardrails: personal data and investment-advice refusals.

These run *before* retrieval, so a blocked question never reaches the knowledge
base or the LLM.

The patterns are deliberately narrower than a keyword blocklist. Bare
substring checks on words like "buy" or "sell" fire on perfectly factual
questions ("what is the exit load if I sell within a year?"), and a refusal
there is a worse failure than answering: it teaches users the bot is broken.
Advice detection therefore keys on the *framing* that asks for a judgement, not
on transaction vocabulary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

AMFI_URL = "https://www.amfiindia.com/investor-corner"

PII_MESSAGE = (
    "Please do not share personal identifiers such as PAN, Aadhaar, folio numbers, "
    "email addresses or phone numbers here. FundBot answers general scheme questions "
    "and never needs your personal details."
)

ADVICE_MESSAGE = (
    "I can only share factual scheme information — I can't give investment advice, "
    "recommend a fund, or predict returns. For guidance on what suits your situation, "
    "please consult a SEBI-registered investment adviser."
)

SCOPE_MESSAGE = (
    "I only cover Mirae Asset schemes — the Large Cap, Flexi Cap, ELSS Tax Saver and "
    "Midcap funds. For schemes from another fund house, please check that AMC's own "
    "site or the AMFI scheme directory, so you get their figures rather than Mirae's."
)

AMFI_SCHEME_URL = "https://www.amfiindia.com/investor-corner"

# Other Indian AMCs. A question naming one of these shares almost all of its
# vocabulary with the corpus ("expense ratio of HDFC Top 100 fund"), so retrieval
# answers it confidently with a *Mirae* figure — the single most misleading
# failure this bot can produce. Scope has to be checked explicitly; no confidence
# threshold can distinguish these, because the match really is strong.
_OTHER_AMCS = (
    "hdfc", "sbi", "icici", "prudential", "axis", "kotak", "nippon", "reliance mutual",
    "aditya birla", "birla sun life", "uti", "dsp", "franklin", "templeton", "tata mutual",
    "quant", "parag parikh", "ppfas", "motilal", "edelweiss", "canara", "robeco", "bandhan",
    "invesco", "pgim", "jm financial", "lic mutual", "baroda", "sundaram", "hsbc",
    "360 one", "navi", "zerodha", "groww", "whiteoak", "white oak", "helios", "bajaj",
    "mahindra manulife", "iti mutual", "samco", "taurus", "union mutual", "quantum",
    "shriram", "trust mutual", "old bridge", "unifi",
)

_OTHER_AMC_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in _OTHER_AMCS) + r")\b", re.IGNORECASE
)
_MIRAE_PATTERN = re.compile(r"\bmirae\b", re.IGNORECASE)

_PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("pan", re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b")),
    # Aadhaar: 12 digits, optionally grouped in fours.
    ("aadhaar", re.compile(r"\b\d{4}[ -]?\d{4}[ -]?\d{4}\b")),
    ("phone", re.compile(r"(?:\+91[ -]?)?\b[6-9]\d{9}\b")),
    ("account_number", re.compile(r"\b\d{9,18}\b")),
    (
        "credential",
        re.compile(
            r"\b(my\s+pan|pan\s+(?:card|number|no)|aadhaar|aadhar|"
            r"folio\s*(?:number|no)|otp|password|cvv|card\s*number|"
            r"bank\s*account\s*(?:number|no)|net\s*banking)\b",
            re.IGNORECASE,
        ),
    ),
)

_ADVICE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bshould\s+(?:i|we|he|she|they|one)\b", re.IGNORECASE),
    re.compile(r"\b(?:shall|can|could)\s+(?:i|we)\s+(?:invest|buy|put|start)\b", re.IGNORECASE),
    re.compile(r"\b(?:which|what)\s+(?:fund|scheme|one)\s+(?:is\s+)?(?:better|best|should)\b", re.IGNORECASE),
    re.compile(r"\b(?:best|top|safest|ideal|perfect)\s+(?:fund|scheme|investment|option)\b", re.IGNORECASE),
    re.compile(r"\bwhich\s+is\s+better\b", re.IGNORECASE),
    re.compile(r"\bworth\s+(?:investing|buying|it)\b", re.IGNORECASE),
    re.compile(r"\b(?:recommend|suggest)\b", re.IGNORECASE),
    re.compile(r"\bgood\s+(?:time|idea|investment|choice)\b", re.IGNORECASE),
    re.compile(r"\bis\s+it\s+safe\s+to\s+invest\b", re.IGNORECASE),
    re.compile(
        r"\b(?:will|would)\s+(?:the\s+|this\s+|it\s+)?"
        r"(?:it|this|fund|scheme|nav|market|price|value|return)s?\s+"
        r"(?:go|rise|fall|grow|drop|crash|double|increase|decrease|beat)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:future|expected|predicted)\s+(?:return|performance|nav|price)\b", re.IGNORECASE),
    re.compile(r"\bhow\s+much\s+(?:return|profit|money)\s+(?:will|would|can)\b", re.IGNORECASE),
    re.compile(r"\bpredict\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class GuardResult:
    """A blocked question, with the canned reply to serve instead."""

    kind: str  # "pii" or "advice"
    answer: str
    source: str
    detail: str = ""


def check_pii(question: str) -> GuardResult | None:
    for label, pattern in _PII_PATTERNS:
        if pattern.search(question):
            return GuardResult(kind="pii", answer=PII_MESSAGE, source="", detail=label)
    return None


def check_advice(question: str) -> GuardResult | None:
    for pattern in _ADVICE_PATTERNS:
        if pattern.search(question):
            return GuardResult(
                kind="advice",
                answer=ADVICE_MESSAGE,
                source=AMFI_URL,
                detail=pattern.pattern,
            )
    return None


def check_scope(question: str) -> GuardResult | None:
    """Block questions about other fund houses.

    A bare mention of another AMC is only out of scope when Mirae is not also
    named — "how does this compare to how HDFC reports TER" is a comparison the
    advice guard handles, and "Mirae vs HDFC" should not be silently reframed as
    a Mirae-only answer either, but naming Mirae at least means the user is
    asking about a scheme we hold.
    """
    match = _OTHER_AMC_PATTERN.search(question)
    if match and not _MIRAE_PATTERN.search(question):
        return GuardResult(
            kind="scope",
            answer=SCOPE_MESSAGE,
            source=AMFI_SCHEME_URL,
            detail=match.group(1).lower(),
        )
    return None


def screen(question: str) -> GuardResult | None:
    """Run every guard.

    Order matters: PII first so identifiers are never echoed onward, then scope,
    so a question about another AMC is refused as out of scope rather than being
    answered with Mirae Asset's numbers.
    """
    return check_pii(question) or check_scope(question) or check_advice(question)
