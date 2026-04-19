"""Generate production-grade image prompts for Midjourney, Imagen, or a human designer.

Why this exists:
- A Short becomes real when its b-roll is shot. When we can't shoot, we generate.
- Image models collapse into stock-photo mush without tight art direction.
- This module turns a Short's b-roll descriptions into per-beat image prompts
  that bake in MaRe's visual language — warm beige + muted teal + brass,
  natural light, Italian-craft restraint, no faces-to-camera clichés.

Output is model-agnostic: we produce ONE structured concept per beat plus three
rendered prompt strings (Midjourney v6+, Imagen 3, and a generic fallback).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.content.shorts import ShortScript
from mare.gemini_client import GeminiClient


MARE_VISUAL_SYSTEM = """MaRe visual identity (use as art-direction floor):
- Palette: warm beige / taupe, muted teal / seafoam, ivory, brushed brass.
  Do NOT use neon, high-saturation pink, cold blue, or typical salon white.
- Lighting: soft natural daylight OR a single warm practical lamp. No harsh studio.
- Materials: linen, pale oak, brushed brass, frosted glass, travertine, steam.
- Composition: calm, unhurried, plenty of negative space. Often a slight overhead
  or three-quarter angle. Hands are welcome. Faces-to-camera are avoided.
- Subject priorities: a scalp, a MaRe Capsule in a quiet room, steam rising, a
  product bottle on a travertine tray, a stylist's hands in the middle of a ritual.
- Forbidden tropes: clip-art wellness icons, hair-product bottle against
  gradient background, "before / after" split, stock-photo smiling woman with
  perfect hair, water droplets that look CGI, anything shouting "luxury".
- Italian restraint: say less, show less. Texture over decoration.
"""


IMAGE_PROMPT_TASK = """For each voiceover beat in a MaRe Short, write an art-directed
image prompt a designer or image-model can execute to generate b-roll.

Constraints (apply to EVERY beat):
- Bake in MaRe's visual identity (pasted above). No need to repeat the full
  identity in every prompt — translate it into concrete visual choices.
- Cinematic, editorial, a touch of Italian restraint.
- 16:9 for wide shots, 9:16 for vertical (Shorts are vertical — default to 9:16).
- One subject per frame. No collages. No text-on-image. No emoji.

Return one entry per beat in the same order. Be concise. Each entry contains:
- `subject`: what's in the frame, concrete nouns. ONE sentence.
- `composition`: framing / angle / lens feel. ONE sentence.
- `lighting_and_palette`: light source + color notes. ONE sentence.
- `negative`: what must NOT appear. Short list, comma-separated.
- `aspect_ratio`: "9:16" unless the brief clearly wants wide.
- `midjourney_prompt`: the full MJ v6 prompt, single line, ending with `--ar 9:16 --v 6`.
- `imagen_prompt`: plain-prose Imagen 3 prompt, single line, no `--ar` flags.
- `generic_prompt`: one-line model-agnostic prompt a human designer could also use.

{visual_system}

SHORT DETAILS
- Hook: "{hook}"
- Head query: "{head_query}"
- LLM summary: "{llm_summary}"

BEATS
{beat_lines}

Return the full set as structured JSON matching the declared response schema.
"""


class _ImagePromptItem(BaseModel):
    beat: int
    subject: str
    composition: str
    lighting_and_palette: str
    negative: str
    aspect_ratio: str = "9:16"
    midjourney_prompt: str
    imagen_prompt: str
    generic_prompt: str


class _ImagePromptResponse(BaseModel):
    items: list[_ImagePromptItem] = Field(..., description="One entry per voiceover beat, in order.")


@dataclass
class ImagePromptSet:
    items: list[_ImagePromptItem]
    short_hook: str

    def to_markdown(self) -> str:
        out = [f"# Image prompts — {self.short_hook}\n"]
        for item in self.items:
            out.append(
                f"## Beat {item.beat}\n\n"
                f"**Subject:** {item.subject}  \n"
                f"**Composition:** {item.composition}  \n"
                f"**Lighting / palette:** {item.lighting_and_palette}  \n"
                f"**Negative:** {item.negative}  \n"
                f"**Aspect ratio:** {item.aspect_ratio}\n\n"
                f"### Midjourney\n```\n{item.midjourney_prompt}\n```\n\n"
                f"### Imagen 3\n```\n{item.imagen_prompt}\n```\n\n"
                f"### Generic\n```\n{item.generic_prompt}\n```\n"
            )
        return "\n".join(out)


def generate_image_prompts(
    script: ShortScript,
    client: GeminiClient | None = None,
) -> ImagePromptSet:
    """Generate per-beat image prompts for a rendered ShortScript."""
    client = client or GeminiClient.from_env()
    beat_lines = "\n".join(
        f"- Beat {i + 1}: VO=\"{b.get('vo', '')}\" | B-roll=\"{b.get('b_roll', '')}\""
        for i, b in enumerate(script.voiceover)
    )
    raw = client.generate(
        IMAGE_PROMPT_TASK.format(
            visual_system=MARE_VISUAL_SYSTEM,
            hook=script.hook,
            head_query=script.ai_search.target_queries.head_query,
            llm_summary=script.ai_search.llm_summary,
            beat_lines=beat_lines,
        ),
        temperature=0.7,
        max_output_tokens=8192,
        response_schema=_ImagePromptResponse,
        use_reasoning_model=True,
    )
    parsed = _ImagePromptResponse.model_validate_json(raw.text)
    return ImagePromptSet(items=parsed.items, short_hook=script.hook)
