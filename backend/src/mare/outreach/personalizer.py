"""Generate personalized outreach drafts (email + LinkedIn DM) for a salon."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.gemini_client import GeminiClient
from mare.outreach.detector import DetectionReport, detect_ai_tells
from mare.outreach.prospect import SalonProspect
from mare.outreach.templates import COLD_EMAIL_TASK, LINKEDIN_DM_TASK


class _EmailResponse(BaseModel):
    subject: str = Field(..., description="5 words or fewer, lowercase except proper nouns.")
    body: str = Field(..., description="3 short paragraphs, separated by blank lines.")
    personalization_anchor: str = Field(..., description="The single specific detail you anchored on.")
    chosen_angle: str = Field(..., description="retail_attach | chair_time | italian_formulation | scalp_category | other")
    self_critique: str


class _DMResponse(BaseModel):
    message: str = Field(..., description="The DM text, 50 words or fewer.")
    word_count: int
    self_critique: str


@dataclass
class OutreachDraft:
    subject: str
    body: str
    linkedin_dm: str
    personalization_anchor: str
    chosen_angle: str
    self_critique: str
    email_report: DetectionReport
    dm_report: DetectionReport

    @property
    def is_clean(self) -> bool:
        return self.email_report.is_clean and self.dm_report.is_clean

    def to_markdown(self) -> str:
        return (
            f"# Outreach draft\n\n"
            f"**Anchor:** {self.personalization_anchor}  \n"
            f"**Angle:** {self.chosen_angle}  \n"
            f"**Self-critique:** {self.self_critique}\n\n"
            f"## Email\n\n"
            f"**Subject:** {self.subject}\n\n"
            f"{self.body}\n\n"
            f"## LinkedIn DM\n\n"
            f"{self.linkedin_dm}\n\n"
            f"---\n"
            f"*Email check:* {self.email_report.summary()}\n\n"
            f"*DM check:* {self.dm_report.summary()}\n"
        )


class OutreachDrafter:
    """Generates email + DM drafts for a `SalonProspect`."""

    def __init__(self, client: GeminiClient | None = None):
        self._client = client or GeminiClient.for_text()

    def draft(
        self,
        prospect: SalonProspect,
        *,
        sender_name: str = "Rebecca",
        sender_title: str = "Co-Founder",
    ) -> OutreachDraft:
        context = prospect.as_prompt_context()

        email_raw = self._client.generate(
            COLD_EMAIL_TASK.format(
                prospect_context=context,
                sender_name=sender_name,
                sender_title=sender_title,
            ),
            temperature=0.75,
            response_schema=_EmailResponse,
            use_reasoning_model=True,
        )
        email = _EmailResponse.model_validate_json(email_raw.text)

        dm_raw = self._client.generate(
            LINKEDIN_DM_TASK.format(
                prospect_context=context,
                sender_name=sender_name,
                sender_title=sender_title,
            ),
            temperature=0.75,
            response_schema=_DMResponse,
        )
        dm = _DMResponse.model_validate_json(dm_raw.text)

        full_email_text = f"{email.subject}\n\n{email.body}"
        return OutreachDraft(
            subject=email.subject,
            body=email.body,
            linkedin_dm=dm.message,
            personalization_anchor=email.personalization_anchor,
            chosen_angle=email.chosen_angle,
            self_critique=email.self_critique,
            email_report=detect_ai_tells(full_email_text),
            dm_report=detect_ai_tells(dm.message),
        )
