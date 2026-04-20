"""MaRe brand voice — the single source of truth for how MaRe sounds.

Every generator pulls from this module so brand drift is structurally
impossible: change the rules here, and every Short, blog, and outreach email
inherits the change automatically.
"""

from mare.brand.ai_red_flags import AI_ISH_PHRASES, AI_ISH_WORDS, STRUCTURAL_TELLS
from mare.brand.identity import (
    BRAND_ESSENCE,
    BRAND_EVOKES,
    BROWN_BASE,
    BROWN_SCALE,
    ICON_CATEGORIES,
    LOGO_DONTS,
    LOGO_SYSTEM,
    MOBILE_FIRST_DOCTRINE,
    PERSONA,
    PRIMARY_COLORS,
    SECONDARY_COLORS,
    TONE_MATRIX,
    TYPOGRAPHY,
    WATER_BASE,
    WATER_SCALE,
    identity_prompt_block,
    palette_prompt_block,
    tone_matrix_block,
    visual_identity_prompt_block,
)
from mare.brand.products import (
    MARE_PARTNERSHIP,
    MARE_POSITIONING_LINE,
    MARE_PRODUCT_LINES,
    MARE_PROOF_POINTS,
    MARE_TAGLINE,
    canonical_product_names,
    product_brief_for_prompt,
)
from mare.brand.salon_lingo import SALON_LINGO
from mare.brand.vocabulary import (
    PILLAR_VOCABULARY,
    VOCABULARY_PROMPT_GUIDANCE,
    CoverageReport,
    evaluate_coverage,
)
from mare.brand.voice import BRAND_SYSTEM_PROMPT, VOICE_RULES

__all__ = [
    "AI_ISH_PHRASES",
    "AI_ISH_WORDS",
    "BRAND_ESSENCE",
    "BRAND_EVOKES",
    "BRAND_SYSTEM_PROMPT",
    "BROWN_BASE",
    "BROWN_SCALE",
    "CoverageReport",
    "ICON_CATEGORIES",
    "LOGO_DONTS",
    "LOGO_SYSTEM",
    "MARE_PARTNERSHIP",
    "MARE_POSITIONING_LINE",
    "MARE_PRODUCT_LINES",
    "MARE_PROOF_POINTS",
    "MARE_TAGLINE",
    "MOBILE_FIRST_DOCTRINE",
    "PERSONA",
    "PILLAR_VOCABULARY",
    "PRIMARY_COLORS",
    "SALON_LINGO",
    "SECONDARY_COLORS",
    "STRUCTURAL_TELLS",
    "TONE_MATRIX",
    "TYPOGRAPHY",
    "VOCABULARY_PROMPT_GUIDANCE",
    "VOICE_RULES",
    "WATER_BASE",
    "WATER_SCALE",
    "canonical_product_names",
    "evaluate_coverage",
    "identity_prompt_block",
    "palette_prompt_block",
    "product_brief_for_prompt",
    "tone_matrix_block",
    "visual_identity_prompt_block",
]
