"""YouTube Shorts / Reels / TikTok scripts (30–60s vertical)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.content.brief import ContentBrief
from mare.content.search_optimization import (
    AI_SEARCH_PROMPT_GUIDANCE,
    AISearchBlock,
)
from mare.gemini_client import GeminiClient

SHORT_TASK = """Write a 45-second vertical-video script (YouTube Shorts / Reels / TikTok) for MaRe.

STRUCTURE
- Hook (first 2 seconds): one line, under 8 words, that stops the scroll. No questions unless genuinely provocative.
- Body (≈30 seconds): spoken voiceover in 2–4 short beats. Each beat pairs one sensory image with one idea.
- Payoff (≈8 seconds): the insight that pays off the hook. Not a CTA unless the brief asks for one.

HARD RULES
- Voiceover must sound like a person talking to one friend, not to a room.
- No rhetorical "Did you know...?" openers.
- If showing the MaRe Capsule on screen, describe the b-roll in [brackets], not in the VO.
- If the brief supplies a CTA, place it only in the final beat, and keep it under 10 words.

{ai_search_guidance}

BRIEF
{brief_context}

Return the script as structured JSON matching the declared response schema.
The caption text will be indexed by YouTube's search and by LLM scrapers — make
it carry real keywords without sounding stuffed.
"""


class _VOBeat(BaseModel):
    beat: int = Field(..., description="1-indexed beat number.")
    vo: str = Field(..., description="Spoken voiceover line for this beat.")
    b_roll: str = Field(..., description="What appears on screen during this beat (in plain prose, not brackets).")


class _ShortResponse(BaseModel):
    hook: str = Field(..., description="On-screen hook text, under 8 words.")
    voiceover: list[_VOBeat] = Field(..., description="2-4 voiceover beats.")
    on_screen_text: list[str] = Field(..., description="Up to 3 short captions reinforcing the voiceover.")
    caption: str = Field(..., description="Social caption posted with the video, under 30 words.")
    hashtags: list[str] = Field(..., description="Up to 5 niche hashtags, lowercase, no generics like #hair.")
    estimated_duration_seconds: int = Field(..., description="Estimated total duration in seconds.")
    ai_search: AISearchBlock
    self_critique: str = Field(..., description="One sentence naming the riskiest cliché you avoided.")


@dataclass
class ShortScript:
    hook: str
    voiceover: list[dict]
    on_screen_text: list[str]
    caption: str
    hashtags: list[str]
    estimated_duration_seconds: int
    ai_search: AISearchBlock
    self_critique: str
    raw: dict

    def to_markdown(self) -> str:
        vo_lines = "\n".join(
            f"{b.get('beat', i + 1)}. **VO:** {b.get('vo', '')}  \n   **B-roll:** {b.get('b_roll', '')}"
            for i, b in enumerate(self.voiceover)
        )
        tq = self.ai_search.target_queries
        return (
            f"# Short — {self.hook}\n\n"
            f"**Est. duration:** {self.estimated_duration_seconds}s  \n"
            f"**Self-critique:** {self.self_critique}\n\n"
            f"## Voiceover\n\n{vo_lines}\n\n"
            f"## On-screen text\n" + "\n".join(f"- {t}" for t in self.on_screen_text) + "\n\n"
            f"## Caption\n{self.caption}\n\n"
            f"**Hashtags:** {' '.join('#' + h.lstrip('#') for h in self.hashtags)}\n\n"
            f"---\n\n"
            f"## AI Search Block\n\n"
            f"**Head query:** {tq.head_query}  \n"
            f"**Body queries:** {', '.join(tq.body_queries) or '(none)'}  \n"
            f"**LLM summary:** {self.ai_search.llm_summary}\n"
        )


def generate_short_script(brief: ContentBrief, client: GeminiClient | None = None) -> ShortScript:
    client = client or GeminiClient.for_text()
    result = client.generate(
        SHORT_TASK.format(
            brief_context=brief.as_prompt_context(),
            ai_search_guidance=AI_SEARCH_PROMPT_GUIDANCE,
        ),
        temperature=0.85,
        max_output_tokens=4096,
        response_schema=_ShortResponse,
    )
    parsed = _ShortResponse.model_validate_json(result.text)
    return ShortScript(
        hook=parsed.hook,
        voiceover=[b.model_dump() for b in parsed.voiceover],
        on_screen_text=parsed.on_screen_text,
        caption=parsed.caption,
        hashtags=parsed.hashtags,
        estimated_duration_seconds=parsed.estimated_duration_seconds,
        ai_search=parsed.ai_search,
        self_critique=parsed.self_critique,
        raw=parsed.model_dump(),
    )
