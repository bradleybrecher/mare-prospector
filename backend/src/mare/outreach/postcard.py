"""Luxury direct-mail postcard concepts.

The postcard is the physical counterpoint to the email. In a luxury B2B motion
a beautiful, specific piece of mail outperforms a beautiful email every time.
This module produces a printable creative brief:

- Front: image concept + art direction (for Midjourney / Imagen / a designer).
- Back: handwritten-style copy addressed to the owner.
- Production: paper stock, foil, size, teaser envelope — tactile luxury cues.
- QR landing page suggestion: what page on mareheadspa.com the card sends to.

Use with `python -m mare outreach postcard --salon-name ...`.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.gemini_client import GeminiClient
from mare.outreach.prospect import SalonProspect


POSTCARD_TASK = """Design a luxury direct-mail postcard concept from MaRe to a named salon owner.

The goal is not to explain MaRe. The goal is to make the recipient save the postcard
on their desk for a week. It should feel like a personal note, not a marketing piece.

THE FRONT
- One evocative image concept. Describe it as a tight art-direction brief a designer
  or an image model can execute. Include subject, lighting, color palette (warm beige,
  muted teal, cream, brass work well for MaRe), framing, and what must NOT appear.
- On-card text: at most 6 words, set in restrained typography. Optional.

THE BACK
- Addressed to the owner by first name if known.
- Hand-written feel. 3 short lines OR one short paragraph. No more.
- MUST reference ONE specific thing about this salon (social highlight first, then
  notable detail, then city+specialty). NEVER say "I saw your Instagram".
- Close with a single line and first name signature. No URL, no logo text.

PRODUCTION NOTES (use only options that fit a luxury Italian-craft brand)
- Paper stock: e.g. "Mohawk Superfine, 130lb cover, eggshell".
- Finish: e.g. "blind deboss of the MaRe wordmark, no ink on the back of the wordmark".
- Foil: used sparingly. Often not at all.
- Size: standard A6 (105x148mm) OR oversized A5 (148x210mm). Decide and justify.
- Optional: a vellum wrap, a wax seal, or a short teaser line on the envelope.

QR / LANDING
- Suggest the single URL (a page on https://mareheadspa.com) the recipient should
  land on if they scan a small QR placed on the back. If the card is powerful
  enough to stand alone without a QR, say so and return null.

PROSPECT CONTEXT
{prospect_context}

SENDER
{sender_name}, {sender_title} at MaRe (Miami).

Return the concept as structured JSON matching the declared response schema.
"""


class _PostcardResponse(BaseModel):
    front_image_concept: str = Field(..., description="Art-direction brief for the front image. 2-4 sentences.")
    front_image_negative_prompt: str = Field(
        "",
        description="What must NOT appear. e.g. 'no people, no product shots, no text-on-image clichés'.",
    )
    front_on_card_text: str | None = Field(None, description="Optional, <=6 words.")
    back_copy: str = Field(..., description="The handwritten-style back-of-card copy.")
    back_signature: str = Field(..., description="First-name-only signature.")
    paper_stock: str
    finish: str
    foil: str | None = Field(None, description="Foil details, or null if none.")
    size: str
    envelope_teaser: str | None = Field(None, description="Optional short line on the envelope.")
    landing_url: str | None = Field(None, description="Suggested page on mareheadspa.com, or null.")
    anchor_used: str = Field(..., description="The specific detail you anchored on.")
    rationale: str = Field(..., description="One sentence on why this concept fits this salon.")


@dataclass
class PostcardConcept:
    front_image_concept: str
    front_image_negative_prompt: str
    front_on_card_text: str | None
    back_copy: str
    back_signature: str
    paper_stock: str
    finish: str
    foil: str | None
    size: str
    envelope_teaser: str | None
    landing_url: str | None
    anchor_used: str
    rationale: str
    raw: dict

    def to_markdown(self) -> str:
        optional_lines = []
        if self.front_on_card_text:
            optional_lines.append(f"**On-card text (front):** {self.front_on_card_text}")
        if self.foil:
            optional_lines.append(f"**Foil:** {self.foil}")
        if self.envelope_teaser:
            optional_lines.append(f"**Envelope teaser:** {self.envelope_teaser}")
        if self.landing_url:
            optional_lines.append(f"**QR landing:** {self.landing_url}")
        optional_block = "\n".join(optional_lines)

        return (
            f"# Postcard concept\n\n"
            f"**Anchor:** {self.anchor_used}  \n"
            f"**Rationale:** {self.rationale}\n\n"
            f"## Front — image\n\n"
            f"{self.front_image_concept}\n\n"
            f"*Negative prompt:* {self.front_image_negative_prompt or '(none)'}\n\n"
            f"## Back — copy\n\n"
            f"{self.back_copy}\n\n"
            f"— {self.back_signature}\n\n"
            f"## Production\n\n"
            f"**Paper stock:** {self.paper_stock}  \n"
            f"**Finish:** {self.finish}  \n"
            f"**Size:** {self.size}\n\n"
            f"{optional_block}\n"
        ).rstrip() + "\n"


class PostcardDesigner:
    def __init__(self, client: GeminiClient | None = None):
        self._client = client or GeminiClient.for_text()

    def design(
        self,
        prospect: SalonProspect,
        *,
        sender_name: str = "Rebecca",
        sender_title: str = "Co-Founder",
    ) -> PostcardConcept:
        raw = self._client.generate(
            POSTCARD_TASK.format(
                prospect_context=prospect.as_prompt_context(),
                sender_name=sender_name,
                sender_title=sender_title,
            ),
            temperature=0.85,
            response_schema=_PostcardResponse,
            use_reasoning_model=True,
        )
        parsed = _PostcardResponse.model_validate_json(raw.text)
        return PostcardConcept(
            front_image_concept=parsed.front_image_concept,
            front_image_negative_prompt=parsed.front_image_negative_prompt,
            front_on_card_text=parsed.front_on_card_text,
            back_copy=parsed.back_copy,
            back_signature=parsed.back_signature,
            paper_stock=parsed.paper_stock,
            finish=parsed.finish,
            foil=parsed.foil,
            size=parsed.size,
            envelope_teaser=parsed.envelope_teaser,
            landing_url=parsed.landing_url,
            anchor_used=parsed.anchor_used,
            rationale=parsed.rationale,
            raw=parsed.model_dump(),
        )
