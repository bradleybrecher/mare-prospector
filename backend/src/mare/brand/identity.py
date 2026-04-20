"""Official MaRe brand identity — single source of truth.

Transcribed verbatim from the MaRe Brand Kit PDFs in
`Brand Kit/MaRe Brand Guidelines.pdf` and `Brand Kit/Copy of 🎨 Style Guide.pdf`.

If the brand team ships a revised guideline, update this module and every
downstream generator (voice, image prompts, postcard art direction) inherits
the change automatically.

Never mutate these constants at runtime. They are the floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


BRAND_ESSENCE: str = (
    "MaRe, it's the only system that fuses AI-powered scalp diagnostics, "
    "multisensory therapy, and European wellness rituals into one personalized "
    "experience."
)
"""The official brand definition sentence (page 1 of the Brand Guidelines)."""

BRAND_EVOKES: tuple[str, ...] = ("relaxation", "trust", "professionalism")
"""What the brand is officially meant to evoke."""

PERSONA: str = "Educated person, informed, prepared."
"""The persona MaRe speaks to and as (page 10, Brand Guidelines)."""


# Tone of Voice — from the Content x Language matrix on page 10.
# Each trait is paired with the language descriptor the brand kit supplies.
# Ordering preserved from the source document.
TONE_MATRIX: tuple[tuple[str, str], ...] = (
    ("Innovative", "Stylish, intentional. 'Look good, feel good.'"),
    ("Sophisticated", "Adaptable, all-round, resourceful."),
    ("Versatile", "Honest and reliable."),
    ("Trustworthy", "Eloquent and likeable."),
    ("Refined", "Smart and factual."),
    ("Knowledgeable", "What you read is what you get."),
    ("Transparent", "Industry terminology, concise."),
    ("Professional", "Easy to understand, welcoming."),
    ("Simple", "Promotes two-way communication."),
    ("Engaging", "Inspirational and motivational."),
    ("Encouraging", "Shares knowledge and resources."),
    ("Educational", "Teaches without talking down."),
)


# -- Logo system ---------------------------------------------------------

@dataclass(frozen=True)
class LogoVariant:
    name: str
    usage: str


LOGO_SYSTEM: tuple[LogoVariant, ...] = (
    LogoVariant(
        name="Primary logo",
        usage="MaRe product packaging. Rendered on the lighter side of the brand gradient.",
    ),
    LogoVariant(
        name="Secondary logo",
        usage="Business presentations, on 'Light' (#E2E2DE) backgrounds.",
    ),
    LogoVariant(
        name="Submark",
        usage="Business presentations. Used at 10% opacity as a subtle watermark.",
    ),
)

LOGO_DONTS: tuple[str, ...] = (
    "Do NOT change the pictorial mark's orientation.",
    "Do NOT stretch the logo in one direction.",
    "Do NOT rotate the logo's view.",
    "Do NOT change the logo's size without keeping proportions.",
)


# -- Color palette -------------------------------------------------------
# Hex codes transcribed from the official palette. The "Primary" and
# "Secondary" groupings are the brand-kit hero set; the brown_scale and
# water_scale are the full tonal ramps from the Style Guide.

PRIMARY_COLORS: Mapping[str, str] = MappingProxyType(
    {
        "Light": "#E2E2DE",
        "Key": "#296167",
        "Extra Dark": "#2A2420",
        "Dark": "#3B3632",
        "Brand Brown": "#653D24",
        "Clear White": "#FFFFFF",
    }
)

SECONDARY_COLORS: Mapping[str, str] = MappingProxyType(
    {
        "Water-50": "#E4ECED",
        "Brown-200": "#C1B1A7",
        "Water-300": "#7C9FA3",
        "Water-900": "#0C1D1F",
    }
)

BROWN_SCALE: Mapping[str, str] = MappingProxyType(
    {
        "brown-50": "#F0ECE9",
        "brown-100": "#E0D8D3",
        "brown-200": "#C1B1A7",
        "brown-300": "#A38B7C",
        "brown-400": "#846450",
        "brown-500": "#653D24",  # base
        "brown-600": "#51311D",
        "brown-700": "#3D2516",
        "brown-800": "#28180E",
        "brown-900": "#1E120B",
    }
)

WATER_SCALE: Mapping[str, str] = MappingProxyType(
    {
        "water-50": "#E4ECED",
        "water-100": "#CFDDDE",
        "water-200": "#A6BEC0",
        "water-300": "#7C9FA3",
        "water-400": "#538085",
        "water-500": "#296167",  # base
        "water-600": "#214E52",
        "water-700": "#193A3E",
        "water-800": "#102729",
        "water-900": "#0C1D1F",
    }
)

BROWN_BASE: str = BROWN_SCALE["brown-500"]
WATER_BASE: str = WATER_SCALE["water-500"]


# -- Typography ----------------------------------------------------------

@dataclass(frozen=True)
class TypefaceRole:
    family: str
    role: str
    weights: tuple[str, ...]
    usage: str


TYPOGRAPHY: tuple[TypefaceRole, ...] = (
    TypefaceRole(
        family="Playfair Display",
        role="Principal",
        weights=("Regular",),
        usage="Titles only. Editorial headlines, hero moments, pull quotes.",
    ),
    TypefaceRole(
        family="Manrope",
        role="Complementary / Headings & UI",
        weights=("Light", "Regular", "Bold"),
        usage=(
            "Manrope Light for display headings (line-height 112%, tracking -4%). "
            "Manrope Regular for body (line-height 136%, tracking -4%). "
            "Manrope Bold for headers & footers / labels."
        ),
    ),
    TypefaceRole(
        family="Albert Sans",
        role="Body (alternate)",
        weights=("Regular",),
        usage="Long-form body copy where Manrope is unavailable.",
    ),
)


# -- Iconography vocabulary ---------------------------------------------

# -- Distribution principle (mobile-first) -------------------------------

MOBILE_FIRST_DOCTRINE: str = (
    "MOBILE-FIRST DOCTRINE\n"
    "MaRe content is consumed on a phone first, a desktop second, a printed "
    "piece third. Every asset is framed, cropped, and written for a thumb-held "
    "screen. That means: the hook lands in the first 12 words or 1.5 seconds; "
    "the focal subject sits inside the center 66% of the frame; on-image text "
    "(if any) is legible at 5% of screen height; and caption copy is scannable "
    "in two lines before the 'more' fold. Desktop and print are cascaded down "
    "from a mobile master, never the other way around."
)


ICON_CATEGORIES: tuple[str, ...] = (
    "Natural Radiance",
    "Verified / Tested",
    "Wavelengths",
    "LinkedIn",
    "Instagram",
    "Email",
    "Organization / Systems / Perks",
    "Products / Sales / Shopping",
    "Verified / Tested 2.0",
    "Scalp Health",
    "Loading / Processing",
    "Science Verified",
    "Approved / Certified",
    "Global",
    "Check Mark / Completed",
    "Location",
    "Magnetic / Client Acquisition / Community",
    "Profit / Benefits / Revenue",
    "Engagement / Positive Feedback",
    "Business Growth",
    "Science Verified 2.0",
    "Growth / Mindset",
    "Network",
)


# -- Prompt block helpers ------------------------------------------------

def tone_matrix_block() -> str:
    """Render the 12-trait tone matrix for inclusion in system prompts."""
    lines = [f"- {trait}: {descriptor}" for trait, descriptor in TONE_MATRIX]
    return "\n".join(lines)


def palette_prompt_block() -> str:
    """Hex-value color palette for art-direction prompts.

    Returned as a plain-prose block rather than a table; image models consume
    prose better and copywriters need to scan it quickly.
    """
    primary_line = ", ".join(f"{name} {hexv}" for name, hexv in PRIMARY_COLORS.items())
    secondary_line = ", ".join(f"{name} {hexv}" for name, hexv in SECONDARY_COLORS.items())
    return (
        f"Primary palette: {primary_line}.\n"
        f"Secondary palette: {secondary_line}.\n"
        f"Brown tonal ramp (base brown-500 = {BROWN_BASE}): "
        f"{', '.join(f'{k} {v}' for k, v in BROWN_SCALE.items())}.\n"
        f"Water tonal ramp (base water-500 = {WATER_BASE}): "
        f"{', '.join(f'{k} {v}' for k, v in WATER_SCALE.items())}."
    )


def typography_prompt_block() -> str:
    lines = []
    for tf in TYPOGRAPHY:
        weights = "/".join(tf.weights)
        lines.append(f"- {tf.family} ({weights}) — {tf.role}. {tf.usage}")
    return "\n".join(lines)


def logo_prompt_block() -> str:
    variants = "\n".join(f"- {v.name}: {v.usage}" for v in LOGO_SYSTEM)
    donts = "\n".join(f"- {rule}" for rule in LOGO_DONTS)
    return f"LOGO VARIANTS\n{variants}\n\nLOGO DO-NOTS\n{donts}"


def identity_prompt_block() -> str:
    """The block that gets injected into BRAND_SYSTEM_PROMPT.

    Contains the official brand essence, persona, and tone-of-voice matrix.
    Logo rules and raw palette live in the visual-identity block instead
    (they matter for image generation, not copywriting).
    """
    tone_block = tone_matrix_block()
    evokes = ", ".join(BRAND_EVOKES)
    return (
        "OFFICIAL BRAND IDENTITY (from the MaRe Brand Kit)\n"
        f"{BRAND_ESSENCE}\n"
        f"The brand is meant to evoke: {evokes}.\n\n"
        f"PERSONA\n{PERSONA}\n"
        "MaRe speaks to this reader and from this reader's shoes: educated, "
        "informed, already prepared. Never talk down, never over-explain.\n\n"
        "TONE OF VOICE (from the Brand Kit Content x Language matrix — keep a "
        "blend of these traits alive in every piece):\n"
        f"{tone_block}"
    )


def visual_identity_prompt_block() -> str:
    """The block used in image-prompt art direction.

    Carries the real hex palette, typography rules, and logo usage — the
    facts an image model or a designer needs in order to ship on-brand work.
    """
    return (
        "MaRe official visual identity (from the Brand Kit):\n\n"
        f"COLOR PALETTE\n{palette_prompt_block()}\n\n"
        f"TYPOGRAPHY\n{typography_prompt_block()}\n\n"
        f"{logo_prompt_block()}"
    )


__all__ = [
    "BRAND_ESSENCE",
    "BRAND_EVOKES",
    "BROWN_BASE",
    "BROWN_SCALE",
    "ICON_CATEGORIES",
    "LOGO_DONTS",
    "LOGO_SYSTEM",
    "LogoVariant",
    "MOBILE_FIRST_DOCTRINE",
    "PERSONA",
    "PRIMARY_COLORS",
    "SECONDARY_COLORS",
    "TONE_MATRIX",
    "TYPOGRAPHY",
    "TypefaceRole",
    "WATER_BASE",
    "WATER_SCALE",
    "identity_prompt_block",
    "logo_prompt_block",
    "palette_prompt_block",
    "tone_matrix_block",
    "typography_prompt_block",
    "visual_identity_prompt_block",
]
