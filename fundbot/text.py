"""Tokenisation and query normalisation.

Pure standard library on purpose: the whole retrieval stack has to fit inside a
Vercel serverless bundle with a cold start measured in milliseconds, so there is
no numpy, no scikit-learn and no torch anywhere in this package.
"""

from __future__ import annotations

import re
import unicodedata

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Dropped before indexing and before scoring. Deliberately short: an aggressive
# stopword list would strip "what is" phrasing that distinguishes a definition
# question ("what is an exit load") from a scheme lookup ("exit load of midcap").
STOPWORDS = frozenset(
    """
    a an the of for to in on at by is are was were be been being do does did
    and or if it its this that these those there here as with from into
    i me my we our you your he she they them their
    can could would should shall will may might must
    please tell give show
    """.split()
)

# Expansions, not replacements: the original token is always kept and these are
# appended, so an exact match still scores highest.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "ter": ("expense", "ratio"),
    "expense": ("cost", "charge", "fee"),
    "ratio": ("expense",),
    "cost": ("expense", "charge", "fee"),
    "charge": ("expense", "cost", "fee"),
    "fee": ("expense", "cost", "charge"),
    "price": ("nav", "cost"),
    "lockin": ("lock", "locked"),
    "locked": ("lock", "lockin"),
    "sip": ("systematic", "investment", "monthly"),
    "swp": ("systematic", "withdrawal"),
    "stp": ("systematic", "transfer"),
    "nav": ("net", "asset", "value"),
    "elss": ("tax", "saver", "80c"),
    "80c": ("tax", "elss", "deduction"),
    "largecap": ("large", "cap"),
    "bluechip": ("large", "cap"),
    "midcap": ("mid", "cap"),
    "flexicap": ("flexi", "cap"),
    "lumpsum": ("lump", "sum"),
    "onetime": ("lump", "sum"),
    "redeem": ("withdraw", "exit", "redemption"),
    "redemption": ("redeem", "withdraw", "exit"),
    "withdraw": ("redeem", "exit", "redemption"),
    "withdrawal": ("redeem", "exit", "swp"),
    "exit": ("redeem", "load"),
    "penalty": ("load", "exit", "charge"),
    "risky": ("risk", "riskometer"),
    "riskometer": ("risk",),
    "benchmark": ("index",),
    "index": ("benchmark",),
    "amc": ("fund", "house"),
    "scheme": ("fund",),
    "minimum": ("least", "smallest"),
    "smallest": ("minimum",),
    "least": ("minimum",),
    "statement": ("cas", "capital", "gains"),
    "cas": ("statement", "consolidated"),
    "kyc": ("verification",),
    "ltcg": ("tax", "capital", "gains", "long", "term"),
    "stcg": ("tax", "capital", "gains", "short", "term"),
    "taxed": ("tax", "taxation"),
    "taxation": ("tax", "taxed"),
    "meaning": ("what", "explain", "definition"),
    "explain": ("what", "meaning", "definition"),
    "definition": ("what", "meaning", "explain"),
    "define": ("what", "meaning", "explain"),
}


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _singularise(token: str) -> str:
    """Very small plural rule. A real stemmer is not worth the false merges here."""
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase, strip accents and currency marks, split, drop stopwords, singularise."""
    normalised = _strip_accents(text.lower()).replace("₹", " rs ")
    tokens = _TOKEN_RE.findall(normalised)
    return [_singularise(t) for t in tokens if t not in STOPWORDS]


def expand(tokens: list[str]) -> list[str]:
    """Append synonym expansions. Used on the query side only."""
    expanded = list(tokens)
    for token in tokens:
        expanded.extend(SYNONYMS.get(token, ()))
    return expanded


def bigrams(tokens: list[str]) -> list[str]:
    """Adjacent token pairs, joined with '_' so they cannot collide with unigrams.

    Indexing these is what separates "capital gains" from "the capital of
    Mongolia": on unigrams alone both look like a match on a rare word, and the
    off-topic one scored well enough to be answered. Bigrams are built from the
    user's own tokens, never from synonym expansions, which would otherwise
    invent phrases nobody typed.
    """
    return [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
