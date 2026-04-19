"""Fan-out pipeline: one brief -> a full content package.

This is the 50x lever. Give the pipeline one `ContentBrief` and it returns a
YouTube Short + an IG caption + a LinkedIn post + a blog draft, all anchored
in the same narrative, all on-brand, all persisted to `artifacts/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mare.config import Settings
from mare.content.blogs import BlogDraft, generate_blog
from mare.content.brief import ContentBrief
from mare.content.shorts import ShortScript, generate_short_script
from mare.content.social import SocialPost, generate_social_caption
from mare.gemini_client import GeminiClient


@dataclass
class ContentPackage:
    brief: ContentBrief
    short: ShortScript
    blog: BlogDraft
    instagram: SocialPost
    linkedin: SocialPost
    output_dir: Path


class ContentPipeline:
    def __init__(self, client: GeminiClient | None = None, settings: Settings | None = None):
        self._settings = settings or Settings.load()
        self._client = client or GeminiClient(self._settings)

    def run(self, brief: ContentBrief) -> ContentPackage:
        short = generate_short_script(brief, self._client)
        blog = generate_blog(brief, self._client)
        ig = generate_social_caption(brief, "instagram", self._client)
        li = generate_social_caption(brief, "linkedin", self._client)

        slug = blog.slug or _slugify(brief.topic)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = self._settings.artifact_dir / "content" / f"{stamp}-{slug}"
        out_dir.mkdir(parents=True, exist_ok=True)

        (out_dir / "brief.json").write_text(brief.model_dump_json(indent=2))
        (out_dir / "short.md").write_text(short.to_markdown())
        (out_dir / "blog.md").write_text(blog.to_markdown())
        (out_dir / "instagram.md").write_text(ig.to_markdown())
        (out_dir / "linkedin.md").write_text(li.to_markdown())

        return ContentPackage(
            brief=brief,
            short=short,
            blog=blog,
            instagram=ig,
            linkedin=li,
            output_dir=out_dir,
        )


def _slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:60] or "untitled"
