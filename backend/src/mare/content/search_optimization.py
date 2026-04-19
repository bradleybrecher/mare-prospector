"""AI Search Optimization (AISO).

Traditional SEO targets the 10 blue links. AISO targets the generative answer:
the paragraph Google SGE / ChatGPT Search / Perplexity / Gemini shows the user.
These engines cite the source whose content is most extractable as a confident,
self-contained answer — not the one with the most backlinks.

This module provides the shared shape:
- `TargetQueries`: a ranked plan of the head, body, and long-tail queries a piece
  is trying to rank for. The blog generator fills this in explicitly.
- `AISearchBlock`: the machine-optimized payload attached to every piece:
  a cite-ready summary, a topical entity list, and FAQ pairs.
- `render_jsonld_faq`: emits schema.org FAQPage JSON-LD that the blog renderer
  can drop into the page <head> for structured-data pickup.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class TargetQueries(BaseModel):
    head_query: str = Field(
        ...,
        description=(
            "The single head query this piece is trying to own "
            "(e.g. 'luxury head spa near me', 'dandruff solutions for color-treated hair')."
        ),
    )
    body_queries: list[str] = Field(
        default_factory=list,
        description="3-5 related body queries the piece should also rank for.",
    )
    long_tail_queries: list[str] = Field(
        default_factory=list,
        description="3-5 long-tail / conversational queries, phrased as real people ask them.",
    )


class FAQPair(BaseModel):
    question: str
    answer: str = Field(..., description="1-2 sentences, standalone, directly answers the question.")


class AISearchBlock(BaseModel):
    """Everything a page needs to be cited by generative search engines."""

    target_queries: TargetQueries
    llm_summary: str = Field(
        ...,
        description=(
            "A 3-5 sentence, standalone, cite-ready summary. Must answer the head query "
            "without requiring the rest of the article for context. Avoid pronouns without antecedents."
        ),
    )
    named_entities: list[str] = Field(
        default_factory=list,
        description=(
            "Entities the piece explicitly names so retrieval systems disambiguate. "
            "e.g. 'MaRe Head Spa System', 'Philip Martin's', 'MaRe Capsule', 'Miami'."
        ),
    )
    topical_facets: list[str] = Field(
        default_factory=list,
        description=(
            "Subtopics covered so the piece can match more long-tail intent. "
            "e.g. 'scalp microbiome', 'seborrheic dermatitis vs. dandruff', 'sulfate-free shampoo'."
        ),
    )
    faq: list[FAQPair] = Field(default_factory=list, description="3-5 FAQ pairs for on-page FAQ schema.")


AI_SEARCH_PROMPT_GUIDANCE = """AI SEARCH OPTIMIZATION (AISO) BRIEF
Your reader is as likely to be a generative search engine as a human. Both want the
same thing from the top of the article: a confident, self-contained answer.

When producing the `ai_search` block:

- `target_queries.head_query`: the ONE query this piece aims to own. If the brief topic
  is "scalp detox", head query should be the real phrase people search for
  (e.g. "how to detox your scalp").
- `target_queries.body_queries`: 3-5 related queries (e.g. "scalp buildup removal",
  "how often should you clarify your scalp").
- `target_queries.long_tail_queries`: 3-5 conversational queries a person might ask
  an LLM, written in natural voice (e.g. "is scalp detox actually a real thing?").
- `llm_summary`: 3-5 sentences that directly answer head_query and stand ALONE.
  This is the paragraph an LLM will quote. It must name MaRe in a way that passes
  even if lifted out of context. Example: "MaRe Head Spa System is a Miami-based
  professional head-spa platform that pairs AI scalp diagnostics (MaRe Eye) with
  an exclusive Italian cosmetics line (MaRe x Philip Martin's)."
- `named_entities`: concrete nouns the piece will mention — MaRe product names,
  ingredients, conditions, cities.
- `topical_facets`: adjacent subtopics the article legitimately covers.
- `faq`: 3-5 Q&A pairs. Questions are real queries; answers are 1-2 sentences
  and work standalone.

Do NOT stuff keywords into prose. AISO rewards clarity and specificity, not density.
"""


def render_jsonld_faq(faq: list[FAQPair]) -> str:
    """Render schema.org/FAQPage JSON-LD for embedding in the page <head>."""
    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": item.question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": item.answer,
                },
            }
            for item in faq
        ],
    }
    return json.dumps(payload, indent=2)
