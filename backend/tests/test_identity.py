"""Tests for the MaRe brand-identity module. Offline, safe in CI.

We're not testing copywriting — we're testing that the official brand kit
is transcribed correctly and exposed consistently, so every downstream
generator inherits identical, well-formed facts.
"""

from __future__ import annotations

import re

import pytest

from mare.brand import identity
from mare.brand.voice import BRAND_SYSTEM_PROMPT

HEX_RE = re.compile(r"^#[0-9A-F]{6}$")


def test_brand_essence_is_present():
    assert "AI-powered scalp diagnostics" in identity.BRAND_ESSENCE
    assert "European wellness rituals" in identity.BRAND_ESSENCE


def test_persona_is_single_sentence():
    assert identity.PERSONA.endswith(".")
    assert len(identity.PERSONA.split(".")) <= 3


@pytest.mark.parametrize(
    "palette",
    [
        identity.PRIMARY_COLORS,
        identity.SECONDARY_COLORS,
        identity.BROWN_SCALE,
        identity.WATER_SCALE,
    ],
)
def test_all_hex_codes_are_well_formed(palette):
    assert palette, "palette must not be empty"
    for name, value in palette.items():
        assert isinstance(name, str) and name, name
        assert HEX_RE.match(value), f"{name}={value} is not a valid 6-digit hex"


def test_brown_and_water_scales_are_complete():
    expected = {f"brown-{n}" for n in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)}
    assert set(identity.BROWN_SCALE) == expected
    expected_water = {f"water-{n}" for n in (50, 100, 200, 300, 400, 500, 600, 700, 800, 900)}
    assert set(identity.WATER_SCALE) == expected_water


def test_base_tones_match_named_primary_colors():
    assert identity.BROWN_BASE == identity.PRIMARY_COLORS["Brand Brown"]
    assert identity.WATER_BASE == identity.PRIMARY_COLORS["Key"]


def test_tone_matrix_has_twelve_entries():
    assert len(identity.TONE_MATRIX) == 12
    for trait, descriptor in identity.TONE_MATRIX:
        assert trait and trait[0].isupper(), trait
        # Descriptor must be a real sentence. Allow trailing ' or " after the period
        # for descriptors that close on a quoted phrase.
        assert descriptor.rstrip("\"'").endswith("."), descriptor


def test_logo_system_has_all_three_variants():
    names = {v.name for v in identity.LOGO_SYSTEM}
    assert names == {"Primary logo", "Secondary logo", "Submark"}


def test_typography_includes_playfair_and_manrope():
    families = {tf.family for tf in identity.TYPOGRAPHY}
    assert "Playfair Display" in families
    assert "Manrope" in families


def test_identity_prompt_block_contains_key_facts():
    block = identity.identity_prompt_block()
    assert identity.BRAND_ESSENCE in block
    assert identity.PERSONA in block
    for trait, _ in identity.TONE_MATRIX:
        assert trait in block


def test_visual_identity_prompt_block_carries_real_hex_codes():
    block = identity.visual_identity_prompt_block()
    assert identity.BROWN_BASE in block
    assert identity.WATER_BASE in block
    assert "#FFFFFF" in block
    assert "Playfair Display" in block
    assert "pictorial mark" in block.lower()


def test_brand_system_prompt_embeds_official_identity():
    """The master prompt must carry the brand-kit facts verbatim."""
    assert identity.BRAND_ESSENCE in BRAND_SYSTEM_PROMPT
    assert identity.PERSONA in BRAND_SYSTEM_PROMPT
    for trait, _ in identity.TONE_MATRIX:
        assert trait in BRAND_SYSTEM_PROMPT
