"""The MaRe product suite, as published on https://mareheadspa.com.

The model MUST use these exact names. No invented product names, no
"MaRe Ultra" or "MaRe Pro" etc. If unsure, refer to this file.
"""

from __future__ import annotations

MARE_TAGLINE = "The World's First All-in-One Head Spa System"
MARE_POSITIONING_LINE = "Your Head. Your Way. Science Supported."

MARE_PARTNERSHIP = (
    "Exclusively partnered with Philip Martin's — the Italian world leader in luxury organic cosmetics. "
    "The 'MaRe x Philip Martin's' line is tailor-made for MaRe rituals."
)

MARE_FOUNDERS = {
    "rebecca": "Co-Founder of MaRe (appears on-site as the brand's face).",
}

MARE_PROOF_POINTS: tuple[str, ...] = (
    "Developed with leading trichologists, professors, and researchers (\"Rooted in Research\").",
    "Patented innovation across red & blue light, steam, waterfall, and laser technologies.",
    "AI-personalized rituals powered by the MaRe Eye diagnostic system.",
    "Italian organic formulations via the MaRe x Philip Martin's exclusive line.",
    "Miami-based, nationwide expansion footprint.",
)

MARE_AUDIENCES: tuple[str, ...] = (
    "Salons, spas, clinics, hotels, and wellness centers (B2B partners).",
    "Wellness enthusiasts who want to take control of their scalp and hair health (D2C).",
)

# The four product pillars, as the website organizes them.
MARE_PRODUCT_LINES: dict[str, dict] = {
    "MaRe Capsule": {
        "tagline": "The first state-of-the-art massage chair designed exclusively for head spas.",
        "features": [
            "Targeted Massage Mode — head, neck, shoulder sequences that relieve tension and improve circulation.",
            "Zero-gravity Recline — aligns the body for a weightless sensation.",
            "Ergonomic Pedestal Sink — integrated basin for smooth wash-to-treatment transitions.",
            "Built-in Steam Therapy — opens pores, refreshes scalp, boosts product absorption.",
        ],
    },
    "MaRe Eye": {
        "tagline": "AI-driven scalp and hair diagnostics that boost treatment precision and retail sales.",
        "features": [
            "High-resolution scalp imaging.",
            "AI-generated reports with customized insights.",
            "Protocol and product recommendations tied to each report.",
            "Integrated client experience — saves visit history, shareable with clients.",
        ],
    },
    "MaRe x Philip Martin's": {
        "tagline": "Organic Italian cosmetics formulated to complement MaRe rituals.",
        "features": [
            "Organic formula — clean, natural ingredients.",
            "Scalp-focused blends that nourish, balance, and restore.",
            "Made in Italy to Philip Martin's quality standards.",
            "Tailor-made for the MaRe system; not sold outside it.",
        ],
    },
    "MaRe Tools": {
        "tagline": "Custom-designed tools that support every step of the MaRe experience.",
        "features": [
            "MaRe Wind — ionic dryer engineered for steady, heat-protective airflow.",
            "MaRe Pure / MaRe Silk — brush series for treatment application and daily use.",
            "MaRe Red / MaRe Halo / MaRe Mask — red-light rejuvenation for face and scalp.",
            "MaRe Whisk / MaRe Pulse — handheld massagers that boost circulation and absorption.",
        ],
    },
}


def canonical_product_names() -> list[str]:
    """Flat list of every valid MaRe product name, used for validation."""
    names: list[str] = list(MARE_PRODUCT_LINES.keys())
    for line in MARE_PRODUCT_LINES.values():
        for feature in line["features"]:
            # Features lead with the product name, e.g. "MaRe Wind — ..."
            head = feature.split("—")[0].strip()
            if head.startswith("MaRe "):
                # Handle "MaRe Pure / MaRe Silk" style entries.
                for token in head.split("/"):
                    clean = token.strip()
                    if clean and clean not in names:
                        names.append(clean)
    return names


def product_brief_for_prompt() -> str:
    """Compact block suitable for dropping into a system prompt."""
    lines = [
        f"MaRe tagline: {MARE_TAGLINE}",
        f"Positioning line: {MARE_POSITIONING_LINE}",
        f"Partnership: {MARE_PARTNERSHIP}",
        "",
        "Proof points (use sparingly, one per piece of copy):",
        *(f"- {p}" for p in MARE_PROOF_POINTS),
        "",
        "Audiences:",
        *(f"- {a}" for a in MARE_AUDIENCES),
        "",
        "Product lines and exact, canonical names (never invent new MaRe product names):",
    ]
    for line_name, data in MARE_PRODUCT_LINES.items():
        lines.append(f"- {line_name}: {data['tagline']}")
        for feat in data["features"]:
            lines.append(f"    • {feat}")
    return "\n".join(lines)
