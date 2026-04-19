"""Tests for the AI-ish tell detector.

These run offline (no Gemini) so they're safe in CI.
"""

from __future__ import annotations

from mare.outreach.detector import detect_ai_tells


def test_clean_text_passes():
    text = (
        "Saw your post about the balayage class last month. "
        "We built the MaRe Capsule for salons whose clients already expect a ritual.\n\n"
        "Worth fifteen minutes?\n\nMarcella"
    )
    report = detect_ai_tells(text)
    assert report.is_clean, report.summary()


def test_catches_banned_word_delve():
    report = detect_ai_tells("Let's delve into scalp health together.")
    assert "delve" in report.banned_words


def test_catches_banned_phrase():
    report = detect_ai_tells("I hope this email finds you well.")
    assert any("finds you well" in p for p in report.banned_phrases)


def test_catches_em_dash_pair():
    report = detect_ai_tells("MaRe — the boutique head-spa system — is from Miami.")
    assert report.em_dash_pairs >= 1


def test_catches_tricolon():
    report = detect_ai_tells("We design, we deliver, and we delight every client.")
    assert report.tricolon_hits
