"""Render real images from the per-beat prompts (Imagen 4).

Midjourney has no official API. To actually produce images without leaving the
Gemini key already configured for MaRe, we use Google's Imagen 4 via the same
`google-genai` SDK. The Midjourney prompt strings we generate in
`image_prompts.py` remain valid for a designer who wants to run them in Discord
for hero shots — but for bulk production we render here.

Tier guide:
- `imagen-4.0-generate-001` — default. Best quality/cost for social b-roll.
- `imagen-4.0-fast-generate-001` — for large batches where speed > polish.
- `imagen-4.0-ultra-generate-001` — hero shots and postcards.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

from google.genai import errors as genai_errors
from google.genai import types

from mare.config import Settings
from mare.content.channels import Channel
from mare.content.image_prompts import ImagePromptSet
from mare.gemini_client import GeminiClient


logger = logging.getLogger(__name__)

DEFAULT_IMAGEN_MODEL = "imagen-4.0-generate-001"
IMAGEN_TIERS = {
    "fast": "imagen-4.0-fast-generate-001",
    "standard": "imagen-4.0-generate-001",
    "ultra": "imagen-4.0-ultra-generate-001",
}

# Per-minute quota on new Vertex projects for Imagen 4 is low (often 5/min).
# We backoff on 429 rather than crashing, so a 5-beat Short finishes eventually.
_DEFAULT_429_BACKOFFS = (20, 40, 60)  # seconds — three attempts, ~2 minute ceiling.

# Universal negative prompt baseline — merged with whatever the per-beat
# prompt generator produces. These are things that must NEVER ship in a MaRe
# image regardless of the beat, so we hard-code them at the renderer level as
# a safety net.
_MARE_BASELINE_NEGATIVE = (
    "text, watermark, logo, typography, captions, subtitles, "
    "invented brand marks, signage, "
    "business portrait, corporate headshot, suit and tie, necktie, "
    "stock-photo smile, modelled beauty pose, "
    "ring-light beauty glow, harsh studio, clinical overheads, "
    "CGI water droplets, glossy 3D render, "
    "salon-white fluorescence, neon signage, "
    "platinum-blonde shampoo-ad hair, "
    "split panel, before and after, collage, "
    "distorted hands, extra fingers, malformed anatomy, "
    "low resolution, blurry"
)


def _merge_negative(per_beat_negative: str | None) -> str:
    """Merge a per-beat negative prompt with MaRe's baseline.

    The per-beat negative comes from the prompt generator and targets the
    specific scene; the baseline targets brand-level tripwires (invented
    logos, business portraits, etc.). We always ship both.
    """
    per_beat = (per_beat_negative or "").strip().rstrip(",")
    if not per_beat:
        return _MARE_BASELINE_NEGATIVE
    return f"{per_beat}, {_MARE_BASELINE_NEGATIVE}"


def _generate_with_backoff(
    client: GeminiClient,
    *,
    model: str,
    prompt: str,
    config: types.GenerateImagesConfig,
    backoffs: tuple[int, ...] = _DEFAULT_429_BACKOFFS,
    beat_label: str = "image",
):
    """Call Imagen once; if 429, sleep and retry up to `len(backoffs)` times."""
    for attempt, wait in enumerate((0, *backoffs)):
        if wait:
            logger.warning(
                "Imagen 429 on %s — Vertex per-minute quota hit. "
                "Sleeping %ds before retry %d/%d.",
                beat_label, wait, attempt, len(backoffs),
            )
            time.sleep(wait)
        try:
            return client.raw_client.models.generate_images(
                model=model, prompt=prompt, config=config,
            )
        except genai_errors.ClientError as exc:
            status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            if status != 429 or attempt == len(backoffs):
                raise  # non-429 or out of retries — surface the error.
            # Otherwise fall through to the next loop iteration for backoff.
    # Unreachable — the loop either returns or raises — but keeps type-checkers happy.
    raise RuntimeError("Imagen retry loop exited without return")


@dataclass
class RenderedBeat:
    beat: int
    prompt_used: str
    image_path: Path
    aspect_ratio: str
    crop_to: str
    channel_id: str


@dataclass
class RenderedSet:
    short_hook: str
    beats: list[RenderedBeat]
    model: str
    channel_id: str

    def summary(self) -> str:
        lines = [
            f"Rendered {len(self.beats)} image(s) with {self.model} "
            f"for channel '{self.channel_id}':"
        ]
        for b in self.beats:
            if b.aspect_ratio == b.crop_to:
                lines.append(f"  beat {b.beat} [{b.aspect_ratio}] → {b.image_path}")
            else:
                lines.append(
                    f"  beat {b.beat} [rendered {b.aspect_ratio}, "
                    f"crop to {b.crop_to}] → {b.image_path}"
                )
        return "\n".join(lines)


def render_image_prompts(
    prompts: ImagePromptSet,
    *,
    out_dir: Path,
    tier: str = "standard",
    client: GeminiClient | None = None,
    number_of_images: int = 1,
    channel: Channel | None = None,
) -> RenderedSet:
    """Render one image per beat into `out_dir/<channel>_beat_{n}.png`.

    Uses the `imagen_prompt` field from each item (plain-prose, model-agnostic)
    because MJ-flavored prompts can confuse Imagen with `--ar` flag tokens.

    The Channel attached to `prompts` dictates the render aspect AND the
    downstream crop guidance in the rendered summary. Pass `channel` only to
    override the channel embedded in `prompts`.
    """
    client = client or GeminiClient.for_images()
    model = IMAGEN_TIERS.get(tier, tier if "/" in tier else DEFAULT_IMAGEN_MODEL)
    channel = channel or prompts.channel
    render_aspect = channel.render_aspect

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[RenderedBeat] = []

    for item in prompts.items:
        config = types.GenerateImagesConfig(
            number_of_images=number_of_images,
            aspect_ratio=render_aspect,
            negative_prompt=_merge_negative(item.negative),
        )
        response = _generate_with_backoff(
            client,
            model=model,
            prompt=item.imagen_prompt,
            config=config,
            beat_label=f"beat {item.beat}",
        )
        if not response.generated_images:
            raise RuntimeError(
                f"Imagen returned no images for beat {item.beat}. "
                "Often means the prompt tripped a safety filter — try a less explicit subject."
            )
        gen = response.generated_images[0]
        image_bytes = gen.image.image_bytes
        if image_bytes is None:
            raise RuntimeError(f"Imagen response missing bytes for beat {item.beat}.")
        out_path = out_dir / f"{channel.id}_beat_{item.beat}.png"
        out_path.write_bytes(image_bytes)
        rendered.append(
            RenderedBeat(
                beat=item.beat,
                prompt_used=item.imagen_prompt,
                image_path=out_path,
                aspect_ratio=render_aspect,
                crop_to=channel.target_aspect,
                channel_id=channel.id,
            )
        )
    return RenderedSet(
        short_hook=prompts.short_hook,
        beats=rendered,
        model=model,
        channel_id=channel.id,
    )


def render_single_image(
    prompt: str,
    *,
    out_path: Path,
    aspect_ratio: str = "9:16",
    negative_prompt: str | None = None,
    tier: str = "standard",
    client: GeminiClient | None = None,
) -> Path:
    """One-shot single image (used for postcard front concepts)."""
    client = client or GeminiClient.for_images()
    model = IMAGEN_TIERS.get(tier, tier if "/" in tier else DEFAULT_IMAGEN_MODEL)
    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio=aspect_ratio,
        negative_prompt=_merge_negative(negative_prompt),
    )
    response = _generate_with_backoff(
        client,
        model=model,
        prompt=prompt,
        config=config,
        beat_label="single image",
    )
    if not response.generated_images or response.generated_images[0].image.image_bytes is None:
        raise RuntimeError("Imagen returned no image — check the prompt and safety filters.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.generated_images[0].image.image_bytes)
    return out_path
