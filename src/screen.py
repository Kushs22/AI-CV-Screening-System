"""Public screening entry points."""

from __future__ import annotations

import sys

from src.jd_parser import parse_job_description
from src.matcher import ScreenResult, assess, build_profile, summarise
from src.resume_parser import extract_text


MIN_CV_CHARS = 80


def screen_text(cv_text: str, job_description: str) -> ScreenResult:
    profile = build_profile(cv_text or "")
    readable = len((cv_text or "").strip()) >= MIN_CV_CHARS and profile.word_count >= 20
    requirements = parse_job_description(job_description or "")
    results = assess(requirements, profile) if readable else []
    return summarise(results, profile, readable)


def screen_file(file_path: str, job_description: str) -> ScreenResult:
    text = extract_text(file_path)
    return screen_text(text, job_description)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if len(argv) != 3:
        print(
            "Usage: python -m src.screen <cv.pdf|docx|txt> <job.txt>",
            file=sys.stderr,
        )
        return 2
    job_description = open(argv[2], encoding="utf-8").read()
    result = screen_file(argv[1], job_description)
    _print_result(result)
    return 0


def _print_result(result: ScreenResult) -> None:
    print(f"Verdict: {result.verdict}")
    print(f"Job fit: {result.fit_score}%")
    print(
        f"Required: {result.required_met}/{result.required_total}"
        f" ({result.required_coverage}%)"
    )
    if result.required_unverified:
        print(f"Unverified required items: {result.required_unverified}")
    if result.preferred_total:
        print(
            f"Preferred: {result.preferred_met}/{result.preferred_total}"
            f" ({result.preferred_coverage}%)"
        )
    print()
    print(result.summary)
    print()
    for item in result.results:
        evidence = f" — {item.evidence}" if item.evidence else ""
        print(f"[{item.status}] ({item.priority}) {item.text}")
        print(f"    {item.match_type}{evidence}")


if __name__ == "__main__":
    raise SystemExit(main())
