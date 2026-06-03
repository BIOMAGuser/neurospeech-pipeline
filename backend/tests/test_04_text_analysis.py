"""Text analysis pipeline tests (no audio, no Whisper — tests GPT + NLP only).
These tests call /analyze_text which skips Whisper and goes straight to analysis.
Veggie and Saying require a valid OpenAI key (GPT scoring).
Picture is NLP-only and always works.
"""
from pathlib import Path

import pytest
import requests
from helpers import auth_headers

FIXTURES = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8").strip()


def _has_valid_openai_key(base_url, token):
    """Check if the OpenAI key is valid by hitting /openai-status."""
    resp = requests.get(
        f"{base_url}/openai-status",
        headers=auth_headers(token),
    )
    return resp.json().get("status") == "ok"


def test_analyze_text_veggie(base_url, admin_token):
    transcript = _read_fixture("veggie_answer.txt")
    resp = requests.post(
        f"{base_url}/analyze_text",
        headers={**auth_headers(admin_token), "Content-Type": "application/json"},
        json={
            "transcript": transcript,
            "taskType": "veggie",
            "attemptId": "test_veggie_001",
        },
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert data["task"] == "veggie"
    assert data["attemptId"] == "test_veggie_001"
    assert "transcript" in data
    assert "metrics" in data

    m = data["metrics"]
    assert "points" in m
    assert "correct_words" in m
    assert "total_word_count" in m

    if m["points"] == 0 and not _has_valid_openai_key(base_url, admin_token):
        pytest.skip("GPT returned 0 — OpenAI key is placeholder/invalid")

    assert m["points"] > 0, f"Expected vegetables found, got points={m['points']}"
    assert len(m["correct_words"]) > 0
    print(f"\n  VEGGIE: {m['points']} Gemuese erkannt: {m['correct_words']}")


def test_analyze_text_saying(base_url, admin_token):
    transcript = _read_fixture("saying_answer.txt")
    resp = requests.post(
        f"{base_url}/analyze_text",
        headers={**auth_headers(admin_token), "Content-Type": "application/json"},
        json={
            "transcript": transcript,
            "taskType": "saying",
            "attemptId": "test_saying_001",
        },
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert data["task"] == "saying"
    m = data["metrics"]
    assert "points" in m
    assert "filler_word_count" in m
    assert "total_word_count" in m

    if m["points"] == 0 and not _has_valid_openai_key(base_url, admin_token):
        pytest.skip("GPT returned 0 — OpenAI key is placeholder/invalid")

    assert m["points"] == 1, f"Expected score=1 for correct answer, got {m['points']}"
    print(f"\n  SAYING: points={m['points']}, fillers={m['filler_word_count']}")


def test_analyze_text_picture(base_url, admin_token):
    """Picture analysis uses NLP only — always works regardless of OpenAI key."""
    transcript = _read_fixture("picture_answer.txt")
    resp = requests.post(
        f"{base_url}/analyze_text",
        headers={**auth_headers(admin_token), "Content-Type": "application/json"},
        json={
            "transcript": transcript,
            "taskType": "picture",
            "attemptId": "test_picture_001",
        },
    )
    assert resp.status_code == 200, f"Failed: {resp.text}"
    data = resp.json()

    assert data["task"] == "picture"
    m = data["metrics"]
    assert "pic_points" in m
    assert "sentence_count" in m
    assert "verb_count" in m
    assert "ttr" in m
    assert "total_word_count" in m
    assert m["pic_points"] > 0, f"Expected concepts found, got {m['pic_points']}"
    assert m["sentence_count"] > 0
    print(f"\n  PICTURE: {m['pic_points']} Konzepte, {m['sentence_count']} Saetze, TTR={m['ttr']}")


def test_analyze_text_requires_auth(base_url):
    resp = requests.post(
        f"{base_url}/analyze_text",
        json={"transcript": "Test", "taskType": "veggie", "attemptId": "x"},
    )
    assert resp.status_code == 401
