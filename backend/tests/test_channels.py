"""Tests for mare.content.channels — the mobile-first distribution matrix.

These are pure-data tests. No Gemini calls, safe in CI.
"""

from __future__ import annotations

import pytest

from mare.brand.identity import MOBILE_FIRST_DOCTRINE as BRAND_DOCTRINE
from mare.content import channels
from mare.content.channels import (
    CHANNELS,
    DEFAULT_CHANNEL_ID,
    IMAGEN_NATIVE_ASPECTS,
    MOBILE_FIRST_DOCTRINE,
    Channel,
    channel_prompt_block,
    default_channel,
    get_channel,
    list_channels,
)


def test_every_channel_has_imagen_native_render_aspect():
    """Imagen 4 only supports 1:1, 3:4, 4:3, 9:16, 16:9. If we ever add a
    channel whose render_aspect isn't in that set, the renderer will blow up
    at runtime — catch it here instead."""
    for c in CHANNELS:
        assert c.render_aspect in IMAGEN_NATIVE_ASPECTS, (
            f"Channel '{c.id}' render_aspect={c.render_aspect} is not Imagen-native. "
            f"Use one of {IMAGEN_NATIVE_ASPECTS}."
        )


def test_every_channel_has_unique_id():
    ids = [c.id for c in CHANNELS]
    assert len(ids) == len(set(ids)), f"Duplicate channel ids: {ids}"


def test_every_channel_has_non_empty_fields():
    for c in CHANNELS:
        assert c.id and c.label
        assert c.target_aspect and c.render_aspect
        assert c.safe_area and c.platform_notes
        assert c.beats_to_render >= 1


def test_default_channel_is_youtube_short():
    assert DEFAULT_CHANNEL_ID == "youtube_short"
    assert default_channel().id == DEFAULT_CHANNEL_ID
    assert default_channel().is_mobile_first is True


def test_mobile_first_channels_outnumber_print():
    mobile = [c for c in CHANNELS if c.is_mobile_first]
    print_ = [c for c in CHANNELS if not c.is_mobile_first]
    assert len(mobile) > len(print_), (
        "Mobile-first is a doctrine. If print overtakes digital, "
        "something's off."
    )


def test_get_channel_lookup_and_error():
    assert get_channel("youtube_short").label == "YouTube Shorts"
    with pytest.raises(KeyError) as exc:
        get_channel("snapchat")
    # Error should list known channels so the caller knows what's valid.
    assert "youtube_short" in str(exc.value)


def test_list_channels_filters_mobile_only():
    all_channels = list_channels()
    mobile_only = list_channels(mobile_first_only=True)
    assert len(all_channels) > len(mobile_only)
    assert all(c.is_mobile_first for c in mobile_only)


def test_channel_prompt_block_contains_spec():
    ch = get_channel("ig_feed")
    block = channel_prompt_block(ch)
    assert "Instagram Feed post" in block
    assert "4:5" in block  # target aspect
    assert "3:4" in block  # render aspect
    assert "Mobile-first: yes" in block


def test_channel_prompt_block_marks_print_as_not_mobile_first():
    ch = get_channel("postcard_front")
    block = channel_prompt_block(ch)
    assert "Mobile-first: no" in block


def test_ig_reel_and_tiktok_and_shorts_all_native_nine_sixteen():
    """All vertical-video channels should render native 9:16 — no crop, no loss."""
    for channel_id in ("youtube_short", "ig_reel", "ig_story", "tiktok"):
        ch = get_channel(channel_id)
        assert ch.target_aspect == "9:16"
        assert ch.render_aspect == "9:16"


def test_mobile_first_doctrine_is_reexported_from_brand():
    """Doctrine lives in mare.brand.identity; channels re-exports it so
    content generators can depend on one symbol."""
    assert MOBILE_FIRST_DOCTRINE is BRAND_DOCTRINE


def test_channel_dataclass_is_hashable():
    """Channel is frozen, so it should be safe to use as a dict key."""
    ch = get_channel("blog_hero")
    assert hash(ch)
    assert isinstance(ch, Channel)


def test_channels_summary_includes_every_channel():
    summary = channels.channels_summary()
    for c in CHANNELS:
        assert c.id in summary
