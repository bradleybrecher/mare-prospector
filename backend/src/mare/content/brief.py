"""A single brief shared by every content generator.

One brief -> N assets (Short, blog, IG caption, email teaser). This is how we
hit 50+ pieces/week without losing narrative coherence.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Audience = Literal["salon_owner", "stylist", "high_end_client", "scalp_curious"]


class ContentBrief(BaseModel):
    topic: str = Field(..., description="The central idea. One sentence, not a title.")
    audience: Audience = "high_end_client"
    desired_emotion: str = Field(
        "quiet confidence",
        description="The feeling the viewer should leave with. e.g. 'calm', 'curiosity', 'relief'.",
    )
    proof_point: str | None = Field(
        None,
        description="A concrete credibility anchor — Miami lab, Italian formulation, a client result, a stat.",
    )
    call_to_action: str | None = Field(
        None,
        description="What the viewer should do next. Optional; many brand pieces should have none.",
    )
    must_mention: list[str] = Field(
        default_factory=list,
        description="Phrases or products that must appear (e.g. 'MaRe Capsule').",
    )
    must_not_mention: list[str] = Field(
        default_factory=list,
        description="Competitors, banned claims, or out-of-scope topics.",
    )

    def as_prompt_context(self) -> str:
        lines = [
            f"Topic: {self.topic}",
            f"Audience: {self.audience}",
            f"Desired emotion: {self.desired_emotion}",
        ]
        if self.proof_point:
            lines.append(f"Proof point: {self.proof_point}")
        if self.call_to_action:
            lines.append(f"CTA: {self.call_to_action}")
        if self.must_mention:
            lines.append("Must mention: " + ", ".join(self.must_mention))
        if self.must_not_mention:
            lines.append("Must NOT mention: " + ", ".join(self.must_not_mention))
        return "\n".join(lines)
