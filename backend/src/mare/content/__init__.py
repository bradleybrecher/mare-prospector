"""Pillar 3 — High-Volume Content Synthesis.

Generates YouTube Shorts scripts, blog drafts, and social captions on-brand,
at 50x the current cadence. Every generator shares:

- The MaRe brand system prompt (via `GeminiClient`).
- A typed `ContentBrief` input so ideation and copy stay separate jobs.
- JSON-shaped outputs so results are easy to store, review, and diff.
"""

from mare.content.blogs import BlogDraft, generate_blog
from mare.content.brief import ContentBrief
from mare.content.channels import (
    CHANNELS,
    Channel,
    DEFAULT_CHANNEL_ID,
    IMAGEN_NATIVE_ASPECTS,
    MOBILE_FIRST_DOCTRINE,
    channel_prompt_block,
    channels_summary,
    default_channel,
    get_channel,
    list_channels,
)
from mare.content.image_prompts import ImagePromptSet, generate_image_prompts
from mare.content.image_renderer import (
    IMAGEN_TIERS,
    RenderedBeat,
    RenderedSet,
    render_image_prompts,
    render_single_image,
)
from mare.content.pipeline import ContentPipeline
from mare.content.search_optimization import AISearchBlock, TargetQueries
from mare.content.shorts import ShortScript, generate_short_script
from mare.content.social import SocialPost, generate_social_caption
from mare.content.video_adapters import (
    HeyGenClient,
    HeyGenJobSpec,
    HeyGenSubmission,
    script_to_heygen_spec,
)

__all__ = [
    "AISearchBlock",
    "BlogDraft",
    "CHANNELS",
    "Channel",
    "ContentBrief",
    "ContentPipeline",
    "DEFAULT_CHANNEL_ID",
    "HeyGenClient",
    "HeyGenJobSpec",
    "HeyGenSubmission",
    "IMAGEN_NATIVE_ASPECTS",
    "IMAGEN_TIERS",
    "ImagePromptSet",
    "MOBILE_FIRST_DOCTRINE",
    "RenderedBeat",
    "RenderedSet",
    "ShortScript",
    "SocialPost",
    "TargetQueries",
    "channel_prompt_block",
    "channels_summary",
    "default_channel",
    "generate_blog",
    "generate_image_prompts",
    "generate_short_script",
    "generate_social_caption",
    "get_channel",
    "list_channels",
    "render_image_prompts",
    "render_single_image",
    "script_to_heygen_spec",
]
