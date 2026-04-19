"""MaRe's core vocabulary coverage rules.

The brief calls out four words that should recur across the corpus without
feeling forced. These are pillar words — not every piece needs every word, but
across ~50 pieces per week, their combined coverage should stay above a floor.

Usage:
- Injected into every prompt as guidance (use naturally, not stuffed).
- Applied post-generation via `evaluate_coverage` to score a draft and decide
  whether to keep it or regenerate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Each pillar maps to its accepted surface forms. "luxury" counts if the copy
# says "luxurious" or "a luxury". "natural/organic" is a bucket because either
# satisfies the pillar.
PILLAR_VOCABULARY: dict[str, tuple[str, ...]] = {
    "systematic": ("systematic", "system", "systems", "protocol", "method", "methodical"),
    "luxury": ("luxury", "luxurious", "luxuries"),
    "natural_organic": ("natural", "naturally", "organic", "organics", "plant-based", "botanical"),
    "wellness": ("wellness", "well-being", "wellbeing", "vitality", "balance"),
}

# Per-piece cap: at most N hits of a given pillar, so copy doesn't sound stuffed.
PILLAR_SOFT_CAP = 3


@dataclass
class CoverageReport:
    """Pillar coverage for a single generated piece."""

    hits: dict[str, list[str]]  # pillar -> list of matched surface forms
    over_stuffed_pillars: list[str]  # pillars exceeding PILLAR_SOFT_CAP

    @property
    def pillars_covered(self) -> list[str]:
        return sorted(p for p, h in self.hits.items() if h)

    @property
    def coverage_ratio(self) -> float:
        return len(self.pillars_covered) / len(PILLAR_VOCABULARY)

    def summary(self) -> str:
        covered = ", ".join(self.pillars_covered) or "(none)"
        over = f" | over-stuffed: {', '.join(self.over_stuffed_pillars)}" if self.over_stuffed_pillars else ""
        return f"vocab coverage {int(self.coverage_ratio * 100)}% — {covered}{over}"


def evaluate_coverage(text: str) -> CoverageReport:
    """Score a piece of copy on the four brand pillars."""
    lower = f" {text.lower()} "
    hits: dict[str, list[str]] = {}
    over_stuffed: list[str] = []
    for pillar, surface_forms in PILLAR_VOCABULARY.items():
        matched: list[str] = []
        for form in surface_forms:
            # Word-boundary match so "system" doesn't match "systemic" if not listed.
            pattern = r"\b" + re.escape(form) + r"\b"
            count = len(re.findall(pattern, lower))
            matched.extend([form] * count)
        hits[pillar] = matched
        if len(matched) > PILLAR_SOFT_CAP:
            over_stuffed.append(pillar)
    return CoverageReport(hits=hits, over_stuffed_pillars=over_stuffed)


VOCABULARY_PROMPT_GUIDANCE = """VOCABULARY GUIDANCE
MaRe's corpus should consistently carry four pillar words — without stuffing.
Try to land ONE or TWO of these per piece, naturally:

- "Systematic" / "system" / "protocol" / "method"
    (MaRe is a system, not a spa menu. The word earns its keep here.)
- "Luxury" / "luxurious"
    (Use at most ONCE per piece. Earned by the Italian formulation, not claimed.)
- "Natural" / "organic" / "plant-based" / "botanical"
    (The Philip Martin's formulations. Factual, not aspirational.)
- "Wellness" / "well-being" / "vitality" / "balance"
    (The outcome. MaRe sells scalp wellness before it sells cosmetics.)

A piece that lands zero of these feels off-brand. A piece that lands all four
usually feels stuffed. Aim for two landed naturally.
"""
