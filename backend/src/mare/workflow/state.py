"""Workflow state types.

Kept intentionally flat and JSON-serializable so LangGraph's SQLite checkpointer
can round-trip it without custom encoders.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

AssetKind = Literal["short", "blog", "outreach", "postcard"]
ASSET_KINDS: tuple[AssetKind, ...] = ("short", "blog", "outreach", "postcard")

ReviewAction = Literal["approve", "revise", "reject"]
WorkflowStatus = Literal[
    "drafting",
    "awaiting_review",
    "revising",
    "approved",
    "rejected",
    "published",
]

MAX_REVISION_ITERATIONS = 3


class LintResult(TypedDict, total=False):
    """Output of the auto-lint pass. `clean` gates a green path, but a reviewer
    can still approve a non-clean draft if they judge the flags as false positives."""

    clean: bool
    ai_tells: list[str]  # words/phrases the detector caught
    vocab_summary: str   # from brand.vocabulary coverage report
    vocab_coverage_ratio: float
    vocab_over_stuffed: list[str]


class WorkflowState(TypedDict, total=False):
    # Identity / routing
    thread_id: str
    asset_kind: AssetKind
    status: WorkflowStatus

    # Input and output
    brief: dict[str, Any]      # the inputs used to draft (topic/salon/highlights...)
    draft: dict[str, Any]      # the structured generator output (from pydantic .model_dump())
    draft_markdown: str        # human-readable rendering

    # Quality signals
    lint: LintResult

    # Human decision loop
    iteration: int
    revision_notes: list[str]          # full history of revision feedback
    reviewer: str | None
    verified_at: str | None            # ISO timestamp when stamped MaRe Verified
    rejection_reason: str | None

    # Where the final approved artifact landed on disk (post-publish).
    published_path: str | None
