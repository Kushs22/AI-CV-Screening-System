"""Text normalisation shared by the job-description parser and the matcher.

Matching is whole-word and line-based. Stemming and a small set of
equivalences catch different wording of the same requirement without
treating merely similar documents as a match.
"""

from __future__ import annotations

import re


STOPWORDS = frozenset(
    """
    a an the and or of to in on for with by from at as into over per via
    be is are was were been being this that these those we you they our your
    their who which what how when where while than then not no nor
    have has had
    such other any all can will should must may
    """.split()
)

# Tokens dropped after phrase aliases have been applied. They are filler
# around a real requirement ("communication skills", "strong Excel").
FILLER_TOKENS = frozenset(
    """
    skill skills ability abilities relevant strong excellent proven good
    solid effective confident clear high higher highly very well plus
    using use used include including able within across
    """.split()
)

_SPELLING = (
    (re.compile(r"\borganisations\b"), "organizations"),
    (re.compile(r"\borganisation\b"), "organization"),
    (re.compile(r"\borganisational\b"), "organizational"),
    (re.compile(r"\borganising\b"), "organizing"),
    (re.compile(r"\borganised\b"), "organized"),
    (re.compile(r"\borganise\b"), "organize"),
    (re.compile(r"\blicences\b"), "licenses"),
    (re.compile(r"\blicence\b"), "license"),
    (re.compile(r"\banalyse\b"), "analyze"),
    (re.compile(r"\banalysed\b"), "analyzed"),
    (re.compile(r"\bbehaviour\b"), "behavior"),
    (re.compile(r"\bfavoured\b"), "favored"),
    (re.compile(r"\bfavour\b"), "favor"),
)

# Equivalence groups. The first item is the canonical id.
# Longer surface forms are applied first so "microsoft excel" is not
# reduced to the single word "excel" too early, and "javascript" is never
# treated as "java".
ALIAS_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "communication",
        (
            "communication skills",
            "communications",
            "communication",
            "communicating",
            "communicated",
            "communicate",
            "liaising",
            "liaised",
            "liaison",
            "presentations",
            "presentation",
            "presenting",
            "presented",
        ),
    ),
    (
        "problem_solving",
        (
            "problem solving",
            "troubleshooting",
            "trouble shooting",
            "solving problems",
            "solved problems",
        ),
    ),
    (
        "attention_detail",
        (
            "attention to detail",
            "attention to details",
            "eye for detail",
        ),
    ),
    (
        "teamwork",
        (
            "worked with a team",
            "working with a team",
            "cross functional",
            "team player",
            "team work",
            "teamwork",
            "collaborating",
            "collaborated",
            "collaboration",
        ),
    ),
    (
        "time_management",
        (
            "time management",
            "meeting deadlines",
            "met deadlines",
            "meet deadlines",
            "deadlines",
        ),
    ),
    (
        "independent",
        (
            "working independently",
            "worked independently",
            "work independently",
            "without supervision",
            "self starter",
            "independently",
            "autonomous",
        ),
    ),
    (
        "documentation",
        (
            "record keeping",
            "documentation",
            "documenting",
            "documented",
        ),
    ),
    (
        "reports",
        (
            "report writing",
            "written reports",
            "writing reports",
            "wrote reports",
            "monthly reports",
            "reports",
            "report",
        ),
    ),
    (
        "digital_tools",
        (
            "digitally literate",
            "computer literate",
            "digital tools",
            "it literate",
        ),
    ),
    ("excel", ("microsoft excel", "ms excel", "excel")),
    ("word", ("microsoft word", "ms word")),
    ("powerpoint", ("ms powerpoint", "power point", "powerpoint")),
    ("outlook", ("ms outlook", "outlook")),
    ("spreadsheet", ("google sheets", "spreadsheets", "spreadsheet")),
    (
        "stakeholder",
        (
            "stakeholders",
            "stakeholder",
            "customers",
            "customer",
            "clients",
            "client",
            "guests",
            "guest",
        ),
    ),
    ("adaptable", ("adaptability", "adaptable", "flexible")),
    (
        "organised",
        (
            "organizational",
            "organizing",
            "organized",
        ),
    ),
    ("reliable", ("reliability", "dependable", "reliable")),
    (
        "learn_quickly",
        (
            "learn new systems quickly",
            "picked up new systems",
            "learned quickly",
            "learnt quickly",
            "learns quickly",
            "learn quickly",
            "quick to learn",
            "quick learner",
        ),
    ),
    ("javascript", ("java script", "javascript", "js")),
    ("typescript", ("typescript",)),
    ("kubernetes", ("kubernetes", "k8s")),
    ("registered_nurse", ("registered nurse", "rn")),
    (
        "customer_service",
        (
            "customer service",
            "client service",
            "guest service",
            "customer facing",
            "served customers",
            "serving customers",
            "served guests",
            "serving guests",
        ),
    ),
    (
        "questions",
        (
            "answering questions",
            "answered questions",
            "answer questions",
            "questions",
            "question",
            "queries",
            "query",
        ),
    ),
    (
        "concerns",
        (
            "addressing concerns",
            "addressed concerns",
            "concerns",
            "concern",
            "complaints",
            "complaint",
        ),
    ),
    (
        "cleanliness",
        (
            "cleanliness",
            "cleaning",
            "cleaned",
            "clean",
        ),
    ),
    (
        "hygiene",
        (
            "food hygiene",
            "hygienic",
            "hygiene",
        ),
    ),
    ("health_safety", ("health and safety",)),
    ("forklift", ("fork lift", "forklift", "flt")),
    ("project_management", ("project management",)),
    ("spring_boot", ("spring boot",)),
    ("power_bi", ("power bi", "powerbi")),
)

# A specific tool is evidence of the vague requirement "digital tools".
# The reverse is not true: "digital tools" is not evidence of Excel.
IMPLIED_BY: dict[str, tuple[str, ...]] = {
    "digital_tools": (
        "excel",
        "word",
        "powerpoint",
        "outlook",
        "spreadsheet",
        "power_bi",
    ),
}

_IMPLIED_PHRASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "digital_tools",
        ("google workspace", "microsoft 365", "salesforce", "sap", "slack"),
    ),
)

_SENTINEL = "qxq"


def _canon(name: str) -> str:
    return f"{_SENTINEL}{name}{_SENTINEL}"


def _alias_patterns() -> list[tuple[re.Pattern[str], str]]:
    phrases: list[tuple[str, str]] = []
    for canon, forms in ALIAS_GROUPS:
        for form in forms:
            phrases.append((form, _canon(canon)))
    phrases.sort(key=lambda item: len(item[0]), reverse=True)
    compiled = []
    for form, token in phrases:
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(form)}(?![a-z0-9])")
        compiled.append((pattern, token))
    return compiled


_ALIAS_PATTERNS = _alias_patterns()

_IMPLIED_COMPILED: list[tuple[str, re.Pattern[str]]] = []
for _canon_name, _forms in _IMPLIED_PHRASES:
    for _form in _forms:
        _IMPLIED_COMPILED.append(
            (
                _canon(_canon_name),
                re.compile(rf"(?<![a-z0-9]){re.escape(_form)}(?![a-z0-9])"),
            )
        )


def fold_spelling(text: str) -> str:
    for pattern, replacement in _SPELLING:
        text = pattern.sub(replacement, text)
    return text


def normalize_base(text: str) -> str:
    """Lowercase, fold spelling, and keep letters, numbers, and sentinels."""
    text = text.lower().replace("\u00a0", " ")
    text = fold_spelling(text)
    text = text.replace("&", " and ")
    text = text.replace("c++", f" {_canon('cplusplus')} ")
    text = text.replace("c#", f" {_canon('csharp')} ")
    text = re.sub(r"\breported to\b", " ", text)
    text = text.replace("-", " ").replace("/", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def stem(word: str) -> str:
    """Reduce a word to a stable stem.

    Two passes turn "managed" and "manage", or "requirements" and "required",
    into the same token. A stem that would become shorter than four letters
    is left as it was, so "going" never becomes "go".
    """
    if word.startswith(_SENTINEL) or len(word) <= 3:
        return word
    word = _strip_suffix(word)
    word = _strip_suffix(word)
    if len(word) >= 5 and word.endswith("e"):
        word = word[:-1]
    if (
        len(word) >= 4
        and word[-1] == word[-2]
        and word[-1] not in "aeiou"
    ):
        word = word[:-1]
    return word


def _strip_suffix(word: str) -> str:
    for suffix in ("ment", "ation", "ies", "ing", "ied", "ed", "es", "ly", "s"):
        if suffix == "s" and word.endswith("ss"):
            continue
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            if suffix == "ies":
                return word[: -len(suffix)] + "y"
            return word[: -len(suffix)]
    return word


def aliased_tokens(text: str, keep_joins: bool = False) -> list[str]:
    """Canonical tokens for one requirement or one CV line.

    ``and`` and ``or`` are kept only when a caller needs to see which words
    were joined. Matching itself ignores them.
    """
    base = normalize_base(text)
    for pattern, token in _ALIAS_PATTERNS:
        base = pattern.sub(f" {token} ", base)
    tokens: list[str] = []
    for raw in base.split():
        if raw.isdigit():
            continue
        if raw.startswith(_SENTINEL):
            tokens.append(raw)
            continue
        if raw in {"and", "or"} and keep_joins:
            tokens.append(raw)
            continue
        if raw in STOPWORDS or raw in FILLER_TOKENS:
            continue
        tokens.append(stem(raw))
    return tokens


def tokenize(text: str) -> list[str]:
    """Canonical tokens for one requirement or one CV line."""
    return aliased_tokens(text)


def and_pairs(text: str) -> list[tuple[str, str]]:
    """Content words joined by ``and``, in canonical form."""
    tokens = aliased_tokens(text, keep_joins=True)
    pairs: list[tuple[str, str]] = []
    for index, token in enumerate(tokens):
        if token != "and" or index == 0 or index + 1 >= len(tokens):
            continue
        left, right = tokens[index - 1], tokens[index + 1]
        if left in {"and", "or"} or right in {"and", "or"}:
            continue
        pairs.append((left, right))
    return pairs


def token_set(text: str) -> set[str]:
    return set(tokenize(text))


def expand_implications(text: str, tokens: set[str]) -> set[str]:
    """Add broad requirements that a specific tool or phrase can satisfy."""
    expanded = set(tokens)
    present_names = set()
    for name, _forms in ALIAS_GROUPS:
        if _canon(name) in tokens:
            present_names.add(name)
    for broad, specifics in IMPLIED_BY.items():
        if present_names.intersection(specifics):
            expanded.add(_canon(broad))
    base = normalize_base(text)
    for token, pattern in _IMPLIED_COMPILED:
        if pattern.search(base):
            expanded.add(token)
    return expanded


def is_sentinel(token: str) -> bool:
    return token.startswith(_SENTINEL)


def sentinel(name: str) -> str:
    return _canon(name)
