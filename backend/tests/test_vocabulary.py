"""Tests for brand-vocabulary coverage. Offline, safe in CI."""

from __future__ import annotations

from mare.brand.vocabulary import evaluate_coverage


def test_empty_text_has_zero_coverage():
    report = evaluate_coverage("")
    assert report.coverage_ratio == 0.0
    assert report.pillars_covered == []


def test_single_pillar_hit():
    report = evaluate_coverage("The MaRe system is calibrated like a protocol.")
    assert "systematic" in report.pillars_covered
    assert report.coverage_ratio == 0.25


def test_balanced_coverage_passes():
    text = (
        "MaRe's wellness protocol pairs natural Italian formulas with a quietly "
        "luxurious head-spa system. Vitality starts at the scalp."
    )
    report = evaluate_coverage(text)
    assert set(report.pillars_covered) >= {"systematic", "luxury", "natural_organic", "wellness"}
    assert not report.over_stuffed_pillars


def test_stuffed_pillar_flagged():
    text = (
        "Wellness, wellness, wellness, and more wellness. Luxury. Balance. "
        "A wellness-forward system."
    )
    report = evaluate_coverage(text)
    assert "wellness" in report.over_stuffed_pillars
