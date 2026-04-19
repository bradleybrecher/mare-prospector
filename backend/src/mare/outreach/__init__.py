"""Pillar 2 — Luxury-Standard Outreach.

Entry points:
- `Prospect` / `SalonProspect`: typed input model for a target salon.
- `OutreachDrafter`: generates a personalized email + short LinkedIn DM.
- `detect_ai_tells`: scans a draft for AI-ish red flags before it reaches a human.
"""

from mare.outreach.detector import DetectionReport, detect_ai_tells
from mare.outreach.personalizer import OutreachDraft, OutreachDrafter
from mare.outreach.postcard import PostcardConcept, PostcardDesigner
from mare.outreach.prospect import SalonProspect, SocialHighlight

__all__ = [
    "DetectionReport",
    "OutreachDraft",
    "OutreachDrafter",
    "PostcardConcept",
    "PostcardDesigner",
    "SalonProspect",
    "SocialHighlight",
    "detect_ai_tells",
]
