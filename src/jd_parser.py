"""Turn any job description into separate requirements.

The job text is the source of the requirements. There is no fixed list of
skills, so the same parser works for nursing, software, trades, or office
roles. A requirement is something the CV can be checked against, not a
random two-word phrase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.textutil import tokenize


_PROTECT = (
    "health and safety",
    "health and social care",
    "research and development",
    "training and development",
    "sales and marketing",
    "monitoring and evaluation",
    "equality and diversity",
    "food and beverage",
    "pick and pack",
    "advice and guidance",
    "quality and compliance",
)

_PREFIXES = (
    r"^(we are|we're) looking for (a |an )?(candidate|person|individual) (with|who (has|is))\s+",
    r"^the ideal candidate (should be|will be|will have|has|is|should have)\s+",
    r"^the (successful )?candidate (should|will|must)( be| have)?\s+",
    r"^(the )?role requires\s+",
    r"^you will( be responsible for| be expected to| need to| be)?\s+",
    r"^(key )?responsibilit(?:y|ies)(?: include)?\s*[:\-]?\s*",
    r"^(essential|desirable|preferred|required)(?: requirements)?\s*[:\-]\s*",
    r"^(must have|need to have|you must have|you must)\s+",
    r"^(about you|what you.ll need|what you will need|requirements)\s*[:\-]?\s*",
    r"^(we need|we require)\s+(a |an )?",
)

_LEADING = (
    r"^(?:strong|excellent|proven|good|solid|relevant|effective|confident|clear)\s+",
    r"^(?:the\s+)?ability\s+to\s+",
    r"^able\s+to\s+",
    r"^experience\s+(?:in|with|of)\s+",
    r"^experience\s+",
    r"^understanding\s+",
    r"^preparing\s+",
    r"^using\s+",
    r"^contributing\s+to\s+",
    r"^knowledge\s+of\s+",
    r"^proficien(?:t|cy)\s+in\s+",
    r"^skilled\s+in\s+",
    r"^responsible\s+for\s+",
)

_PREFERRED_LINE = re.compile(
    r"^(desirable|preferred|nice to have|bonus|ideal|advantageous)\b",
    re.I,
)
_REQUIRED_LINE = re.compile(
    r"^(essential|required|must[- ]haves?|minimum requirements|what you.ll need|key requirements)\b",
    re.I,
)
_YEARS = re.compile(
    r"(\d+)\s*\+?\s*(?:years|yrs)\b(?:\s+of)?\s+(?:relevant\s+|professional\s+|work\s+)?experience",
    re.I,
)
_DEGREE = re.compile(
    r"\b(ph\.?d|dphil|doctorate|master'?s|msc|m\.sc|mba|meng|m\.?a\b|bachelor'?s|bsc|b\.sc|beng|b\.?a\b|degree|hnd|nvq|gcse|a[- ]levels?)\b",
    re.I,
)
_LEVELS: tuple[tuple[str, int, re.Pattern[str]], ...] = (
    ("doctorate", 5, re.compile(r"\b(?:ph\.?d|dphil|doctorate)\b", re.I)),
    ("masters", 4, re.compile(r"\b(?:master'?s|msc|m\.sc|mba|meng|m\.?a)\b", re.I)),
    ("bachelors", 3, re.compile(r"\b(?:bachelor'?s|bsc|b\.sc|beng|b\.?a|degree)\b", re.I)),
    ("school", 2, re.compile(r"\b(?:a[- ]levels?|hnd|nvq|gcse)\b", re.I)),
)


@dataclass
class Requirement:
    text: str
    priority: str
    kind: str = "skill"
    alternatives: list[tuple[str, ...]] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)
    years: int | None = None
    education_level: int | None = None
    education_level_name: str = ""
    education_field: tuple[str, ...] = ()


def parse_job_description(job_description: str) -> list[Requirement]:
    text = job_description.replace("\u00a0", " ").strip()
    text = _split_glued_headings(text)
    if not text:
        return []

    requirements: list[Requirement] = []
    years_match = _YEARS.search(text)
    if years_match:
        years = int(years_match.group(1))
        requirements.append(
            Requirement(
                text=f"At least {years} years of experience",
                priority="required",
                kind="years",
                years=years,
            )
        )

    mode = "required"
    seen: set[tuple[str, str, tuple]] = set()
    for sentence, sentence_mode in _sentences(text, mode):
        for part, alternatives in _explode(sentence):
            if not part:
                continue
            priority = _priority(sentence, sentence_mode)
            requirement = _build(part, alternatives, priority)
            if requirement is None:
                continue
            key = (
                requirement.priority,
                requirement.kind,
                tuple(sorted(map(tuple, (sorted(alt) for alt in requirement.alternatives))))
                if requirement.kind == "skill"
                else (requirement.kind, requirement.years, requirement.education_level, requirement.education_field),
            )
            if key in seen:
                continue
            seen.add(key)
            requirements.append(requirement)
    return requirements


_GLUED_HEADINGS = (
    "about the company",
    "about the organisation",
    "about the organization",
    "about the team",
    "about us",
    "what we offer",
    "what you will do",
    "what you'll do",
    "what you will need",
    "what you'll need",
    "it helps if you have",
    "who we are",
    "who you are",
    "how to apply",
    "the role",
    "your role",
    "key responsibilities",
    "person specification",
)

# Company description, pay, hours, and hiring policy are not CV content.
_NOT_A_CV_REQUIREMENT = re.compile(
    r"("
    r"\bwe(?:'re| are) (?:a|an|committed|dedicated|proud)\b"
    r"|\bwe (?:pride|offer|cannot|can't|do not|don't|provide|welcome)\b"
    r"|dedicated to delivering"
    r"|\bis a (?:growing|leading|global|dynamic)\b"
    r"|\b(?:part-time|full-time)\b.{0,40}\b(?:hours|role|position|contract|possible|available)\b"
    r"|competitive (?:salary|pay|package)|pension scheme"
    r"|visa sponsorship|sponsor (?:a )?visa|right to work"
    r"|equal opportunit"
    r")",
    re.I,
)

_SECTION_HEADINGS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "skip",
        re.compile(
            r"^(about us|about the (?:company|organisation|organization|team)|who we are|"
            r"our (?:story|mission|values)|what we offer|why (?:join|work)(?: with)? us|"
            r"benefits|perks|salary|how to apply|equal opportunities)$",
            re.I,
        ),
    ),
    (
        "preferred",
        re.compile(
            r"^(it helps if you have|desirable|nice to have|preferred|bonus)$",
            re.I,
        ),
    ),
    (
        "required",
        re.compile(
            r"^(what you will do|what you'll do|the role|your role|role|"
            r"key duties|duties|responsibilities|key responsibilities|"
            r"requirements|what you(?:'ll| will) need|who you are|about you|"
            r"essential|person specification|qualifications)$",
            re.I,
        ),
    ),
)


def _split_glued_headings(text: str) -> str:
    """Put a heading back on its own line when a PDF joins it to the next word."""
    for heading in sorted(_GLUED_HEADINGS, key=len, reverse=True):
        text = re.sub(
            rf"(?i)({re.escape(heading)})(?=[A-Za-z])",
            r"\1\n",
            text,
        )
    text = re.sub(r"(?i)(?<![A-Za-z])(role)(?=[A-Z])", r"\1\n", text)
    return text


def _section_heading(line: str) -> tuple[str, str] | None:
    candidate = line.strip(" :|-")
    for kind, pattern in _SECTION_HEADINGS:
        if pattern.match(candidate):
            return kind, ""
    return None


def _sentences(text: str, mode: str):
    opening_line = True
    section = mode
    for raw_line in text.splitlines():
        original = raw_line.strip()
        if not original:
            continue
        is_bullet = bool(re.match(r"^([-*•●]|\d+[.)])\s+", original))
        line = re.sub(r"^([-*•●]|\d+[.)])\s+", "", original)
        heading = _section_heading(line)
        if heading:
            section, line = heading
            if not line:
                continue
        if section == "skip" or _NOT_A_CV_REQUIREMENT.search(line):
            continue
        if ":" in line:
            head, rest = line.split(":", 1)
            head = head.strip()
            if len(head.split()) <= 6 and _PREFERRED_LINE.match(head):
                mode = "preferred"
                line = rest.strip()
            elif len(head.split()) <= 6 and _REQUIRED_LINE.match(head):
                mode = "required"
                line = rest.strip()
        else:
            if len(line.split()) <= 3 and _PREFERRED_LINE.match(line):
                mode = "preferred"
                continue
            if len(line.split()) <= 3 and _REQUIRED_LINE.match(line):
                mode = "required"
                continue
        if not line:
            continue
        if opening_line:
            opening_line = False
            if _is_job_title(line, is_bullet):
                continue
        pieces = re.split(r"(?<=[.!?])\s+", line)
        for piece in pieces:
            piece = piece.strip(" \t-•")
            if piece and not _NOT_A_CV_REQUIREMENT.search(piece):
                piece_mode = "preferred" if section == "preferred" else mode
                yield piece, _priority(piece, piece_mode)


def _is_job_title(line: str, is_bullet: bool) -> bool:
    """A short opening line is the job title, not a requirement."""
    if is_bullet or "," in line or len(line.split()) > 10:
        return False
    return (
        re.search(
            r"\b(experience|skills?|degree|must|required|proficient|ability|years|yrs)\b",
            line,
            re.I,
        )
        is None
    )


def _priority(sentence: str, mode: str) -> str:
    if re.search(
        r"\b(ideal candidate|nice to have|preferably|preferred|desirable|bonus|plus|advantageous)\b",
        sentence,
        re.I,
    ):
        return "preferred"
    if re.search(r"\b(essential|must have|required|you must)\b", sentence, re.I):
        return "required"
    return mode


def _explode(sentence: str) -> list[tuple[str, list[str]]]:
    cleaned = _strip_prefixes(sentence)
    cleaned = _YEARS.sub(" ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .;:")
    if not cleaned:
        return []
    protected, slots = _protect(cleaned)
    if _is_skill_list(protected):
        parts = re.split(r";|,", protected)
    else:
        parts = [protected]
    exploded: list[tuple[str, list[str]]] = []
    for part in parts:
        part = _restore(part, slots)
        part = _clean_part(part)
        if not _keep(part):
            continue
        alternatives = [_clean_part(item) for item in _split_or(part)]
        alternatives = [item for item in alternatives if _keep(item)]
        if not alternatives:
            continue
        exploded.append((part, alternatives))
    return exploded


def _strip_prefixes(text: str) -> str:
    changed = True
    while changed:
        changed = False
        for pattern in _PREFIXES:
            updated = re.sub(pattern, "", text, count=1, flags=re.I).strip()
            if updated != text:
                text = updated
                changed = True
    return text


def _clean_part(text: str) -> str:
    text = text.strip(" \t.;:-")
    changed = True
    while changed and text:
        changed = False
        for pattern in _LEADING:
            updated = re.sub(pattern, "", text, count=1, flags=re.I).strip()
            if updated != text:
                text = updated
                changed = True
        updated = re.sub(
            r"^(as well as|along with)\s+",
            "",
            text,
            count=1,
            flags=re.I,
        ).strip()
        if updated != text:
            text = updated
            changed = True
        updated = re.sub(
            r"^(and|or|with|the|in)\s+",
            "",
            text,
            count=1,
            flags=re.I,
        ).strip()
        if updated != text:
            text = updated
            changed = True
        updated = re.sub(
            r"\b(skills?|abilities|ability)\b$",
            "",
            text,
            count=1,
            flags=re.I,
        ).strip(" \t.;:-")
        if updated != text:
            text = updated
            changed = True
    return re.sub(r"\s+", " ", text).strip()


def _is_skill_list(text: str) -> bool:
    """Split a comma list of skills, and leave a prose duty as one item."""
    if text.count(";") >= 1:
        return True
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if len(parts) < 3:
        return False
    short = [part for part in parts if len(part.split()) <= 8]
    return len(short) >= len(parts) - 1


def _split_or(part: str) -> list[str]:
    if len(re.findall(r"\bor\b", part, flags=re.I)) != 1:
        return [part]
    left, right = re.split(r"\bor\b", part, maxsplit=1, flags=re.I)
    left, right = left.strip(), right.strip()
    # "concerns or issues in a long duty" is one requirement.
    # "client or stakeholder requirements" is two parallel alternatives.
    if len(left.split()) > 4 or len(right.split()) > 4:
        return [part]
    left_words, right_words = left.split(), right.split()
    if len(left_words) == 1 and len(right_words) >= 2:
        left = f"{left} {right_words[-1]}"
    elif len(right_words) == 1 and len(left_words) >= 2:
        shared = left_words[0]
        if shared.lower() not in {"a", "an", "the"}:
            right = f"{shared} {right}"
    return [left.strip(), right.strip()]


def _protect(text: str) -> tuple[str, dict[str, str]]:
    slots: dict[str, str] = {}
    for index, phrase in enumerate(_PROTECT):
        token = f"qxqprotect{index}qxq"
        pattern = re.compile(re.escape(phrase), re.I)
        if pattern.search(text):
            text = pattern.sub(token, text)
            slots[token] = phrase
    return text, slots


def _restore(text: str, slots: dict[str, str]) -> str:
    for token, phrase in slots.items():
        text = text.replace(token, phrase)
    return text


def _keep(text: str) -> bool:
    if not text or not re.search(r"[A-Za-z+#]", text):
        return False
    if _NOT_A_CV_REQUIREMENT.search(text) or _section_heading(text):
        return False
    if tokenize(text):
        return True
    return bool(re.search(r"\b(c\+\+|c#|r|go|ai|ml|ui|ux|sql|js|rn)\b", text, re.I))


def _build(display: str, alternatives: list[str], priority: str) -> Requirement | None:
    if (
        _DEGREE.search(display)
        and not re.search(r"\bdegree of\b", display, re.I)
        and len(display.split()) <= 12
    ):
        level_name, level = _education_level(display)
        field_tokens = _education_field(display)
        return Requirement(
            text=display,
            priority=priority,
            kind="education",
            education_level=level,
            education_level_name=level_name,
            education_field=tuple(field_tokens),
        )

    token_sets = []
    phrases = []
    for alternative in alternatives:
        tokens = tuple(dict.fromkeys(tokenize(alternative)))
        if tokens:
            token_sets.append(tokens)
            phrases.append(alternative)
    if not token_sets:
        return None
    # Prefer the richer wording when every alternative collapsed together.
    return Requirement(
        text=display,
        priority=priority,
        kind="skill",
        alternatives=token_sets,
        phrases=phrases,
    )


def _education_level(text: str) -> tuple[str, int]:
    for name, level, pattern in _LEVELS:
        if pattern.search(text):
            return name, level
    return "unspecified", 1


def _education_field(text: str) -> list[str]:
    match = re.search(
        r"\b(?:in|of)\s+([a-z][a-z\s/&-]{2,60})",
        text,
        re.I,
    )
    if not match:
        return []
    field = re.split(
        r"\b(?:or equivalent|or related|preferred|required)\b",
        match.group(1),
        maxsplit=1,
        flags=re.I,
    )[0]
    return tokenize(field)
