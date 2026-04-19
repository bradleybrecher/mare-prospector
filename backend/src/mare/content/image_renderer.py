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

from dataclasses import dataclass
from pathlib import Path

from google.genai import types

from mare.config import Settings
from mare.content.image_prompts import ImagePromptSet
from mare.gemini_client import GeminiClient


DEFAULT_IMAGEN_MODEL = "imagen-4.0-generate-001"
IMAGEN_TIERS = {
    "fast": "imagen-4.0-fast-generate-001",
    "standard": "imagen-4.0-generate-001",
    "ultra": "imagen-4.0-ultra-generate-001",
}


@dataclass
class RenderedBeat:
    beat: int
    prompt_used: str
    image_path: Path
    aspect_ratio: str


@dataclass
class RenderedSet:
    short_hook: str
    beats: list[RenderedBeat]
    model: str

    def summary(self) -> str:
        lines = [f"Rendered {len(self.beats)} image(s) with {self.model}:"]
        for b in self.beats:
            lines.append(f"  beat {b.beat} [{b.aspect_ratio}] → {b.image_path}")
        return "\n".join(lines)


def render_image_prompts(
    prompts: ImagePromptSet,
    *,
    out_dir: Path,
    tier: str = "standard",
    client: GeminiClient | None = None,
    number_of_images: int = 1,
) -> RenderedSet:
    """Render one image per beat into `out_dir/beat_{n}.png`.

    Uses the `imagen_prompt` field from each item (plain-prose, model-agnostic)
    because MJ-flavored prompts can confuse Imagen with `--ar` flag tokens.
    """
    client = client or GeminiClient.from_env()
    model = IMAGEN_TIERS.get(tier, tier if "/" in tier else DEFAULT_IMAGEN_MODEL)

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[RenderedBeat] = []

    for item in prompts.items:
        config = types.GenerateImagesConfig(
            number_of_images=number_of_images,
            aspect_ratio=item.aspect_ratio or "9:16",
            negative_prompt=item.negative or None,
        )
        response = client.raw_client.models.generate_images(
            model=model,
            prompt=item.imagen_prompt,
            config=config,
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
        out_path = out_dir / f"beat_{item.beat}.png"
        out_path.write_bytes(image_bytes)
        rendered.append(
            RenderedBeat(
                beat=item.beat,
                prompt_used=item.imagen_prompt,
                image_path=out_path,
                aspect_ratio=item.aspect_ratio or "9:16",
            )
        )
    return RenderedSet(short_hook=prompts.short_hook, beats=rendered, model=model)


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
    client = client or GeminiClient.from_env()
    model = IMAGEN_TIERS.get(tier, tier if "/" in tier else DEFAULT_IMAGEN_MODEL)
    config = types.GenerateImagesConfig(
        number_of_images=1,
        aspect_ratio=aspect_ratio,
        negative_prompt=negative_prompt,
    )
    response = client.raw_client.models.generate_images(
        model=model,
        prompt=prompt,
        config=config,
    )
    if not response.generated_images or response.generated_images[0].image.image_bytes is None:
        raise RuntimeError("Imagen returned no image — check the prompt and safety filters.")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.generated_images[0].image.image_bytes)
    return out_path
