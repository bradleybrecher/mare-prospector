"""AI-ish tells that kill a luxury brand on contact.

Two purposes:
1. Injected into the system prompt as a BANNED list (prevention).
2. Consumed by `outreach.detector` to scan drafts before a human sees them
   (detection). If any of these appear, the draft is flagged for rewrite.
"""

from __future__ import annotations

AI_ISH_WORDS: frozenset[str] = frozenset({
    "delve",
    "delved",
    "delving",
    "unlock",
    "unlocks",
    "unlocking",
    "leverage",
    "leveraging",
    "utilize",
    "utilizing",
    "empower",
    "empowering",
    "elevate",
    "elevating",
    "harness",
    "harnessing",
    "seamlessly",
    "seamless",
    "robust",
    "cutting-edge",
    "game-changer",
    "game-changing",
    "revolutionize",
    "revolutionary",
    "paradigm",
    "synergy",
    "synergistic",
    "holistic",
    "ecosystem",
    "landscape",
    "journey",
    "tapestry",
    "testament",
    "bespoke",
    # Note: "curate / curated" is allowed — MaRe's own site uses "curated line"
    # for the Philip Martin's collection. Keep it reserved for that one context.
    "transformative",
    "meticulously",
    "meticulous",
    "endeavor",
    "foster",
    "fostering",
    "navigate",
    "navigating",
    "underscore",
    "underscores",
    "pivotal",
    "myriad",
    "plethora",
    "commendable",
    "noteworthy",
    "realm",
    "navigate",
    "resonate",
    "resonates",
    "resonating",
})


AI_ISH_PHRASES: tuple[str, ...] = (
    "in today's fast-paced world",
    "in the ever-evolving",
    "it's no secret that",
    "in the world of",
    "at the end of the day",
    "when it comes to",
    "i hope this email finds you well",
    "i hope this message finds you well",
    "i wanted to reach out",
    "just wanted to reach out",
    "i came across your",
    "i stumbled upon your",
    "hope you're doing well",
    "let me know your thoughts",
    "looking forward to connecting",
    "looking forward to hearing from you",
    "feel free to reach out",
    "don't hesitate to reach out",
    "in conclusion",
    "it is important to note",
    "it's worth noting",
    "needless to say",
    "take your business to the next level",
    "take your salon to the next level",
    "game changer",
    "best-in-class",
    "state-of-the-art",
    "one-stop shop",
    "cutting edge",
)


STRUCTURAL_TELLS: tuple[str, ...] = (
    "Three-item lists where two would do (the 'rule of three' AI default).",
    "Parallel tricolons ('we design, we deliver, we delight') — a dead giveaway.",
    "Em-dash pairs used as parentheticals — they scream AI now.",
    "Opening a sentence with 'Indeed,' 'Moreover,' 'Furthermore,' or 'Additionally,'.",
    "Closing paragraphs that restate the opener.",
    "Titles in Title Case for Every Major Word.",
    "Bulleted lists with bold lead-ins followed by a colon, on every bullet.",
)
