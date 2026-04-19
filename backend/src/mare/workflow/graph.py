"""Compile the MaRe approval graph.

Shape:

    START -> draft -> auto_lint -> human_review ─┬─> publish -> END
                      ^                          │
                      │                          └─> (revise) ─> draft (loop)
                      │                          └─> (reject) ─> END
                      │                          └─> (too many revisions) ─> force_reject -> END

The checkpointer is SQLite at `artifacts/workflow.sqlite`. One file, durable,
queryable with the `sqlite3` CLI if you want to pop the hood.

IMPORTANT: LangGraph 1.x's SqliteSaver is implemented as a context manager
(`with SqliteSaver.from_conn_string(...) as saver: ...`). We keep the connection
open for the lifetime of the process via `__enter__` called manually, which is
correct for our CLI model — every invocation opens, runs, closes.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from mare.config import Settings
from mare.workflow.nodes import (
    auto_lint_node,
    draft_node,
    force_reject_node,
    human_review_node,
    publish_node,
    route_after_review,
)
from mare.workflow.state import WorkflowState


def _workflow_db_path() -> Path:
    settings = Settings.load()
    path = settings.artifact_dir / "workflow.sqlite"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _build_builder() -> StateGraph:
    builder = StateGraph(WorkflowState)
    builder.add_node("draft", draft_node)
    builder.add_node("auto_lint", auto_lint_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("force_reject", force_reject_node)
    builder.add_node("publish", publish_node)

    builder.add_edge(START, "draft")
    builder.add_edge("draft", "auto_lint")
    builder.add_edge("auto_lint", "human_review")
    builder.add_conditional_edges(
        "human_review",
        route_after_review,
        {
            "publish": "publish",
            "draft": "draft",
            "force_reject": "force_reject",
            "end": END,
        },
    )
    builder.add_edge("force_reject", END)
    builder.add_edge("publish", END)
    return builder


def build_workflow_graph(checkpointer: SqliteSaver):
    """Compile the graph with the given checkpointer.

    Kept separate from `get_workflow` so tests can compile with an in-memory
    checkpointer (e.g. `SqliteSaver.from_conn_string(":memory:")`).
    """
    builder = _build_builder()
    return builder.compile(checkpointer=checkpointer)


@contextmanager
def get_workflow() -> Iterator:
    """Yield a compiled workflow with a file-backed SQLite checkpointer.

    Always use this as a context manager:

        with get_workflow() as graph:
            graph.invoke(...)
    """
    db_path = _workflow_db_path()
    # `check_same_thread=False` lets the same connection serve CLI calls across
    # the typer app lifecycle without thread-affinity complaints.
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    saver = SqliteSaver(conn)
    try:
        yield build_workflow_graph(saver)
    finally:
        conn.close()
