"""Nyata is asked two questions and is never given the CV."""

from __future__ import annotations

import json
from unittest.mock import patch
from urllib.request import Request

from src.nyata_guide import apply_links, ask, ask_both, find_city, questions_for


CV_TEXT = "Amira Khan, housing officer, amira.khan@example.com, Bristol Council."


def test_a_named_city_narrows_the_questions_and_the_apply_links():
    asked = "Where can I find jobs related to my CV in Bristol?"
    assert find_city(asked) == "Bristol"
    titles = [title for _id, title, _question, _city in questions_for(asked)]
    cities = [city for _id, _title, _question, city in questions_for(asked)]
    questions = [question for _id, _title, question, _city in questions_for(asked)]
    assert titles == ["Where to apply", "Local help with CVs and jobs"]
    assert cities == ["Bristol", "Bristol"]
    assert all("Bristol" in question for question in questions)
    assert CV_TEXT not in " ".join(questions)
    urls = [item["url"] for item in apply_links("Bristol")]
    assert "https://www.indeed.co.uk/jobs?l=Bristol" in urls
    assert "https://www.linkedin.com/jobs/search?location=Bristol" in urls


def test_a_question_without_a_city_stays_general():
    asked = "Where can I find jobs related to my CV?"
    assert find_city(asked) == ""
    cities = [city for _id, _title, _question, city in questions_for(asked)]
    assert cities == ["", ""]
    assert "in general" in questions_for(asked)[0][2]
    urls = [item["url"] for item in apply_links("")]
    assert "https://www.indeed.co.uk/jobs" in urls
    assert "https://www.linkedin.com/jobs" in urls


def test_missing_key_does_not_call_nyata_but_still_lists_platforms():
    with patch("src.nyata_guide.urllib.request.urlopen") as opener:
        answers = ask_both("", "Where can I find jobs related to my CV in Bristol?")
    opener.assert_not_called()
    assert [item["error"] for item in answers] == ["not_configured", "not_configured"]
    assert answers[0]["links"][0]["name"] == "Indeed"
    assert answers[1]["links"] == []


def test_sandbox_sample_text_is_left_out():
    payload = {
        "sandbox": True,
        "choices": [
            {
                "message": {
                    "content": (
                        "Sample Community Kitchen serves free hot meals. "
                        "(Sandbox: sample data only. Use a live key for real listings.)"
                    )
                }
            }
        ],
        "nyata": {
            "results": [
                {"name": "Sample Community Kitchen", "organisation": "Sample", "address": "1 Sample Street"}
            ]
        },
    }

    class _Response:
        status = 200

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with patch("src.nyata_guide.urllib.request.urlopen", return_value=_Response()):
        answer = ask("Where can I find jobs related to my CV?", api_key="test-key", title="Where to apply")
    assert answer["ok"] is True
    assert answer["reply"] == ""
    assert answer["listings"] == []


def test_request_sends_the_question_and_not_a_cv():
    payload = {
        "choices": [{"message": {"content": "Try Indeed and the campus careers desk."}}],
        "nyata": {
            "results": [
                {
                    "name": "Campus careers",
                    "organisation": "City College",
                    "address": "1 High Street",
                    "postcode": "BS1 1AA",
                    "distance_km": 0.8,
                    "open_now": True,
                    "directions_url": "https://maps.example/careers",
                }
            ]
        },
    }

    class _Response:
        status = 200

        def read(self) -> bytes:
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with patch("src.nyata_guide.urllib.request.urlopen", return_value=_Response()) as opener:
        answer = ask(
            "Where should a student apply for jobs in Bristol?",
            api_key="test-key",
            city="Bristol",
            title="Where to apply",
            question_id="where_to_apply",
        )

    sent: Request = opener.call_args.args[0]
    body = json.loads(sent.data.decode("utf-8"))
    assert body["messages"][0]["content"].startswith("Where should a student apply")
    assert CV_TEXT not in body["messages"][0]["content"]
    assert body["city"] == "Bristol"
    assert sent.get_header("X-api-key") == "test-key"
    assert answer["ok"] is True
    assert "Indeed" in answer["reply"]
    assert answer["listings"][0]["name"] == "Campus careers"
    assert answer["listings"][0]["directions_url"] == "https://maps.example/careers"
