"""Channel registry — MaRe's mobile-first distribution matrix.

MaRe content is consumed on a phone first, a desktop second, a printed piece
third. Every generated asset is framed, lit, and cropped for that hierarchy.

This module is the single source of truth for:
  - which distribution channels MaRe ships to
  - the native aspect ratio for each channel
  - the Imagen-native aspect we actually render at (Imagen 4 supports
    1:1, 3:4, 4:3, 9:16, 16:9 — so non-native channel ratios like
    IG Feed 4:5 or Pinterest 2:3 are rendered at the nearest native
    aspect with generous safe-area margins)
  - the safe-area rule a designer or cropping script follows downstream
  - the prompt-guidance block the image-prompt generator injects so the
    mobile-first framing is present BEFORE the image is drawn, not after

Keep adding channels here when MaRe expands distribution. Every generator
and the CLI inherit new channels automatically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

# Re-exported here so content generators can depend on a single symbol
# (`channels.MOBILE_FIRST_DOCTRINE`) without reaching into brand.identity.
from mare.brand.identity import MOBILE_FIRST_DOCTRINE  # noqa: F401


# The set of aspect ratios Imagen 4 can natively produce. Non-native targets
# must be rendered at the nearest native ratio + cropped downstream.
IMAGEN_NATIVE_ASPECTS: tuple[str, ...] = ("1:1", "3:4", "4:3", "9:16", "16:9")


@dataclass(frozen=True)
class Channel:
    """A single distribution channel (a place MaRe content lands)."""

    id: str
    label: str

    # The TRUE target aspect on the platform, as spec'd by the platform.
    target_aspect: str

    # The Imagen-native aspect we actually render at. Must be in
    # IMAGEN_NATIVE_ASPECTS. If target == render, no cropping needed.
    render_aspect: str

    # Where the focal subject + any on-image text must sit so that the
    # mobile crop doesn't amputate it. Free-form, one sentence.
    safe_area: str

    # Platform-specific constraints worth baking into every prompt for
    # this channel (hook timing, text-overlay rules, caption length, etc.)
    platform_notes: str

    # Is this a mobile-first channel? True for every digital channel,
    # False for print (postcard). Print assets still render at portrait
    # but carry different composition rules.
    is_mobile_first: bool = True

    # Max recommended render count per script beat — some channels only
    # want a hero shot, others (carousel) want a set.
    beats_to_render: int = 1

    def display(self) -> str:
        m = "mobile-first" if self.is_mobile_first else "print"
        return (
            f"{self.label} [{self.id}] — target {self.target_aspect}, "
            f"render {self.render_aspect}, {m}."
        )


# -- The registry --------------------------------------------------------

CHANNELS: tuple[Channel, ...] = (
    Channel(
        id="youtube_short",
        label="YouTube Shorts",
        target_aspect="9:16",
        render_aspect="9:16",
        safe_area=(
            "Subject fills the center 70% of frame. Keep the top 8% and "
            "bottom 16% clear — YouTube chrome (title, avatar, CTA) lives there."
        ),
        platform_notes=(
            "Hook in the first 1.5 seconds. Vertical only. On-image text "
            "is discouraged — use VO + captions track instead."
        ),
    ),
    Channel(
        id="ig_reel",
        label="Instagram Reels",
        target_aspect="9:16",
        render_aspect="9:16",
        safe_area=(
            "Subject fills the center 66% of frame. Keep top 14% and "
            "bottom 25% clear — username, caption, and CTA live there."
        ),
        platform_notes=(
            "Hook in the first 1 second. Captions and face-lift text are OK "
            "if legible at 5% screen height."
        ),
    ),
    Channel(
        id="ig_story",
        label="Instagram Stories",
        target_aspect="9:16",
        render_aspect="9:16",
        safe_area=(
            "Subject in center 50% of frame. Avoid the top 14% (profile row) "
            "and bottom 14% (reply bar)."
        ),
        platform_notes=(
            "Ephemeral. One thought per story. Sticker-friendly: leave "
            "negative space for a poll or question sticker over the image."
        ),
    ),
    Channel(
        id="tiktok",
        label="TikTok",
        target_aspect="9:16",
        render_aspect="9:16",
        safe_area=(
            "Subject fills the center 65% of frame. Bottom 20% belongs to "
            "the caption and share rail."
        ),
        platform_notes=(
            "Native-feeling, not polished-feeling. Slight grain and handheld "
            "energy outperform stock-clean imagery on this platform."
        ),
    ),
    Channel(
        id="ig_feed",
        label="Instagram Feed post",
        # Platform target is 4:5 (the ideal portrait feed ratio).
        # Imagen can't do 4:5 natively, so we render 3:4 and crop.
        target_aspect="4:5",
        render_aspect="3:4",
        safe_area=(
            "Keep subject inside the center vertical band. A 4:5 crop of "
            "a 3:4 render trims roughly 6% from top and bottom — do not "
            "place text or eyes within that margin."
        ),
        platform_notes=(
            "Seen in-feed with the caption collapsed to 2 lines. The image "
            "carries the hook alone; the caption is support."
        ),
        beats_to_render=1,
    ),
    Channel(
        id="ig_carousel",
        label="Instagram Carousel",
        target_aspect="4:5",
        render_aspect="3:4",
        safe_area=(
            "Every slide reads on its own AND as a sequence. Keep a "
            "consistent focal position across slides for thumb-swipe rhythm."
        ),
        platform_notes=(
            "Slide 1 is the hook (80% of stop-the-scroll). Slides 2-4 earn "
            "the save. Slide 5+ is the CTA."
        ),
        beats_to_render=5,
    ),
    Channel(
        id="linkedin_post",
        label="LinkedIn post",
        target_aspect="4:5",
        render_aspect="3:4",
        safe_area=(
            "Center subject. LinkedIn renders portrait images at a smaller "
            "on-phone height — the eye / focal point must be big."
        ),
        platform_notes=(
            "Professional register. Copy is longer and the image is the "
            "thumbnail, not the hero. Still mobile-first: 60%+ of LinkedIn "
            "traffic is mobile."
        ),
    ),
    Channel(
        id="blog_hero",
        label="Blog hero image",
        target_aspect="16:9",
        render_aspect="9:16",
        safe_area=(
            "Compose for BOTH crops. Center a focal subject that survives "
            "a 16:9 desktop crop AND a 9:16 mobile-first crop. The 9:16 "
            "render is the default on mareheadspa.com; the 16:9 is the "
            "OG/Twitter card."
        ),
        platform_notes=(
            "60% of mareheadspa.com traffic is mobile. The hero is viewed "
            "portrait-first. A 16:9 crop is served only to desktop and "
            "to social preview cards."
        ),
    ),
    Channel(
        id="email_hero",
        label="Email hero image",
        target_aspect="4:5",
        render_aspect="3:4",
        safe_area=(
            "Gmail / iOS Mail render a ~600px-wide column. Subject must "
            "read at that width. Text on the image must exceed 32px."
        ),
        platform_notes=(
            "Must decode under a slow connection AND with images-off "
            "(alt text matters). No tiny typography. No faces smaller "
            "than a fingertip."
        ),
    ),
    Channel(
        id="postcard_front",
        label="Direct-mail postcard (front)",
        target_aspect="5:7",
        render_aspect="3:4",
        safe_area=(
            "Full bleed. Keep focal subject inside the center 70%; the outer "
            "5% can be trimmed by the printer. Back of card carries all copy."
        ),
        platform_notes=(
            "Physical print, NOT mobile-first. Designed for tactility in the "
            "hand. Paper stock + foil + finish matter more than the image."
        ),
        is_mobile_first=False,
    ),
)


_CHANNEL_INDEX: dict[str, Channel] = {c.id: c for c in CHANNELS}


def get_channel(channel_id: str) -> Channel:
    """Look up a Channel by id. Raises KeyError with a useful hint."""
    try:
        return _CHANNEL_INDEX[channel_id]
    except KeyError:
        known = ", ".join(sorted(_CHANNEL_INDEX))
        raise KeyError(
            f"Unknown channel '{channel_id}'. Known channels: {known}."
        ) from None


def list_channels(*, mobile_first_only: bool = False) -> list[Channel]:
    if mobile_first_only:
        return [c for c in CHANNELS if c.is_mobile_first]
    return list(CHANNELS)


# Default: any script without a declared channel is treated as a Short.
DEFAULT_CHANNEL_ID = "youtube_short"


def default_channel() -> Channel:
    return get_channel(DEFAULT_CHANNEL_ID)


# -- Prompt blocks -------------------------------------------------------


def channel_prompt_block(channel: Channel) -> str:
    """Render a channel spec as a prompt-ready block for the image-prompt generator."""
    return (
        f"CHANNEL SPEC — {channel.label} (id: {channel.id})\n"
        f"- Target aspect on platform: {channel.target_aspect}\n"
        f"- Render aspect (Imagen 4 native): {channel.render_aspect}\n"
        f"- Safe area: {channel.safe_area}\n"
        f"- Platform notes: {channel.platform_notes}\n"
        f"- Mobile-first: {'yes' if channel.is_mobile_first else 'no — physical print'}\n"
        f"- Beats to render: {channel.beats_to_render}"
    )


def channels_summary(channels: Iterable[Channel] | None = None) -> str:
    """Human-readable summary of all (or selected) channels."""
    channels = list(channels) if channels is not None else list(CHANNELS)
    return "\n".join(f"- {c.display()}" for c in channels)


__all__ = [
    "CHANNELS",
    "Channel",
    "DEFAULT_CHANNEL_ID",
    "IMAGEN_NATIVE_ASPECTS",
    "MOBILE_FIRST_DOCTRINE",
    "channel_prompt_block",
    "channels_summary",
    "default_channel",
    "get_channel",
    "list_channels",
]
