"""Generate production-grade image prompts for Midjourney, Imagen, or a human designer.

Why this exists:
- A Short becomes real when its b-roll is shot. When we can't shoot, we generate.
- Image models collapse into stock-photo mush without tight art direction.
- This module turns a Short's b-roll descriptions into per-beat image prompts
  that bake in MaRe's official visual identity (colors by hex, typography,
  logo usage rules — see `mare.brand.identity`), plus the art-direction floor
  below (lighting, composition, forbidden tropes).

Output is model-agnostic: we produce ONE structured concept per beat plus three
rendered prompt strings (Midjourney v6+, Imagen 3, and a generic fallback).
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.brand.identity import (
    BROWN_BASE,
    PRIMARY_COLORS,
    WATER_BASE,
    visual_identity_prompt_block,
)
from mare.content.channels import (
    Channel,
    MOBILE_FIRST_DOCTRINE,
    channel_prompt_block,
    default_channel,
)
from mare.content.shorts import ShortScript
from mare.gemini_client import GeminiClient


# Art-direction floor layered on top of the brand kit's raw identity data.
# The brand kit gives us hex and typography; this gives us the SHOT.
_ART_DIRECTION_FLOOR = f"""Art-direction floor for MaRe imagery (layered on top of the official palette):

- Anchor any warm surface on Brand Brown {BROWN_BASE} (brown-500). Anchor any
  cool/aquatic accent on Key {WATER_BASE} (water-500). Lift with Light
  {PRIMARY_COLORS['Light']} and Clear White {PRIMARY_COLORS['Clear White']}.
  Do NOT use neon, high-saturation pink, cold corporate blue, or typical
  salon-white fluorescence.
- Lighting: soft natural daylight OR a single warm practical lamp. No harsh
  studio, no ring-light beauty glow, no clinical overheads.
- Materials: linen, pale oak, travertine, brushed brass, frosted glass, steam.
  These materials read "European wellness ritual," not "spa menu."
- Composition: calm, unhurried, generous negative space. Slight overhead or
  three-quarter angles preferred. Hands welcome. Direct faces-to-camera avoided.
- Subject priorities: a scalp under soft light, the MaRe Capsule in a quiet
  room, steam rising, a Philip Martin's bottle on a travertine tray, a
  practitioner's hands mid-ritual, a MaRe Eye scan visualization.
- Forbidden tropes: clip-art wellness icons, hair-product bottle against a
  gradient background, "before / after" split panels, stock-photo smiling
  woman with perfect hair, CGI-looking water droplets, anything shouting
  the word "luxury."
- Restraint: say less, show less. Texture over decoration. The brand evokes
  relaxation, trust, and professionalism — not drama.

IMAGE-MODEL TRIPWIRES (Imagen + Midjourney gravitate toward these; write
prompts that explicitly SHUT THEM DOWN):

- SUBJECT POLICY — when a person IS in frame (hands, crown, profile, etc.):
  render a WOMAN by default, 30s-50s, diverse skin tones (warm ivory, olive,
  deep brown rotating beat-to-beat). Roughly one in four beats across a
  Short may feature a man when the beat context supports it (male barber
  client, male stylist, male salon owner). Hair shown should match MaRe's
  clientele: textured brunette, warm balayage, chestnut, silver, natural
  curl patterns — NOT platinum-blonde shampoo-ad hair.
- The word "human" or "person" without a framing verb will render a full
  business portrait. Say "an extreme close-up of a woman's scalp surface
  (no face, no shoulders, no clothing visible)" instead of "a human scalp."
- "Scalp" alone often renders a full head. Always pair it with a framing verb
  ("macro," "extreme close-up," "overhead shot of") AND a texture cue
  ("hair strands filling the frame," "skin texture visible").
- "Healthy hair" often renders a model in a shampoo ad. Say "a single part
  line across dark, lustrous hair, shot from directly above, no face in frame."
- "Dandruff" often renders snow-globe fragments on fabric. Say "fine flecks
  of scalp flake on a dark scalp surface with hair strands in the background"
  or equivalent anatomical framing.
- "Practitioner" without a body-part qualifier will render a full portrait.
  Say "a practitioner's hands" or "gloved fingers" — describe only the hands.
- "Client in a capsule" often renders a sci-fi pod. Describe the MaRe
  Capsule in materials language: "a low-profile wellness chair of pale oak
  and linen, frosted-glass dome, warm practical lamp inside, a client's head
  visible from above (crown only)."
- Never include the word "logo," "text," "label," or "brand" in a positive
  prompt — image models will hallucinate invented logos that violate the
  identity system. Describe bottles and surfaces without any typography.
"""

MARE_VISUAL_SYSTEM = f"""{visual_identity_prompt_block()}

{_ART_DIRECTION_FLOOR}"""


IMAGE_PROMPT_TASK = """For each voiceover beat in a MaRe Short, write an art-directed
image prompt a designer or image-model can execute to generate b-roll.

Constraints (apply to EVERY beat):
- Bake in MaRe's visual identity (pasted above). No need to repeat the full
  identity in every prompt — translate it into concrete visual choices.
- Cinematic, editorial, a touch of Italian restraint.
- Frame for the CHANNEL SPEC below — respect the render aspect and safe area.
  Compose so a downstream crop from render aspect to target aspect does NOT
  amputate the subject or any focal detail.
- One subject per frame. No collages. No text-on-image. No emoji.

HARD RULES on the `subject` and `imagen_prompt` fields (violating these
means the image will miss the brief):

- Every `subject` and `imagen_prompt` MUST open with an explicit framing
  verb: "Extreme close-up of...", "Macro of...", "Overhead shot of...",
  "Three-quarter angle of...", or "Profile view of...". No prompt may begin
  with just a noun like "A healthy scalp" — the model will freelance a full
  portrait.
- If the beat is anatomical (scalp, hair, flakes, root, follicle), the
  prompt MUST explicitly state which body parts are NOT visible. Example:
  "no face, no shoulders, no neck, no clothing visible — hair and scalp
  fill 90% of the frame."
- When a person IS in the frame, specify gender + age range + hair color
  explicitly (honoring the subject policy above — women by default, a man
  when the beat context supports it). Do NOT say "a client" or "a person"
  — say "a woman in her 40s with a warm balayage" or "a man in his 50s with
  short silver hair."
- Avoid the literal string "MaRe Eye" or "MaRe Capsule" in the prompt — image
  models will invent a fictional logo. Describe these props in pure
  materials language (see the IMAGE-MODEL TRIPWIRES above).

Return one entry per beat in the same order. Be concise. Each entry contains:
- `subject`: what's in the frame, concrete nouns. ONE sentence. Opens with
  a framing verb (see hard rules).
- `composition`: framing / angle / lens feel. ONE sentence. Mention the
  safe area explicitly.
- `lighting_and_palette`: light source + color notes. ONE sentence.
- `negative`: what must NOT appear. Short list, comma-separated. MUST include
  at minimum: "text, watermark, logo, typography, invented brand marks,
  stock-photo smile, ring-light beauty glow, CGI water, business portrait,
  clothing if the beat is anatomical".
- `aspect_ratio`: set this to the channel's render aspect ("{render_aspect}").
- `midjourney_prompt`: the full MJ v6 prompt, single line, ending with
  `--ar {render_aspect} --v 6`.
- `imagen_prompt`: plain-prose Imagen 3/4 prompt, single line, no `--ar` flags.
  Opens with a framing verb (see hard rules).
- `generic_prompt`: one-line model-agnostic prompt a human designer could also use.

{visual_system}

{mobile_first}

{channel_spec}

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
    channel: Channel

    def to_markdown(self) -> str:
        out = [
            f"# Image prompts — {self.short_hook}",
            f"_Channel: **{self.channel.label}** "
            f"(target {self.channel.target_aspect}, "
            f"render {self.channel.render_aspect}, "
            f"{'mobile-first' if self.channel.is_mobile_first else 'print'})_\n",
        ]
        for item in self.items:
            out.append(
                f"## Beat {item.beat}\n\n"
                f"**Subject:** {item.subject}  \n"
                f"**Composition:** {item.composition}  \n"
                f"**Lighting / palette:** {item.lighting_and_palette}  \n"
                f"**Negative:** {item.negative}  \n"
                f"**Aspect ratio:** {item.aspect_ratio} "
                f"(crop to {self.channel.target_aspect} for {self.channel.label})\n\n"
                f"### Midjourney\n```\n{item.midjourney_prompt}\n```\n\n"
                f"### Imagen 3/4\n```\n{item.imagen_prompt}\n```\n\n"
                f"### Generic\n```\n{item.generic_prompt}\n```\n"
            )
        return "\n".join(out)


def generate_image_prompts(
    script: ShortScript,
    client: GeminiClient | None = None,
    *,
    channel: Channel | None = None,
) -> ImagePromptSet:
    """Generate per-beat image prompts for a rendered ShortScript.

    Pass `channel` to target something other than the default YouTube Short.
    For example, a long-form blog hero (`channel=get_channel('blog_hero')`)
    will swap the render aspect to 9:16 and bake a mobile-hero composition
    brief into the prompt.
    """
    client = client or GeminiClient.for_text()
    channel = channel or default_channel()
    beat_lines = "\n".join(
        f"- Beat {i + 1}: VO=\"{b.get('vo', '')}\" | B-roll=\"{b.get('b_roll', '')}\""
        for i, b in enumerate(script.voiceover)
    )
    raw = client.generate(
        IMAGE_PROMPT_TASK.format(
            visual_system=MARE_VISUAL_SYSTEM,
            mobile_first=MOBILE_FIRST_DOCTRINE,
            channel_spec=channel_prompt_block(channel),
            render_aspect=channel.render_aspect,
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
    # Ensure the channel's render aspect lands on every item even if the
    # model deviated — the downstream renderer trusts this field.
    items = [item.model_copy(update={"aspect_ratio": channel.render_aspect})
             for item in parsed.items]
    return ImagePromptSet(items=items, short_hook=script.hook, channel=channel)
