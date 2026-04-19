"""Prompt templates for outreach generation.

Kept as plain strings (not Jinja) so they are easy to read, diff, and iterate
with non-engineers. Swap to Jinja if templates grow branches.
"""

from __future__ import annotations

COLD_EMAIL_TASK = """Write a single cold outreach email from MaRe to this salon.

GOAL
Start a real conversation about bringing the MaRe head-spa ritual into their salon.
Not a pitch deck. Not a sales letter. A short, quietly confident note that reads
like it was written by a person who knows salons.

STRUCTURE (strict)
- Subject line: 5 words or fewer, lowercase except proper nouns, no colons, no emoji.
- Body: 3 short paragraphs max. Sentence fragments are fine.
- Paragraph 1 (1–2 sentences): A specific, non-generic observation about THIS salon.
  Priority order for the anchor: (1) a social_highlight if present, (2) a notable
  detail, (3) their city + a specialty. If you use a social highlight, reference it
  the way a peer would — by the thing in the post, not by the fact you saw the post.
  Never say "I came across your salon" / "I saw on your Instagram" / similar.
- Paragraph 2 (2–3 sentences): One concrete reason MaRe fits them specifically
  — e.g. retail attach rate on scalp rituals, chair-time economics of the
  Capsule, or the Italian formulation story. Pick ONE angle, not three.
- Paragraph 3 (1 sentence): A low-stakes ask. A 15-minute call, a sample kit,
  or a visit to the Miami lab. Never "let me know your thoughts".
- Sign-off: first name only.

HARD RULES
- No "I hope this email finds you well" or any variant.
- No adjective stacks (no "luxurious, personalized, transformative" triplets).
- No em-dash pairs as parentheticals.
- No rhetorical questions as openers.
- No promises of speed, scale, or guarantees.
- The word "luxury" can appear at most once.

PROSPECT CONTEXT
{prospect_context}

SENDER
{sender_name}, {sender_title} at MaRe (Miami).

Return the email as structured JSON matching the declared response schema.
The `body` field should contain 3 short paragraphs separated by blank lines.
"""


LINKEDIN_DM_TASK = """Write a LinkedIn DM (not an email) from MaRe to this salon owner.

STRUCTURE (strict)
- 50 words or fewer. Period.
- One specific observation about them (not their industry).
- One sentence on why MaRe is worth 15 minutes.
- No link unless asked.
- Signed with first name only.

HARD RULES
- No "I hope you're doing well".
- No "I came across your profile".
- No emoji.
- Read like a text to a peer, not a template.

PROSPECT CONTEXT
{prospect_context}

SENDER
{sender_name}, {sender_title} at MaRe.

Return the DM as structured JSON matching the declared response schema.
"""
