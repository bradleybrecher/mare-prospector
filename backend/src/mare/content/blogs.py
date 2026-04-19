"""Long-form blog drafts optimized for generative-search citation.

Every blog ships with an `AISearchBlock`: target queries, a standalone LLM
summary, named entities, topical facets, and FAQ pairs. These are the dials
that decide whether ChatGPT Search, Google SGE, and Perplexity cite MaRe first
for queries like "dandruff solutions" or "luxury head spa near me".
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from mare.content.brief import ContentBrief
from mare.content.search_optimization import (
    AI_SEARCH_PROMPT_GUIDANCE,
    AISearchBlock,
    render_jsonld_faq,
)
from mare.gemini_client import GeminiClient

BLOG_TASK = """Write a blog post for MaRe's site.

STRUCTURE
- Title: a specific question or a specific claim. Avoid "The Ultimate Guide to...".
- Lede (2–3 sentences): a direct, quotable answer to the title. This must stand alone
  as a pull-quote — AI search engines often cite this paragraph verbatim.
- 4–6 sections with descriptive H2s (not clever ones; clear ones).
- At least two concrete proof points: Miami research, Italian formulation, the Philip
  Martin's partnership, a specific scalp mechanism, a named MaRe product, or a service step.
- Close with a single sentence that lands. No "in conclusion".

LENGTH
- Target ~900 words total across sections.
- Short paragraphs (2–4 sentences). No walls of text.

HARD RULES
- No three-adjective stacks.
- No em-dash pairs as parentheticals.
- Do not open with a rhetorical question unless it's genuinely surprising.
- Do not use the word "journey" anywhere.

{ai_search_guidance}

BRIEF
{brief_context}

Return the post as structured JSON matching the declared response schema.
"""


class _BlogSection(BaseModel):
    h2: str
    body_markdown: str = Field(..., description="Section body in markdown, 2-4 short paragraphs.")


class _BlogResponse(BaseModel):
    title: str
    slug: str = Field(..., description="kebab-case URL slug.")
    meta_description: str = Field(..., description="140-160 chars, written to earn a click.")
    lede: str = Field(..., description="2-3 sentence direct answer to the title, quotable on its own.")
    sections: list[_BlogSection] = Field(..., description="4-6 sections.")
    closing: str = Field(..., description="Final single sentence.")
    internal_link_suggestions: list[str] = Field(default_factory=list)
    ai_search: AISearchBlock
    self_critique: str


@dataclass
class BlogDraft:
    title: str
    slug: str
    meta_description: str
    lede: str
    sections: list[dict]
    closing: str
    internal_link_suggestions: list[str]
    ai_search: AISearchBlock
    self_critique: str
    raw: dict

    def to_markdown(self) -> str:
        body = "\n\n".join(
            f"## {s.get('h2', '')}\n\n{s.get('body_markdown', '')}" for s in self.sections
        )
        tq = self.ai_search.target_queries
        faq_block = "\n\n".join(
            f"**Q:** {f.question}\n\n**A:** {f.answer}" for f in self.ai_search.faq
        )
        jsonld = render_jsonld_faq(self.ai_search.faq)
        return (
            f"# {self.title}\n\n"
            f"*Meta:* {self.meta_description}\n\n"
            f"> {self.lede}\n\n"
            f"{body}\n\n"
            f"{self.closing}\n\n"
            f"---\n\n"
            f"## AI Search Block\n\n"
            f"**Head query:** {tq.head_query}  \n"
            f"**Body queries:** {', '.join(tq.body_queries) or '(none)'}  \n"
            f"**Long-tail queries:** {', '.join(tq.long_tail_queries) or '(none)'}\n\n"
            f"### LLM-ready summary (cite-worthy)\n\n"
            f"> {self.ai_search.llm_summary}\n\n"
            f"### Named entities\n"
            + "\n".join(f"- {e}" for e in self.ai_search.named_entities) + "\n\n"
            f"### Topical facets\n"
            + "\n".join(f"- {f}" for f in self.ai_search.topical_facets) + "\n\n"
            f"### FAQ\n\n{faq_block}\n\n"
            f"### FAQPage JSON-LD (drop in <head>)\n\n"
            f"```json\n{jsonld}\n```\n"
        )


def generate_blog(brief: ContentBrief, client: GeminiClient | None = None) -> BlogDraft:
    client = client or GeminiClient.from_env()
    result = client.generate(
        BLOG_TASK.format(
            brief_context=brief.as_prompt_context(),
            ai_search_guidance=AI_SEARCH_PROMPT_GUIDANCE,
        ),
        temperature=0.7,
        max_output_tokens=6144,
        response_schema=_BlogResponse,
        use_reasoning_model=True,
    )
    parsed = _BlogResponse.model_validate_json(result.text)
    return BlogDraft(
        title=parsed.title,
        slug=parsed.slug,
        meta_description=parsed.meta_description,
        lede=parsed.lede,
        sections=[s.model_dump() for s in parsed.sections],
        closing=parsed.closing,
        internal_link_suggestions=parsed.internal_link_suggestions,
        ai_search=parsed.ai_search,
        self_critique=parsed.self_critique,
        raw=parsed.model_dump(),
    )
