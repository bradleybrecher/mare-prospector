"""MaRe brand voice — the single source of truth for how MaRe sounds.

Every generator pulls from this module so brand drift is structurally
impossible: change the rules here, and every Short, blog, and outreach email
inherits the change automatically.
"""

from mare.brand.ai_red_flags import AI_ISH_PHRASES, AI_ISH_WORDS, STRUCTURAL_TELLS
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
    "BRAND_SYSTEM_PROMPT",
    "CoverageReport",
    "MARE_PARTNERSHIP",
    "MARE_POSITIONING_LINE",
    "MARE_PRODUCT_LINES",
    "MARE_PROOF_POINTS",
    "MARE_TAGLINE",
    "PILLAR_VOCABULARY",
    "SALON_LINGO",
    "STRUCTURAL_TELLS",
    "VOCABULARY_PROMPT_GUIDANCE",
    "VOICE_RULES",
    "canonical_product_names",
    "evaluate_coverage",
    "product_brief_for_prompt",
]
