"""Match each job requirement to a line in the CV.

A hit has to happen inside one line or bullet. Words taken from different
parts of the CV are not combined, which is what kept the old phrase overlap
imprecise. Years and qualifications are checked on their own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from src.jd_parser import Requirement
from src.textutil import and_pairs, expand_implications, is_sentinel, normalize_base, sentinel, tokenize


_HEADINGS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "experience",
        re.compile(
            r"^(work experience|professional experience|employment history|work history|career history|employment|experience)$",
            re.I,
        ),
    ),
    (
        "education",
        re.compile(r"^(education|qualifications|academic qualifications|academic background)$", re.I),
    ),
    (
        "skills",
        re.compile(
            r"^(skills|technical skills|core skills|key skills|core competencies|competencies|expertise|it skills|tools)$",
            re.I,
        ),
    ),
    (
        "summary",
        re.compile(
            r"^(summary|professional summary|profile|personal profile|personal statement|objective|about me)$",
            re.I,
        ),
    ),
    (
        "certifications",
        re.compile(r"^(certifications?|certificates|licen[cs]es|training)$", re.I),
    ),
    ("projects", re.compile(r"^(projects|personal projects|selected projects)$", re.I)),
    ("volunteer", re.compile(r"^(volunteering|volunteer experience|voluntary work)$", re.I)),
)

_DEMONSTRATED = {"experience", "projects", "volunteer", "summary"}
_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
_RANGE = re.compile(
    r"(?:(?P<smon>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+)?"
    r"(?P<syear>(?:19|20)\d{2})"
    r"\s*(?:-|–|—|\bto\b)\s*"
    r"(?:(?P<emon>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\.?\s+)?"
    r"(?P<eyear>(?:19|20)\d{2}|present|current|now|ongoing)",
    re.I,
)
_NUMERIC_RANGE = re.compile(
    r"\b(?P<smon>0?[1-9]|1[0-2])\s*/\s*(?P<syear>(?:19|20)\d{2})"
    r"\s*(?:-|–|—|to)\s*"
    r"(?P<emon>0?[1-9]|1[0-2])\s*/\s*(?P<eyear>(?:19|20)\d{2}|present|current|now)",
    re.I,
)
_DEGREE_PATTERNS: tuple[tuple[int, re.Pattern[str]], ...] = (
    (5, re.compile(r"\b(?:ph\.?d|dphil|doctorate)\b", re.I)),
    (4, re.compile(r"\b(?:master'?s|msc|m\.sc|mba|meng|m\.?a)\b", re.I)),
    (3, re.compile(r"\b(?:bachelor'?s|bsc|b\.sc|beng|b\.?a|degree)\b", re.I)),
    (2, re.compile(r"\b(?:a[- ]levels?|hnd|nvq|gcse)\b", re.I)),
)
_AMBIGUOUS = {
    "go": sentinel("go"),
    "r": sentinel("r"),
    "c": sentinel("c"),
}
_CODE_CONTEXT = re.compile(
    r"\b(programming|developer|language|software|engineer|engineering|coding|backend|framework|golang)\b",
    re.I,
)
# Duty wording that does not identify the requirement. Dropped only when a
# real requirement remains, so "health and safety regulations" is checked as
# health and safety, while a one-word requirement is left as it is.
_GENERIC = frozenset(
    """
    ensur provid maintain addres creat support contribut every point specific
    establish environ adherenc regul comp location manner flow journey servic
    need work includ follow standard area mak tak giv help high wide posit
    direct clear good great efficient effectiv throughout
    """.split()
)
# "friendly and professional" describes manner. Missing it does not wipe out
# the duty. "food and beverages" or "kitchen and dining" does.
_MODIFIERS = frozenset(
    """
    friend professional inclusiv safe warm smooth open polit calm
    """.split()
)


@dataclass
class Span:
    text: str
    section: str
    demonstrated: bool


@dataclass
class CvProfile:
    text: str
    spans: list[Span]
    sections: list[str]
    email: str = ""
    phone: str = ""
    years_experience: float | None = None
    education_level: int = 0
    word_count: int = 0


@dataclass
class RequirementResult:
    text: str
    priority: str
    kind: str
    status: str
    strength: float
    match_type: str
    evidence: str
    section: str
    advice: str = ""


@dataclass
class ScreenResult:
    fit_score: float
    required_met: int
    required_total: int
    required_unverified: int
    preferred_met: int
    preferred_total: int
    verdict: str
    summary: str
    results: list[RequirementResult] = field(default_factory=list)
    profile: CvProfile | None = None
    readable: bool = True

    @property
    def required_coverage(self) -> float:
        if self.required_total == 0:
            return 0.0
        return round(100 * self.required_met / self.required_total, 1)

    @property
    def preferred_coverage(self) -> float | None:
        if self.preferred_total == 0:
            return None
        return round(100 * self.preferred_met / self.preferred_total, 1)


def build_profile(cv_text: str, today: tuple[int, int] | None = None) -> CvProfile:
    text = cv_text or ""
    labelled = _label_lines(text)
    sections = []
    for _line, section in labelled:
        if section not in sections and section != "other":
            sections.append(section)
    has_experience = "experience" in sections
    spans: list[Span] = []
    for line, section in labelled:
        demonstrated = section in _DEMONSTRATED or (
            section == "other" and not has_experience
        )
        pieces = _split_skill_line(line) if section == "skills" else [line]
        for piece in pieces:
            spans.append(Span(piece, section, demonstrated))

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    phone_match = re.search(
        r"(?:(?:\+|00)\d{1,3}[\s-]?)?(?:\(?\d{2,5}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}",
        text,
    )
    date_lines = [
        line
        for line, section in labelled
        if section == "experience" or (section == "other" and not has_experience)
    ]
    return CvProfile(
        text=text,
        spans=spans,
        sections=sections,
        email=email_match.group(0) if email_match else "",
        phone=phone_match.group(0) if phone_match else "",
        years_experience=_years_from_lines(date_lines, today),
        education_level=_highest_degree(text),
        word_count=len(text.split()),
    )


def assess(requirements: list[Requirement], profile: CvProfile) -> list[RequirementResult]:
    results = []
    for requirement in requirements:
        results.append(_assess_one(requirement, profile))
    return results


def summarise(results: list[RequirementResult], profile: CvProfile, readable: bool) -> ScreenResult:
    if not readable:
        return ScreenResult(
            fit_score=0.0,
            required_met=0,
            required_total=0,
            required_unverified=0,
            preferred_met=0,
            preferred_total=0,
            verdict="Could not read this CV",
            summary=(
                "The file did not contain enough text to score. "
                "Image-only scans and empty files cannot be matched honestly. "
                "Export a text-based PDF or a DOCX and try again."
            ),
            results=[],
            profile=profile,
            readable=False,
        )
    if not results:
        return ScreenResult(
            fit_score=0.0,
            required_met=0,
            required_total=0,
            required_unverified=0,
            preferred_met=0,
            preferred_total=0,
            verdict="No requirements found",
            summary="The job description did not contain requirements that can be checked against a CV.",
            results=[],
            profile=profile,
            readable=True,
        )

    scored = [item for item in results if item.status != "unverified"]
    weight_total = 0.0
    weight_score = 0.0
    for item in scored:
        weight = 1.0 if item.priority == "required" else 0.45
        weight_total += weight
        weight_score += weight * item.strength
    fit = round(100 * weight_score / weight_total, 1) if weight_total else 0.0

    required = [item for item in results if item.priority == "required"]
    preferred = [item for item in results if item.priority == "preferred"]
    unverified = [item for item in required if item.status == "unverified"]
    decided_required = [item for item in required if item.status != "unverified"]
    required_met = [item for item in decided_required if item.status == "met"]
    preferred_met = [item for item in preferred if item.status == "met"]
    listed_only = [
        item.text
        for item in required_met
        if item.section in {"skills", "certifications", "education"}
    ]

    coverage = (len(required_met) / len(decided_required)) if decided_required else 0.0
    verdict = _verdict(coverage, fit, required_met, profile, decided_required, unverified)

    if decided_required:
        parts = [
            f"ATS score {fit}%. {len(required_met)} of {len(decided_required)} required skills are supported by the CV."
        ]
    elif unverified:
        parts = ["The required items could not be verified from the CV text."]
    else:
        parts = ["This job description has no required items, only preferences."]
    gaps = [
        item
        for item in required
        if item.status in {"missing", "partial", "unverified"} and item.advice
    ]
    if gaps:
        parts.append("What is missing, and what to add:")
        for item in gaps:
            parts.append(f"{item.text} — {item.advice}")
    elif listed_only:
        parts.append(
            "These are only in a list, so describe them in a role: "
            + "; ".join(listed_only[:4])
            + "."
        )
    parts.append(
        "A requirement is met only when one line of the CV shows it. "
        "This is an evidence score for shortlisting, not a hiring decision."
    )
    return ScreenResult(
        fit_score=fit,
        required_met=len(required_met),
        required_total=len(decided_required),
        required_unverified=len(unverified),
        preferred_met=len(preferred_met),
        preferred_total=len(preferred),
        verdict=verdict,
        summary=" ".join(parts),
        results=results,
        profile=profile,
        readable=True,
    )


def _verdict(
    coverage: float,
    fit: float,
    required_met: list[RequirementResult],
    profile: CvProfile,
    decided_required: list[RequirementResult],
    unverified: list[RequirementResult],
) -> str:
    if not decided_required and unverified:
        return "Could not verify"
    skill_hits = [item for item in required_met if item.kind == "skill"]
    demonstrated = [item for item in skill_hits if item.section in _DEMONSTRATED]
    # A heading-based CV must show requirements in experience, not only in a list.
    # A CV with no headings is scored from its sentences and can still be strong.
    strong_blocked = False
    if profile.sections and skill_hits:
        if len(demonstrated) < max(1, len(skill_hits) / 2):
            strong_blocked = True
    if coverage >= 0.8 and fit >= 70 and not strong_blocked:
        return "Strong match"
    if coverage >= 0.6 and fit >= 55:
        return "Good match"
    if coverage >= 0.35 or fit >= 40:
        return "Partial match"
    return "Weak match"


def _assess_one(requirement: Requirement, profile: CvProfile) -> RequirementResult:
    if requirement.kind == "years":
        return _assess_years(requirement, profile)
    if requirement.kind == "education":
        return _assess_education(requirement, profile)
    return _assess_skill(requirement, profile)


def _assess_skill(requirement: Requirement, profile: CvProfile) -> RequirementResult:
    best_strength = 0.0
    best_span: Span | None = None
    best_ratio = 0.0
    alternatives = _prepare_alternatives(requirement)
    for span in profile.spans:
        span_tokens = expand_implications(span.text, set(tokenize(span.text)))
        span_tokens = _apply_ambiguous(span, span_tokens)
        for phrase, alternative in alternatives:
            ratio = _overlap(alternative, span_tokens, and_pairs(phrase))
            if ratio <= 0:
                continue
            strength = _strength(ratio, span.demonstrated)
            if strength > best_strength:
                best_strength = strength
                best_span = span
                best_ratio = ratio
    if best_span is None or best_strength <= 0:
        return RequirementResult(
            text=requirement.text,
            priority=requirement.priority,
            kind=requirement.kind,
            status="missing",
            strength=0.0,
            match_type="Not found",
            evidence="",
            section="",
            advice=f"Not in the CV. Add a line that shows: {requirement.text}.",
        )
    status = "met" if best_strength >= 0.85 else "partial"
    evidence = best_span.text.strip()[:280]
    return RequirementResult(
        text=requirement.text,
        priority=requirement.priority,
        kind=requirement.kind,
        status=status,
        strength=round(best_strength, 2),
        match_type=_wording(requirement.text, best_span.text, best_ratio >= 0.999),
        evidence=evidence,
        section=best_span.section,
        advice=_advice(requirement.text, status, evidence, best_span.section),
    )


def _prepare_alternatives(requirement: Requirement) -> list[tuple[str, set[str]]]:
    phrases = requirement.phrases or [requirement.text] * len(requirement.alternatives)
    if len(phrases) != len(requirement.alternatives):
        phrases = [requirement.text] * len(requirement.alternatives)
    prepared = []
    for phrase, alternative in zip(phrases, requirement.alternatives):
        tokens = set(alternative)
        if tokens == {"go"}:
            tokens = {sentinel("go")}
        elif tokens == {"r"}:
            tokens = {sentinel("r")}
        elif tokens == {"c"}:
            tokens = {sentinel("c")}
        prepared.append((phrase, tokens))
    return prepared


def _apply_ambiguous(span: Span, tokens: set[str]) -> set[str]:
    raw = normalize_base(span.text)
    updated = set(tokens)
    for bare, token in _AMBIGUOUS.items():
        if bare in updated:
            updated.remove(bare)
        if re.search(rf"(?<![a-z0-9]){bare}(?![a-z0-9])", raw):
            allowed = span.section == "skills" or _CODE_CONTEXT.search(span.text)
            if bare == "go" and re.search(r"\bgolang\b|\bgo language\b", raw, re.I):
                allowed = True
            if allowed:
                updated.add(token)
    if re.search(r"\bgolang\b", raw, re.I):
        updated.add(sentinel("go"))
    return updated


def _overlap(required: set[str], found: set[str], pairs: list[tuple[str, str]] | None = None) -> float:
    content = _content_tokens(required)
    if not content:
        return 0.0
    found_content = {token for token in found if token not in _GENERIC} or set(found)
    if content <= found_content or content <= found:
        ratio = 1.0
    else:
        shared = len(content & found_content)
        ratio = shared / len(content)
        if len(content) <= 2:
            return 0.0
        if len(content) == 3 and not (shared >= 2 and ratio >= 0.67):
            return 0.0
        if len(content) >= 4 and not (shared >= 2 and ratio >= 0.28):
            return 0.0
    return _cap_missing_pairs(pairs or [], found, ratio)


def _content_tokens(required: set[str]) -> set[str]:
    """Drop duty filler when a specific requirement is still left."""
    content = {token for token in required if token not in _GENERIC}
    if len(content) >= 2:
        return content
    if len(content) == 1 and is_sentinel(next(iter(content))) and len(required) >= 3:
        return content
    return set(required)


def _cap_missing_pairs(pairs: list[tuple[str, str]], found: set[str], ratio: float) -> float:
    """A missing noun pair such as food and beverages limits the score."""
    for left, right in pairs:
        if left in _GENERIC or right in _GENERIC:
            continue
        if left in _MODIFIERS and right in _MODIFIERS:
            continue
        if left in found and right in found:
            continue
        ratio = min(ratio, 0.4)
    return ratio


def _strength(ratio: float, demonstrated: bool) -> float:
    if ratio >= 0.999:
        return 1.0 if demonstrated else 0.9
    if demonstrated:
        return ratio
    return ratio * 0.9


_JOINERS = {"and", "or", "of", "for", "with", "to", "in", "on"}
_LEVEL_WORD = re.compile(
    r"^(ph\.?d|dphil|doctorate|masters?|master'?s|msc|m\.sc|mba|meng|m\.?a|bachelors?|bachelor'?s|bsc|b\.sc|beng|b\.?a|degree|hnd|nvq|gcse|a[- ]levels?)$",
    re.I,
)


def _advice(text: str, status: str, evidence: str, section: str) -> str:
    if status == "met" and section in {"skills", "certifications"}:
        return "Only listed, not shown in a role. Add a bullet under experience that describes this."
    if status == "met":
        return ""
    if status == "missing" or not evidence:
        return f"Not in the CV. Add a line that shows: {text}."
    missing = _missing_surface(text, evidence)
    if missing:
        return f"Still missing: {missing}. Add a line that shows: {missing}."
    return f"Only partly shown. Add a line that shows: {text}."


def _missing_surface(text: str, evidence: str) -> str:
    evidence_tokens = expand_implications(evidence, set(tokenize(evidence)))
    words = text.replace("–", " ").replace("—", " ").replace("/", " ").split()
    keep: list[bool] = []
    for word in words:
        cleaned = word.strip(".,;:()[]")
        tokens = [token for token in tokenize(cleaned) if token not in _GENERIC]
        keep.append(bool(tokens) and any(token not in evidence_tokens for token in tokens))
    chosen: list[str] = []
    for index, word in enumerate(words):
        bare = word.strip(".,;:()[]")
        if not bare:
            continue
        if keep[index]:
            chosen.append(bare)
        elif bare.lower() in _JOINERS and _between_kept(keep, index):
            chosen.append(bare.lower())
    while chosen and chosen[0].lower() in _JOINERS:
        chosen.pop(0)
    while chosen and chosen[-1].lower() in _JOINERS:
        chosen.pop()
    return " ".join(chosen)


def _between_kept(keep: list[bool], index: int) -> bool:
    return any(keep[max(0, index - 4) : index]) and any(keep[index + 1 : index + 5])


def _wording(requirement: str, evidence: str, full: bool) -> str:
    required = normalize_base(requirement)
    evidence_norm = normalize_base(evidence)
    if required and required in evidence_norm:
        return "Same wording"
    if full:
        return "Equivalent wording"
    return "Partial overlap"


def _assess_years(requirement: Requirement, profile: CvProfile) -> RequirementResult:
    needed = requirement.years or 0
    found = profile.years_experience
    if found is None:
        return RequirementResult(
            text=requirement.text,
            priority=requirement.priority,
            kind="years",
            status="unverified",
            strength=0.0,
            match_type="Dates not found",
            evidence="No readable employment dates, so years of experience were not scored.",
            section="experience",
            advice="No employment dates were read. Add a start and end date for each role.",
        )
    met = found + 0.25 >= needed
    return RequirementResult(
        text=requirement.text,
        priority=requirement.priority,
        kind="years",
        status="met" if met else "missing",
        strength=1.0 if met else 0.0,
        match_type="Years found",
        evidence=f"About {found:.1f} years read from employment dates.",
        section="experience",
        advice=""
        if met
        else (
            f"Dates show about {found:.1f} years. The job asks for {needed}. "
            "Add earlier roles with dates if that experience exists."
        ),
    )


def _assess_education(requirement: Requirement, profile: CvProfile) -> RequirementResult:
    level_ok = profile.education_level >= (requirement.education_level or 1)
    blob_tokens: set[str] = set()
    for span in profile.spans:
        if span.section in {"education", "certifications", "other"}:
            blob_tokens |= set(tokenize(span.text))
    field_ok = True
    if requirement.education_field:
        field_ok = set(requirement.education_field) <= blob_tokens
    subject = _subject_tokens(requirement.text)
    if subject and not subject <= blob_tokens:
        field_ok = False
    if level_ok and field_ok:
        status, strength, match_type = "met", 1.0, "Qualification"
    else:
        status, strength, match_type = "missing", 0.0, "Not found"
    quote = ""
    for span in profile.spans:
        if any(pattern.search(span.text) for _level, pattern in _DEGREE_PATTERNS):
            quote = span.text.strip()[:280]
            break
    if requirement.education_field and level_ok and not field_ok:
        quote = (quote + " " if quote else "") + "The qualification is in a different subject."
    if not quote:
        quote = f"Highest qualification level read from the CV: {profile.education_level or 'none'}."
    if status == "met":
        advice = ""
    elif requirement.education_field and level_ok and not field_ok:
        advice = (
            f"The qualification is in a different subject. "
            f"Add this if you hold it: {requirement.text}."
        )
    else:
        advice = f"Not in the CV. Add this qualification if you hold it: {requirement.text}."
    return RequirementResult(
        text=requirement.text,
        priority=requirement.priority,
        kind="education",
        status=status,
        strength=strength,
        match_type=match_type,
        evidence=quote,
        section="education",
        advice=advice,
    )


def _subject_tokens(text: str) -> set[str]:
    """Words that name the subject, once the degree level itself is removed."""
    tokens: set[str] = set()
    for word in re.findall(r"[A-Za-z0-9+#.]+", text):
        if _LEVEL_WORD.match(word):
            continue
        for token in tokenize(word):
            if token not in _GENERIC and len(token) > 1:
                tokens.add(token)
    return tokens


def _label_lines(text: str) -> list[tuple[str, str]]:
    section = "other"
    labelled: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading, remainder = _heading(line)
        if heading:
            section = heading
            if remainder:
                labelled.append((remainder, section))
            continue
        labelled.append((line, section))
    return labelled


def _heading(line: str) -> tuple[str | None, str]:
    if ":" in line:
        head, rest = line.split(":", 1)
        name = _match_heading(head.strip())
        if name:
            return name, rest.strip()
    name = _match_heading(line.strip(" :|-").strip())
    if name:
        return name, ""
    return None, ""


def _match_heading(candidate: str) -> str | None:
    if not candidate or len(candidate) > 40 or len(candidate.split()) > 4:
        return None
    if candidate.endswith("."):
        return None
    for name, pattern in _HEADINGS:
        if pattern.match(candidate):
            return name
    return None


def _split_skill_line(line: str) -> list[str]:
    if line.count(",") < 1 and " | " not in line and ";" not in line:
        return [line]
    parts = re.split(r",|;|\|", line)
    pieces = [line]
    for part in parts:
        part = part.strip(" -")
        if part and part != line:
            pieces.append(part)
    return pieces


def _highest_degree(text: str) -> int:
    level = 0
    for value, pattern in _DEGREE_PATTERNS:
        if pattern.search(text):
            level = max(level, value)
    return level


def _years_from_lines(lines: list[str], today: tuple[int, int] | None) -> float | None:
    if today is None:
        from datetime import date

        current = date.today()
        today = (current.year, current.month)
    end_cap = today[0] * 12 + today[1]
    intervals: list[tuple[int, int]] = []
    blob = "\n".join(lines)
    for pattern in (_RANGE, _NUMERIC_RANGE):
        for match in pattern.finditer(blob):
            start = _month_index(match.group("syear"), match.group("smon"), default_month=1)
            end_token = match.group("eyear")
            if end_token and end_token.lower() in {"present", "current", "now", "ongoing"}:
                end = end_cap
            else:
                end = _month_index(end_token, match.group("emon"), default_month=12)
            if start is None or end is None or end < start:
                continue
            intervals.append((start, min(end, end_cap)))
    if not intervals:
        return None
    intervals.sort()
    merged: list[list[int]] = [[intervals[0][0], intervals[0][1]]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    months = sum(end - start for start, end in merged)
    return round(months / 12, 1)


def _month_index(year: str | None, month: str | None, default_month: int) -> int | None:
    if not year or not year.isdigit():
        return None
    if month and month.isdigit():
        month_number = int(month)
    elif month:
        month_number = _MONTHS.get(month.lower().rstrip("."), default_month)
    else:
        month_number = default_month
    return int(year) * 12 + month_number
