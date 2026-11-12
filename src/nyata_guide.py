"""Ask Nyata where to apply, and where to get local CV and job help.

The CV is never sent. These answers sit beside the ATS score and do not change it.
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


NYATA_ENDPOINT = "https://nyataai.co.uk/external_api.php"
NYATA_MODEL = "nyata-1"
REQUEST_TIMEOUT_SECONDS = 20


_NOT_A_CITY = {
    "my", "the", "a", "an", "this", "that", "your", "our", "any", "some",
    "jobs", "job", "work", "cv", "cvs", "general", "uk",
}
_CITY_PATTERN = re.compile(
    r"\b(?:in|near|around|at)\s+([A-Za-z][A-Za-z'’.-]*(?:\s+[A-Za-z][A-Za-z'’.-]*){0,2})",
    re.IGNORECASE,
)


def find_city(question: str) -> str:
    """Read a city from a question such as 'jobs in Bristol'. Empty when none is named."""
    match = _CITY_PATTERN.search(question or "")
    if not match:
        return ""
    kept: list[str] = []
    for word in match.group(1).strip(" .,!?").split():
        if word.lower().strip(".,!?") in _NOT_A_CITY:
            if not kept:
                continue
            break
        kept.append(word.strip(".,!?"))
    return " ".join(kept[:3])


def apply_links(city: str = "") -> list[dict[str, str]]:
    """Sites where a person can apply. A named city is added to the search."""
    place = (city or "").strip()
    if place:
        encoded = urllib.parse.quote_plus(place)
        slug = re.sub(r"[^a-z0-9]+", "-", place.lower()).strip("-")
        return [
            {"name": "Indeed", "url": f"https://www.indeed.co.uk/jobs?l={encoded}"},
            {"name": "LinkedIn", "url": f"https://www.linkedin.com/jobs/search?location={encoded}"},
            {"name": "Reed", "url": f"https://www.reed.co.uk/jobs/in-{slug}"},
            {"name": "GOV.UK Find a job", "url": "https://www.gov.uk/find-a-job"},
        ]
    return [
        {"name": "Indeed", "url": "https://www.indeed.co.uk/jobs"},
        {"name": "LinkedIn", "url": "https://www.linkedin.com/jobs"},
        {"name": "Reed", "url": "https://www.reed.co.uk/jobs"},
        {"name": "GOV.UK Find a job", "url": "https://www.gov.uk/find-a-job"},
    ]


def questions_for(question: str) -> list[tuple[str, str, str, str]]:
    asked = (question or "").strip() or "Where can I find jobs related to my CV?"
    city = find_city(asked)
    place = f" in {city}" if city else ""
    scope = f" in {city}" if city else " in general"
    return [
        (
            "where_to_apply",
            "Where to apply",
            f"{asked} List the job findings{scope}, and name the platforms where a person can apply.",
            city,
        ),
        (
            "local_help",
            "Local help with CVs and jobs",
            (
                f"Where can someone get help{place} with writing a CV and finding a job?"
                if city
                else "Where can someone get help with writing a CV and finding a job?"
            ),
            city,
        ),
    ]


def ask_both(api_key: str, question: str = "") -> list[dict[str, Any]]:
    answers = []
    for question_id, title, text, city in questions_for(question):
        item = ask(text, api_key=api_key, city=city, title=title, question_id=question_id)
        item["city"] = city
        item["links"] = apply_links(city) if question_id == "where_to_apply" else []
        answers.append(item)
    return answers


def ask(
    question: str,
    *,
    api_key: str,
    city: str = "",
    title: str = "",
    question_id: str = "",
) -> dict[str, Any]:
    base = {
        "id": question_id,
        "title": title or question,
        "question": question,
        "ok": False,
        "reply": "",
        "listings": [],
        "error": "",
    }
    key = (api_key or "").strip()
    if not key:
        base["error"] = "not_configured"
        return base

    body: dict[str, Any] = {
        "model": NYATA_MODEL,
        "messages": [{"role": "user", "content": question}],
        "max_tokens": 400,
        "temperature": 0.2,
    }
    place = (city or "").strip()
    if place:
        body["city"] = place

    request = urllib.request.Request(
        NYATA_ENDPOINT,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": key,
            "Accept": "application/json",
            "User-Agent": "AI-CV-Screening/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS, context=_ssl_context()) as response:
            raw = response.read().decode("utf-8", errors="replace")
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        base["error"] = f"http_{exc.code}"
        return base
    except Exception:  # noqa: BLE001
        base["error"] = "unavailable"
        return base

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        base["error"] = "invalid_json"
        return base
    if status != 200 or not isinstance(payload, dict):
        base["error"] = f"http_{status}"
        return base

    choices = payload.get("choices") or []
    reply = ""
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message") or {}
        reply = str(message.get("content") or "").strip()
    nyata = payload.get("nyata") if isinstance(payload.get("nyata"), dict) else {}
    results = [item for item in (nyata.get("results") or []) if isinstance(item, dict)]
    listings = [_listing(item) for item in _sort_listings(results)[:6]]
    if payload.get("sandbox") or _is_sample(reply):
        reply = ""
    listings = [
        item
        for item in listings
        if not _is_sample(item["name"]) and not _is_sample(item.get("organisation") or "")
    ]
    base["ok"] = True
    base["reply"] = reply
    base["listings"] = listings
    return base


def _is_sample(text: str) -> bool:
    lowered = (text or "").lower()
    return "sandbox" in lowered or "sample data" in lowered or "sample community" in lowered


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _sort_listings(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple[int, float, str]:
        open_now = 0 if item.get("open_now") is True else 1
        try:
            distance = float(item.get("distance_km") if item.get("distance_km") is not None else 9_999)
        except (TypeError, ValueError):
            distance = 9_999.0
        return (open_now, distance, str(item.get("name") or ""))

    return sorted(results, key=key)


def _listing(item: dict[str, Any]) -> dict[str, Any]:
    distance = item.get("distance_km")
    try:
        distance_km = float(distance) if distance is not None else None
    except (TypeError, ValueError):
        distance_km = None
    directions = str(item.get("directions_url") or "").strip()
    if not directions.startswith(("http://", "https://")):
        directions = ""
    return {
        "name": str(item.get("name") or "Local place"),
        "organisation": str(item.get("organisation") or "").strip(),
        "address": str(item.get("address") or "").strip(),
        "postcode": str(item.get("postcode") or "").strip(),
        "distance_km": distance_km,
        "directions_url": directions,
        "open_now": item.get("open_now") is True,
        "when": _when(item),
    }


def _when(item: dict[str, Any]) -> str:
    parts: list[str] = []
    day = str(item.get("day") or "").strip()
    start = str(item.get("start_time") or "").strip()
    end = str(item.get("end_time") or "").strip()
    if day:
        parts.append(day)
    if start and end:
        parts.append(f"{start}–{end}")
    elif start:
        parts.append(start)
    return " · ".join(parts)
