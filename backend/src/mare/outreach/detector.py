"""Post-generation scanner for AI-ish tells.

Every draft from `OutreachDrafter` is run through `detect_ai_tells`. If the
report has any hits, the CLI flags the draft so a human either rewrites or
asks the model to regenerate with a specific critique.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from mare.brand import AI_ISH_PHRASES, AI_ISH_WORDS


@dataclass
class DetectionReport:
    banned_words: list[str] = field(default_factory=list)
    banned_phrases: list[str] = field(default_factory=list)
    em_dash_pairs: int = 0
    tricolon_hits: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return (
            not self.banned_words
            and not self.banned_phrases
            and self.em_dash_pairs == 0
            and not self.tricolon_hits
        )

    def summary(self) -> str:
        if self.is_clean:
            return "Clean — no AI-ish tells detected."
        parts = []
        if self.banned_words:
            parts.append(f"banned words: {', '.join(sorted(set(self.banned_words)))}")
        if self.banned_phrases:
            parts.append(f"banned phrases: {'; '.join(self.banned_phrases)}")
        if self.em_dash_pairs:
            parts.append(f"em-dash pairs: {self.em_dash_pairs}")
        if self.tricolon_hits:
            parts.append(f"tricolons: {len(self.tricolon_hits)}")
        return "Flagged — " + " | ".join(parts)


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-']*")
_EM_DASH_PAIR_RE = re.compile(r"—[^—]{2,80}—")
# Very simple tricolon heuristic: "X, Y, and Z" or "X, Y, Z." with short items.
_TRICOLON_RE = re.compile(
    r"\b([A-Za-z][A-Za-z ]{2,25}),\s+([A-Za-z][A-Za-z ]{2,25}),\s+(?:and\s+)?([A-Za-z][A-Za-z ]{2,25})\b"
)


def detect_ai_tells(text: str) -> DetectionReport:
    """Scan `text` for the tells defined in `mare.brand.ai_red_flags`."""
    report = DetectionReport()
    lower = text.lower()

    tokens = [m.group(0).lower() for m in _WORD_RE.finditer(text)]
    for tok in tokens:
        if tok in AI_ISH_WORDS:
            report.banned_words.append(tok)

    for phrase in AI_ISH_PHRASES:
        if phrase in lower:
            report.banned_phrases.append(phrase)

    report.em_dash_pairs = len(_EM_DASH_PAIR_RE.findall(text))
    report.tricolon_hits = [m.group(0) for m in _TRICOLON_RE.finditer(text)]

    return report
