"""Short-form social captions (IG, LinkedIn, X)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from mare.content.brief import ContentBrief
from mare.gemini_client import GeminiClient

Platform = Literal["instagram", "linkedin", "x"]

SOCIAL_TASK = """Write a social caption for MaRe on {platform}.

PLATFORM RULES
- instagram: up to 40 words. Sensorial, intimate. Up to 5 niche hashtags.
- linkedin: up to 80 words. Written like a practitioner's note, not a brand post. No hashtag stacks.
- x: up to 25 words. One idea. No hashtags unless essential.

HARD RULES (all platforms)
- No hook formulas like "Here's the truth about..." or "Most people don't know...".
- No humblebrags.
- No emoji unless the brief explicitly allows it.
- First line must earn the rest. If it doesn't, rewrite it.

BRIEF
{brief_context}

Return the caption as structured JSON matching the declared response schema.
"""


class _SocialResponse(BaseModel):
    platform: str
    caption: str
    alt_versions: list[str] = Field(default_factory=list, description="1-2 alternative first lines to A/B test.")
    hashtags: list[str] = Field(default_factory=list)
    word_count: int
    self_critique: str


@dataclass
class SocialPost:
    platform: Platform
    caption: str
    alt_versions: list[str]
    hashtags: list[str]
    word_count: int
    self_critique: str
    raw: dict

    def to_markdown(self) -> str:
        alts = "\n".join(f"- {a}" for a in self.alt_versions) or "- (none)"
        tags = " ".join("#" + h.lstrip("#") for h in self.hashtags) if self.hashtags else "(none)"
        return (
            f"# Social — {self.platform}\n\n"
            f"**Words:** {self.word_count}  \n"
            f"**Self-critique:** {self.self_critique}\n\n"
            f"## Caption\n\n{self.caption}\n\n"
            f"## Alt first lines\n{alts}\n\n"
            f"**Hashtags:** {tags}\n"
        )


def generate_social_caption(
    brief: ContentBrief,
    platform: Platform = "instagram",
    client: GeminiClient | None = None,
) -> SocialPost:
    client = client or GeminiClient.for_text()
    result = client.generate(
        SOCIAL_TASK.format(platform=platform, brief_context=brief.as_prompt_context()),
        temperature=0.85,
        response_schema=_SocialResponse,
    )
    parsed = _SocialResponse.model_validate_json(result.text)
    return SocialPost(
        platform=platform,
        caption=parsed.caption,
        alt_versions=parsed.alt_versions,
        hashtags=parsed.hashtags,
        word_count=parsed.word_count,
        self_critique=parsed.self_critique,
        raw=parsed.model_dump(),
    )
