"""Typed input model for a salon prospect.

Kept intentionally narrow. The Pillar 1 (Revenue-Verified Prospecting) system —
when built — will populate these fields from a data source. For now they are
filled manually via the CLI or from a CSV.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SalonProspect(BaseModel):
    """A single salon we want to reach."""

    salon_name: str = Field(..., description="Trading name of the salon.")
    owner_name: str | None = Field(None, description="First name of the decision-maker, if known.")
    city: str = Field(..., description="City where the salon operates.")
    state: str | None = None

    website: str | None = None
    instagram_handle: str | None = None

    estimated_annual_revenue_usd: int | None = Field(
        None,
        description="Best-available revenue signal. MaRe's floor is ~$1M/yr.",
    )
    service_specialties: list[str] = Field(
        default_factory=list,
        description="e.g. ['color correction', 'extensions', 'scalp treatments'].",
    )
    notable_details: list[str] = Field(
        default_factory=list,
        description=(
            "Non-generic, owner-flattering observations we want woven into the copy. "
            "e.g. 'Featured in Allure 2024', 'Known for their Aveda bar'. "
            "The personalizer uses these to avoid generic 'I came across your salon' openers."
        ),
    )
    social_highlights: list["SocialHighlight"] = Field(
        default_factory=list,
        description=(
            "Recent, specific social media moments — a reel caption, a before/after, "
            "a press feature. The personalizer uses ONE of these as the hook of "
            "the email or postcard."
        ),
    )

    def as_prompt_context(self) -> str:
        """Render this prospect as a compact context block for a prompt."""
        lines = [
            f"Salon name: {self.salon_name}",
            f"City: {self.city}" + (f", {self.state}" if self.state else ""),
        ]
        if self.owner_name:
            lines.append(f"Owner first name: {self.owner_name}")
        if self.estimated_annual_revenue_usd:
            lines.append(f"Estimated annual revenue: ${self.estimated_annual_revenue_usd:,}")
        if self.website:
            lines.append(f"Website: {self.website}")
        if self.instagram_handle:
            lines.append(f"Instagram: @{self.instagram_handle.lstrip('@')}")
        if self.service_specialties:
            lines.append("Specialties: " + ", ".join(self.service_specialties))
        if self.notable_details:
            lines.append("Notable details (use at most ONE, naturally):")
            lines.extend(f"  - {d}" for d in self.notable_details)
        if self.social_highlights:
            lines.append("Recent social highlights (reference ONE specifically, as a practitioner would):")
            for h in self.social_highlights:
                lines.append(f"  - [{h.platform}] {h.summary}"
                             + (f" (posted {h.posted_when})" if h.posted_when else "")
                             + (f" — URL: {h.url}" if h.url else ""))
        return "\n".join(lines)


class SocialHighlight(BaseModel):
    """A single recent social-media moment we can anchor outreach to.

    Populate manually from the prospect's public feeds for now. A future
    ingestion job will scrape these automatically.
    """

    platform: str = Field(..., description="instagram | tiktok | youtube | press | other")
    summary: str = Field(
        ...,
        description=(
            "One concrete, specific sentence. NOT 'great Instagram presence'. "
            "DO: 'Reel on Nov 14 about her client's 3-hour color correction on a brunette-to-blonde.' "
            "DO: 'Post pinned to top of grid shows their private suite with natural light.'"
        ),
    )
    posted_when: str | None = Field(None, description="Rough recency, e.g. 'last week', 'Nov 2025'.")
    url: str | None = None


SalonProspect.model_rebuild()
