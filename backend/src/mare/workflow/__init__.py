"""MaRe's human-in-the-loop approval workflow.

Nothing ships as MaRe without a human "MaRe Verified" stamp. This package
wraps every generator (shorts, blogs, outreach, postcards) in a durable
LangGraph state machine:

    draft -> auto_lint -> human_review (INTERRUPT) -> approve -> publish
                                                    -> revise (loops back to draft)
                                                    -> reject (END)

State is persisted to a SQLite checkpointer (`artifacts/workflow.sqlite`), so a
draft can sit in review for minutes, hours, or days without losing context.
"""

from mare.workflow.graph import build_workflow_graph, get_workflow
from mare.workflow.state import ASSET_KINDS, AssetKind, ReviewAction, WorkflowState
from mare.workflow.store import WorkflowStore, list_pending_threads, thread_summary

__all__ = [
    "ASSET_KINDS",
    "AssetKind",
    "ReviewAction",
    "WorkflowState",
    "WorkflowStore",
    "build_workflow_graph",
    "get_workflow",
    "list_pending_threads",
    "thread_summary",
]
