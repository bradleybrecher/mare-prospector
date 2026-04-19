"""Cross-thread querying for the workflow checkpointer.

LangGraph's `get_state(config)` gives you one thread's state. To list ALL
pending threads (what the review dashboard needs), we have to go one level
below the LangGraph API and query its SQLite schema directly. This module
isolates that SQL so the rest of the codebase keeps talking in LangGraph terms.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mare.config import Settings


def _db_path() -> Path:
    settings = Settings.load()
    return settings.artifact_dir / "workflow.sqlite"


@dataclass
class ThreadSummary:
    thread_id: str
    asset_kind: str | None
    status: str | None
    iteration: int | None
    lint_clean: bool | None
    topic_or_salon: str | None

    def one_liner(self) -> str:
        parts = [
            self.thread_id,
            self.status or "?",
            f"{self.asset_kind or '?'}",
        ]
        if self.iteration and self.iteration > 1:
            parts.append(f"iter {self.iteration}")
        if self.lint_clean is True:
            parts.append("lint:clean")
        elif self.lint_clean is False:
            parts.append("lint:flagged")
        if self.topic_or_salon:
            parts.append(f"— {self.topic_or_salon}")
        return "  ".join(parts)


class WorkflowStore:
    """Minimal wrapper over the LangGraph SQLite checkpoint tables."""

    def __init__(self, db_path: Path | str | None = None):
        self._path = Path(db_path) if db_path else _db_path()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._path))

    def iter_thread_ids(self) -> list[str]:
        """All distinct thread IDs the checkpointer knows about."""
        if not self._path.exists():
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id"
            ).fetchall()
        return [r[0] for r in rows]


def list_pending_threads(store: WorkflowStore | None = None) -> list[ThreadSummary]:
    """Return a ThreadSummary for every thread currently awaiting human review.

    We query the compiled graph (via `get_workflow`) for each thread's current
    state. A thread is "pending" if its last checkpoint's `status` is
    `awaiting_review`.
    """
    from mare.workflow.graph import get_workflow

    store = store or WorkflowStore()
    summaries: list[ThreadSummary] = []
    with get_workflow() as graph:
        for thread_id in store.iter_thread_ids():
            config = {"configurable": {"thread_id": thread_id}}
            snapshot = graph.get_state(config)
            values = dict(snapshot.values) if snapshot.values else {}
            status = values.get("status")
            if status != "awaiting_review":
                continue
            summaries.append(_summary_from_values(thread_id, values))
    return summaries


def thread_summary(thread_id: str) -> ThreadSummary | None:
    """Summary for a single thread, regardless of status."""
    from mare.workflow.graph import get_workflow

    with get_workflow() as graph:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(config)
        if not snapshot.values:
            return None
        return _summary_from_values(thread_id, dict(snapshot.values))


def _summary_from_values(thread_id: str, values: dict[str, Any]) -> ThreadSummary:
    brief = values.get("brief") or {}
    topic_or_salon = brief.get("topic") or brief.get("salon_name") or None
    # Truncate long topics to keep the one-liner readable in the terminal.
    if topic_or_salon and len(topic_or_salon) > 60:
        topic_or_salon = topic_or_salon[:57] + "..."
    lint = values.get("lint") or {}
    return ThreadSummary(
        thread_id=thread_id,
        asset_kind=values.get("asset_kind"),
        status=values.get("status"),
        iteration=values.get("iteration"),
        lint_clean=lint.get("clean") if lint else None,
        topic_or_salon=topic_or_salon,
    )
