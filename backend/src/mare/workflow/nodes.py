"""Graph nodes.

Each node takes the current state and returns a partial-state update.
Nodes are deliberately thin wrappers so all domain logic stays in the
existing generators (`mare.content.*`, `mare.outreach.*`).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langgraph.types import interrupt

from mare.brand import evaluate_coverage
from mare.config import Settings
from mare.content.blogs import generate_blog
from mare.content.brief import ContentBrief
from mare.content.shorts import generate_short_script
from mare.outreach.detector import detect_ai_tells
from mare.outreach.personalizer import OutreachDrafter
from mare.outreach.postcard import PostcardDesigner
from mare.outreach.prospect import SalonProspect, SocialHighlight
from mare.workflow.state import MAX_REVISION_ITERATIONS, WorkflowState


# --------------------------------------------------------------------------- #
# Drafting
# --------------------------------------------------------------------------- #


def draft_node(state: WorkflowState) -> dict[str, Any]:
    """Route to the correct generator based on asset_kind.

    Accepts an optional `revision_notes` in state. When non-empty, generators
    receive them as a steering hint via a pseudo-brief field the prompt
    templates already understand (we just append a "REVISION NOTES" block).
    """
    kind = state["asset_kind"]
    brief = state.get("brief", {})
    revision_notes = state.get("revision_notes", [])

    if kind == "short":
        short_brief = _build_content_brief(brief, revision_notes)
        script = generate_short_script(short_brief)
        return {
            "status": "drafting",
            "draft": script.raw,
            "draft_markdown": script.to_markdown(),
        }

    if kind == "blog":
        blog_brief = _build_content_brief(brief, revision_notes)
        blog = generate_blog(blog_brief)
        return {
            "status": "drafting",
            "draft": blog.raw,
            "draft_markdown": blog.to_markdown(),
        }

    if kind == "outreach":
        prospect = _build_prospect(brief)
        drafter = OutreachDrafter()
        draft = drafter.draft(
            prospect,
            sender_name=brief.get("sender_name", "Rebecca"),
            sender_title=brief.get("sender_title", "Co-Founder"),
        )
        payload = {
            "email": draft.email,
            "linkedin_dm": draft.linkedin_dm,
            "anchor": draft.anchor,
            "angle": draft.angle,
            "self_critique": draft.self_critique,
        }
        return {
            "status": "drafting",
            "draft": payload,
            "draft_markdown": draft.to_markdown(),
        }

    if kind == "postcard":
        prospect = _build_prospect(brief)
        designer = PostcardDesigner()
        concept = designer.design(
            prospect,
            sender_name=brief.get("sender_name", "Rebecca"),
            sender_title=brief.get("sender_title", "Co-Founder"),
        )
        return {
            "status": "drafting",
            "draft": concept.raw,
            "draft_markdown": concept.to_markdown(),
        }

    raise ValueError(f"Unknown asset_kind: {kind!r}")


def _build_content_brief(brief: dict[str, Any], revision_notes: list[str]) -> ContentBrief:
    """Bake revision notes into the topic so the generator sees the feedback.

    This is deliberately blunt — we append a reviewer block to the topic. The
    brand prompt already tells the model to take feedback seriously. A cleaner
    alternative would be adding a dedicated `revision_notes` field to
    ContentBrief and every prompt template; we'll do that when feedback loops
    become the common path rather than the exception.
    """
    topic = brief.get("topic", "")
    if revision_notes:
        bullet = "\n".join(f"- {note}" for note in revision_notes)
        topic = f"{topic}\n\nREVIEWER FEEDBACK — address these on this revision:\n{bullet}"
    return ContentBrief(
        topic=topic,
        audience=brief.get("audience", "high_end_client"),  # type: ignore[arg-type]
        primary_product=brief.get("primary_product"),
        proof_point=brief.get("proof_point"),
        call_to_action=brief.get("call_to_action"),
    )


def _build_prospect(brief: dict[str, Any]) -> SalonProspect:
    highlights = [SocialHighlight(**h) for h in brief.get("social_highlights", [])]
    return SalonProspect(
        salon_name=brief["salon_name"],
        city=brief["city"],
        state=brief.get("state"),
        owner_name=brief.get("owner_name"),
        website=brief.get("website"),
        instagram_handle=brief.get("instagram_handle"),
        estimated_annual_revenue_usd=brief.get("estimated_annual_revenue_usd"),
        service_specialties=brief.get("service_specialties", []),
        notable_details=brief.get("notable_details", []),
        social_highlights=highlights,
    )


# --------------------------------------------------------------------------- #
# Auto-lint
# --------------------------------------------------------------------------- #


def auto_lint_node(state: WorkflowState) -> dict[str, Any]:
    """Machine checks before the human sees it.

    Combines:
    - AI-ish detector on the draft markdown (banned words, em-dash pairs, etc.)
    - Brand-pillar vocabulary coverage (systematic / luxury / natural-organic / wellness)
    """
    text = state.get("draft_markdown", "") or ""
    tells_report = detect_ai_tells(text)
    coverage = evaluate_coverage(text)
    ai_tells: list[str] = sorted({*tells_report.banned_words, *tells_report.banned_phrases})
    if tells_report.em_dash_pairs:
        ai_tells.append(f"em-dash pairs × {tells_report.em_dash_pairs}")
    if tells_report.tricolon_hits:
        ai_tells.append(f"tricolons × {len(tells_report.tricolon_hits)}")
    lint = {
        "clean": tells_report.is_clean and not coverage.over_stuffed_pillars,
        "ai_tells": ai_tells,
        "vocab_summary": coverage.summary(),
        "vocab_coverage_ratio": coverage.coverage_ratio,
        "vocab_over_stuffed": coverage.over_stuffed_pillars,
    }
    return {"status": "awaiting_review", "lint": lint}


# --------------------------------------------------------------------------- #
# Human review (INTERRUPT)
# --------------------------------------------------------------------------- #


def human_review_node(state: WorkflowState) -> dict[str, Any]:
    """Pause the graph until a human resumes with an action.

    The caller resumes with:
        graph.invoke(Command(resume={"action": "approve", "reviewer": "..."}), config=...)
        graph.invoke(Command(resume={"action": "revise", "notes": "..."}), config=...)
        graph.invoke(Command(resume={"action": "reject", "reason": "..."}), config=...)
    """
    payload_to_reviewer = {
        "thread_id": state.get("thread_id"),
        "asset_kind": state.get("asset_kind"),
        "iteration": state.get("iteration", 1),
        "lint": state.get("lint"),
        "draft_markdown": state.get("draft_markdown"),
    }
    decision: dict[str, Any] = interrupt(payload_to_reviewer)
    action = decision.get("action")

    if action == "approve":
        return {
            "status": "approved",
            "reviewer": decision.get("reviewer", "anonymous"),
            "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    if action == "revise":
        notes = str(decision.get("notes", "")).strip() or "(no notes)"
        existing = list(state.get("revision_notes", []))
        existing.append(notes)
        return {
            "status": "revising",
            "revision_notes": existing,
            "iteration": state.get("iteration", 1) + 1,
        }
    if action == "reject":
        return {
            "status": "rejected",
            "rejection_reason": str(decision.get("reason", "")).strip() or "(no reason)",
            "reviewer": decision.get("reviewer"),
        }
    raise ValueError(f"Unknown review action: {action!r}")


# --------------------------------------------------------------------------- #
# Routing after review
# --------------------------------------------------------------------------- #


def route_after_review(state: WorkflowState) -> str:
    status = state.get("status")
    if status == "approved":
        return "publish"
    if status == "revising":
        if state.get("iteration", 1) > MAX_REVISION_ITERATIONS:
            # Safety rail — don't let a draft loop forever. Force reject.
            return "force_reject"
        return "draft"
    if status == "rejected":
        return "end"
    return "end"


def force_reject_node(state: WorkflowState) -> dict[str, Any]:
    return {
        "status": "rejected",
        "rejection_reason": (
            state.get("rejection_reason")
            or f"Exceeded MAX_REVISION_ITERATIONS={MAX_REVISION_ITERATIONS}."
        ),
    }


# --------------------------------------------------------------------------- #
# Publish
# --------------------------------------------------------------------------- #


def publish_node(state: WorkflowState) -> dict[str, Any]:
    """Write the MaRe-Verified artifact to `artifacts/verified/<kind>/<thread>.md`.

    'Publish' here means: stamped, durable, ready to be picked up by a downstream
    sender / scheduler. We deliberately do NOT auto-post to HeyGen, email, or
    socials from this node — that belongs to a separate dispatcher the user
    controls. The verified artifact is the durable contract between the two.
    """
    thread_id = state["thread_id"]
    kind = state["asset_kind"]
    reviewer = state.get("reviewer") or "anonymous"
    verified_at = state.get("verified_at") or datetime.now(timezone.utc).isoformat(timespec="seconds")

    settings = Settings.load()
    out_dir: Path = settings.artifact_dir / "verified" / kind
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{thread_id}.md"

    frontmatter = (
        "---\n"
        f"mare_verified: true\n"
        f"thread_id: {thread_id}\n"
        f"asset_kind: {kind}\n"
        f"reviewer: {reviewer}\n"
        f"verified_at: {verified_at}\n"
        f"iterations: {state.get('iteration', 1)}\n"
        "---\n\n"
    )
    out_path.write_text(frontmatter + (state.get("draft_markdown") or ""))
    return {"status": "published", "published_path": str(out_path)}
