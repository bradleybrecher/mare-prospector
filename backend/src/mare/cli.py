"""MaRe command-line interface.

Examples:
    python -m mare ping
    python -m mare outreach draft --salon-name "Maison Noir" --city Aspen --owner Camille
    python -m mare content short --topic "Why your $300 shampoo isn't working"
    python -m mare content package --topic "The case for a 20-minute head ritual"
"""

from __future__ import annotations

from pathlib import Path

import typer
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mare.config import Settings
from mare.content.brief import ContentBrief
from mare.content.image_prompts import generate_image_prompts
from mare.content.image_renderer import IMAGEN_TIERS, render_image_prompts
from mare.content.pipeline import ContentPipeline
from mare.content.shorts import generate_short_script
from mare.content.video_adapters import HeyGenClient, script_to_heygen_spec
from mare.gemini_client import GeminiClient
from mare.outreach.personalizer import OutreachDrafter
from mare.outreach.postcard import PostcardDesigner
from mare.outreach.prospect import SalonProspect, SocialHighlight
from mare.workflow import get_workflow, list_pending_threads, thread_summary

app = typer.Typer(help="MaRe Head Spa growth engine CLI.", no_args_is_help=True)
outreach_app = typer.Typer(help="Pillar 2 — luxury-standard outreach.", no_args_is_help=True)
content_app = typer.Typer(help="Pillar 3 — high-volume content synthesis.", no_args_is_help=True)
workflow_app = typer.Typer(
    help="Submit drafts to the MaRe-Verified approval workflow.", no_args_is_help=True
)
review_app = typer.Typer(
    help="Review, approve, revise, or reject drafts awaiting MaRe Verified status.",
    no_args_is_help=True,
)
app.add_typer(outreach_app, name="outreach")
app.add_typer(content_app, name="content")
app.add_typer(workflow_app, name="workflow")
app.add_typer(review_app, name="review")

console = Console()


@app.command()
def ping(
    model: str | None = typer.Option(
        None, "--model", help="Override GEMINI_MODEL for this call (e.g. gemini-2.5-pro)."
    ),
) -> None:
    """Smoke-test the Gemini connection with a short, on-brand prompt."""
    settings = Settings.load()
    client = GeminiClient(settings)
    effective = model or settings.gemini_model
    console.print(f"[dim]Model:[/dim] {effective}")
    result = client.generate(
        "In one short sentence (no adjectives stacked), describe the feeling of a MaRe head-spa ritual.",
        model=model,
    )
    console.print(Panel(result.text, title="Gemini says", border_style="cyan"))


def _build_prospect(
    salon_name: str,
    city: str,
    *,
    state: str | None,
    owner: str | None,
    website: str | None,
    instagram: str | None,
    revenue: int | None,
    specialty: list[str] | None,
    note: list[str] | None,
    highlight: list[str] | None,
) -> SalonProspect:
    """Shared builder for both `outreach draft` and `outreach postcard`.

    `--highlight` accepts "<platform>|<summary>" or just "<summary>" (assumes
    instagram). e.g. --highlight "instagram|Reel on Nov 14 about a 3-hour color
    correction from brunette to blonde".
    """
    highlights: list[SocialHighlight] = []
    for raw in highlight or []:
        if "|" in raw:
            platform, summary = (part.strip() for part in raw.split("|", 1))
        else:
            platform, summary = "instagram", raw.strip()
        highlights.append(SocialHighlight(platform=platform, summary=summary))

    return SalonProspect(
        salon_name=salon_name,
        owner_name=owner,
        city=city,
        state=state,
        website=website,
        instagram_handle=instagram,
        estimated_annual_revenue_usd=revenue,
        service_specialties=specialty or [],
        notable_details=note or [],
        social_highlights=highlights,
    )


@outreach_app.command("draft")
def outreach_draft(
    salon_name: str = typer.Option(..., "--salon-name", help="Name of the salon."),
    city: str = typer.Option(..., "--city", help="City where the salon operates."),
    state: str | None = typer.Option(None, "--state"),
    owner: str | None = typer.Option(None, "--owner", help="Owner first name."),
    website: str | None = typer.Option(None, "--website"),
    instagram: str | None = typer.Option(None, "--instagram"),
    revenue: int | None = typer.Option(None, "--revenue", help="Estimated annual revenue USD."),
    specialty: list[str] = typer.Option(
        None, "--specialty", help="Repeatable. e.g. --specialty 'color correction'."
    ),
    note: list[str] = typer.Option(
        None, "--note", help="Repeatable notable detail. e.g. --note 'Featured in Allure 2024'."
    ),
    highlight: list[str] = typer.Option(
        None,
        "--highlight",
        help=(
            "Repeatable social-media highlight. Format: 'platform|summary' "
            "(or just 'summary' for instagram)."
        ),
    ),
    sender_name: str = typer.Option("Rebecca", "--sender"),
    sender_title: str = typer.Option("Co-Founder", "--sender-title"),
) -> None:
    """Generate a personalized email + LinkedIn DM for a single salon."""
    prospect = _build_prospect(
        salon_name,
        city,
        state=state,
        owner=owner,
        website=website,
        instagram=instagram,
        revenue=revenue,
        specialty=specialty,
        note=note,
        highlight=highlight,
    )
    drafter = OutreachDrafter()
    draft = drafter.draft(prospect, sender_name=sender_name, sender_title=sender_title)

    settings = Settings.load()
    out_path = settings.artifact_dir / "outreach" / f"{_slugify(salon_name)}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(draft.to_markdown())

    console.print(Panel(draft.to_markdown(), title=f"Draft → {out_path}", border_style="cyan"))
    if not draft.is_clean:
        console.print("[yellow]Heads up: AI-ish tells detected. Rewrite before sending.[/yellow]")


@outreach_app.command("postcard")
def outreach_postcard(
    salon_name: str = typer.Option(..., "--salon-name"),
    city: str = typer.Option(..., "--city"),
    state: str | None = typer.Option(None, "--state"),
    owner: str | None = typer.Option(None, "--owner"),
    website: str | None = typer.Option(None, "--website"),
    instagram: str | None = typer.Option(None, "--instagram"),
    revenue: int | None = typer.Option(None, "--revenue"),
    specialty: list[str] = typer.Option(None, "--specialty"),
    note: list[str] = typer.Option(None, "--note"),
    highlight: list[str] = typer.Option(None, "--highlight"),
    sender_name: str = typer.Option("Rebecca", "--sender"),
    sender_title: str = typer.Option("Co-Founder", "--sender-title"),
) -> None:
    """Generate a luxury direct-mail postcard concept (front image + back copy + production)."""
    prospect = _build_prospect(
        salon_name,
        city,
        state=state,
        owner=owner,
        website=website,
        instagram=instagram,
        revenue=revenue,
        specialty=specialty,
        note=note,
        highlight=highlight,
    )
    designer = PostcardDesigner()
    concept = designer.design(prospect, sender_name=sender_name, sender_title=sender_title)

    settings = Settings.load()
    out_path = settings.artifact_dir / "outreach" / "postcards" / f"{_slugify(salon_name)}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(concept.to_markdown())
    console.print(Panel(concept.to_markdown(), title=f"Postcard → {out_path}", border_style="magenta"))


@content_app.command("short")
def content_short(
    topic: str = typer.Option(..., "--topic", help="Central idea for the Short."),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
    cta: str | None = typer.Option(None, "--cta"),
) -> None:
    """Generate a single YouTube Short / Reel script."""
    brief = ContentBrief(
        topic=topic,
        audience=audience,  # type: ignore[arg-type]
        proof_point=proof,
        call_to_action=cta,
    )
    script = generate_short_script(brief)
    settings = Settings.load()
    out_path = settings.artifact_dir / "content" / "shorts" / f"{_slugify(topic)}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(script.to_markdown())
    console.print(Panel(script.to_markdown(), title=f"Short → {out_path}", border_style="cyan"))


@content_app.command("image-prompts")
def content_image_prompts(
    topic: str = typer.Option(..., "--topic", help="Central idea — same as for `content short`."),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
    cta: str | None = typer.Option(None, "--cta"),
) -> None:
    """Generate a Short AND per-beat image prompts (Midjourney / Imagen / generic)."""
    brief = ContentBrief(
        topic=topic,
        audience=audience,  # type: ignore[arg-type]
        proof_point=proof,
        call_to_action=cta,
    )
    script = generate_short_script(brief)
    prompts = generate_image_prompts(script)

    settings = Settings.load()
    slug = _slugify(topic)
    out_dir = settings.artifact_dir / "content" / "shorts" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.md").write_text(script.to_markdown())
    (out_dir / "image_prompts.md").write_text(prompts.to_markdown())

    console.print(
        Panel(
            f"Wrote [bold]{out_dir}[/bold]\n• script.md\n• image_prompts.md",
            title="Short + image prompts",
            border_style="cyan",
        )
    )


@content_app.command("render-images")
def content_render_images(
    topic: str = typer.Option(..., "--topic", help="Central idea for the Short."),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
    cta: str | None = typer.Option(None, "--cta"),
    tier: str = typer.Option(
        "standard",
        "--tier",
        help=f"Imagen tier: fast | standard | ultra. Options: {', '.join(IMAGEN_TIERS)}.",
    ),
) -> None:
    """End-to-end: Short + per-beat prompts + real rendered images via Imagen 4."""
    brief = ContentBrief(
        topic=topic,
        audience=audience,  # type: ignore[arg-type]
        proof_point=proof,
        call_to_action=cta,
    )
    script = generate_short_script(brief)
    prompts = generate_image_prompts(script)

    settings = Settings.load()
    slug = _slugify(topic)
    out_dir = settings.artifact_dir / "content" / "shorts" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.md").write_text(script.to_markdown())
    (out_dir / "image_prompts.md").write_text(prompts.to_markdown())

    images_dir = out_dir / "images"
    rendered = render_image_prompts(prompts, out_dir=images_dir, tier=tier)
    console.print(
        Panel(
            f"Wrote [bold]{out_dir}[/bold]\n"
            f"• script.md\n• image_prompts.md\n• images/ ({len(rendered.beats)} frame{'s' if len(rendered.beats) != 1 else ''})\n\n"
            f"{rendered.summary()}",
            title="Short + rendered images",
            border_style="green",
        )
    )


@content_app.command("heygen-spec")
def content_heygen_spec(
    topic: str = typer.Option(..., "--topic"),
    submit: bool = typer.Option(False, "--submit", help="Actually POST to HeyGen (requires HEYGEN_API_KEY)."),
) -> None:
    """Generate a Short and produce a ready-to-submit HeyGen job spec (dry-run by default)."""
    brief = ContentBrief(topic=topic)
    script = generate_short_script(brief)
    spec = script_to_heygen_spec(script)

    settings = Settings.load()
    out_dir = settings.artifact_dir / "content" / "shorts" / _slugify(topic)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "script.md").write_text(script.to_markdown())
    (out_dir / "heygen_spec.json").write_text(spec.to_json())

    client = HeyGenClient()
    if submit:
        submission = client.submit(spec)
        note = "LIVE — submitted to HeyGen." if not submission.dry_run else "DRY-RUN — set HEYGEN_API_KEY to submit."
    else:
        note = "Dry-run only. Re-run with --submit (and HEYGEN_API_KEY set) to actually generate."

    console.print(
        Panel(
            f"Wrote [bold]{out_dir}[/bold]\n• script.md\n• heygen_spec.json\n\n{note}",
            title="HeyGen job",
            border_style="cyan",
        )
    )


@content_app.command("package")
def content_package(
    topic: str = typer.Option(..., "--topic"),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
    cta: str | None = typer.Option(None, "--cta"),
) -> None:
    """Generate a full content package: Short + Blog + IG + LinkedIn from one brief."""
    brief = ContentBrief(
        topic=topic,
        audience=audience,  # type: ignore[arg-type]
        proof_point=proof,
        call_to_action=cta,
    )
    pkg = ContentPipeline().run(brief)
    console.print(
        Panel(
            f"Wrote 4 assets to [bold]{pkg.output_dir}[/bold]\n"
            f"• short.md\n• blog.md\n• instagram.md\n• linkedin.md",
            title="Content package",
            border_style="green",
        )
    )


def _slugify(s: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in s.lower()).strip("-")[:60] or "untitled"


# --------------------------------------------------------------------------- #
# Workflow: submit a draft into the MaRe-Verified approval flow
# --------------------------------------------------------------------------- #


def _new_thread_id() -> str:
    import secrets
    return secrets.token_hex(4)


def _submit(asset_kind: str, brief: dict) -> tuple[str, dict]:
    """Kick off a new workflow thread and run until the human-review interrupt.

    Returns (thread_id, final_state_values_at_interrupt).
    """
    thread_id = _new_thread_id()
    config = {"configurable": {"thread_id": thread_id}}
    initial: dict = {
        "thread_id": thread_id,
        "asset_kind": asset_kind,
        "brief": brief,
        "iteration": 1,
        "revision_notes": [],
    }
    with get_workflow() as graph:
        graph.invoke(initial, config=config)
        snapshot = graph.get_state(config)
    return thread_id, dict(snapshot.values) if snapshot.values else {}


def _resume(thread_id: str, resume_value: dict) -> dict:
    """Resume a paused thread with a review action."""
    config = {"configurable": {"thread_id": thread_id}}
    with get_workflow() as graph:
        graph.invoke(Command(resume=resume_value), config=config)
        snapshot = graph.get_state(config)
    return dict(snapshot.values) if snapshot.values else {}


@workflow_app.command("submit-short")
def workflow_submit_short(
    topic: str = typer.Option(..., "--topic"),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
    cta: str | None = typer.Option(None, "--cta"),
) -> None:
    """Draft a Short and queue it for MaRe-Verified review."""
    thread_id, values = _submit(
        "short",
        {"topic": topic, "audience": audience, "proof_point": proof, "call_to_action": cta},
    )
    _render_submission(thread_id, values)


@workflow_app.command("submit-blog")
def workflow_submit_blog(
    topic: str = typer.Option(..., "--topic"),
    audience: str = typer.Option("high_end_client", "--audience"),
    proof: str | None = typer.Option(None, "--proof"),
) -> None:
    """Draft a Blog and queue it for MaRe-Verified review."""
    thread_id, values = _submit(
        "blog", {"topic": topic, "audience": audience, "proof_point": proof}
    )
    _render_submission(thread_id, values)


@workflow_app.command("submit-outreach")
def workflow_submit_outreach(
    salon_name: str = typer.Option(..., "--salon-name"),
    city: str = typer.Option(..., "--city"),
    state: str | None = typer.Option(None, "--state"),
    owner: str | None = typer.Option(None, "--owner"),
    website: str | None = typer.Option(None, "--website"),
    instagram: str | None = typer.Option(None, "--instagram"),
    revenue: int | None = typer.Option(None, "--revenue"),
    specialty: list[str] = typer.Option(None, "--specialty"),
    note: list[str] = typer.Option(None, "--note"),
    highlight: list[str] = typer.Option(None, "--highlight"),
    sender_name: str = typer.Option("Rebecca", "--sender"),
    sender_title: str = typer.Option("Co-Founder", "--sender-title"),
) -> None:
    """Draft a salon outreach email+DM and queue it for MaRe-Verified review."""
    brief = _outreach_brief_dict(
        salon_name, city, state, owner, website, instagram, revenue,
        specialty, note, highlight, sender_name, sender_title,
    )
    thread_id, values = _submit("outreach", brief)
    _render_submission(thread_id, values)


@workflow_app.command("submit-postcard")
def workflow_submit_postcard(
    salon_name: str = typer.Option(..., "--salon-name"),
    city: str = typer.Option(..., "--city"),
    state: str | None = typer.Option(None, "--state"),
    owner: str | None = typer.Option(None, "--owner"),
    website: str | None = typer.Option(None, "--website"),
    instagram: str | None = typer.Option(None, "--instagram"),
    revenue: int | None = typer.Option(None, "--revenue"),
    specialty: list[str] = typer.Option(None, "--specialty"),
    note: list[str] = typer.Option(None, "--note"),
    highlight: list[str] = typer.Option(None, "--highlight"),
    sender_name: str = typer.Option("Rebecca", "--sender"),
    sender_title: str = typer.Option("Co-Founder", "--sender-title"),
) -> None:
    """Draft a luxury postcard concept and queue it for MaRe-Verified review."""
    brief = _outreach_brief_dict(
        salon_name, city, state, owner, website, instagram, revenue,
        specialty, note, highlight, sender_name, sender_title,
    )
    thread_id, values = _submit("postcard", brief)
    _render_submission(thread_id, values)


def _outreach_brief_dict(
    salon_name, city, state, owner, website, instagram, revenue,
    specialty, note, highlight, sender_name, sender_title,
) -> dict:
    highlights: list[dict] = []
    for raw in highlight or []:
        if "|" in raw:
            platform, summary = (part.strip() for part in raw.split("|", 1))
        else:
            platform, summary = "instagram", raw.strip()
        highlights.append({"platform": platform, "summary": summary})

    return {
        "salon_name": salon_name,
        "city": city,
        "state": state,
        "owner_name": owner,
        "website": website,
        "instagram_handle": instagram,
        "estimated_annual_revenue_usd": revenue,
        "service_specialties": specialty or [],
        "notable_details": note or [],
        "social_highlights": highlights,
        "sender_name": sender_name,
        "sender_title": sender_title,
    }


def _render_submission(thread_id: str, values: dict) -> None:
    lint = values.get("lint") or {}
    status = values.get("status", "?")
    coverage = lint.get("vocab_summary", "")
    tells = lint.get("ai_tells") or []
    tells_line = ", ".join(tells) if tells else "(none)"
    clean = "✓ clean" if lint.get("clean") else "⚠ flagged"
    console.print(
        Panel(
            f"[bold]Thread:[/bold] {thread_id}\n"
            f"[bold]Status:[/bold] {status}\n"
            f"[bold]Auto-lint:[/bold] {clean}\n"
            f"[bold]AI tells:[/bold] {tells_line}\n"
            f"[bold]Vocabulary:[/bold] {coverage}\n\n"
            f"Inspect:   [cyan]python -m mare review show {thread_id}[/cyan]\n"
            f"Approve:   [green]python -m mare review approve {thread_id} --reviewer rebecca[/green]\n"
            f"Revise:    [yellow]python -m mare review revise {thread_id} --notes \"...\"[/yellow]\n"
            f"Reject:    [red]python -m mare review reject {thread_id} --reason \"...\"[/red]",
            title="Submitted — awaiting MaRe Verified",
            border_style="cyan",
        )
    )


# --------------------------------------------------------------------------- #
# Review: the human-in-the-loop side
# --------------------------------------------------------------------------- #


@review_app.command("pending")
def review_pending() -> None:
    """List every draft currently awaiting MaRe Verified review."""
    pending = list_pending_threads()
    if not pending:
        console.print("[dim]No drafts awaiting review.[/dim]")
        return
    table = Table(title="Awaiting MaRe Verified", title_style="bold cyan")
    table.add_column("Thread", style="cyan", no_wrap=True)
    table.add_column("Kind")
    table.add_column("Iter")
    table.add_column("Lint")
    table.add_column("Topic / Salon")
    for s in pending:
        lint_cell = "[green]clean[/green]" if s.lint_clean else "[yellow]flagged[/yellow]"
        table.add_row(
            s.thread_id,
            s.asset_kind or "?",
            str(s.iteration or 1),
            lint_cell,
            s.topic_or_salon or "-",
        )
    console.print(table)


@review_app.command("show")
def review_show(thread_id: str = typer.Argument(...)) -> None:
    """Show the full draft + lint report for one thread."""
    summary = thread_summary(thread_id)
    if not summary:
        console.print(f"[red]No thread found with id {thread_id!r}.[/red]")
        raise typer.Exit(1)
    with get_workflow() as graph:
        snapshot = graph.get_state({"configurable": {"thread_id": thread_id}})
        values = dict(snapshot.values) if snapshot.values else {}

    lint = values.get("lint") or {}
    header = (
        f"[bold]Thread:[/bold] {thread_id}\n"
        f"[bold]Kind:[/bold] {values.get('asset_kind')}\n"
        f"[bold]Status:[/bold] {values.get('status')}\n"
        f"[bold]Iteration:[/bold] {values.get('iteration', 1)}\n"
        f"[bold]Auto-lint:[/bold] "
        + ("[green]clean[/green]" if lint.get("clean") else "[yellow]flagged[/yellow]")
        + "\n"
        f"[bold]Vocabulary:[/bold] {lint.get('vocab_summary', '-')}\n"
    )
    console.print(Panel(header, title="Review", border_style="cyan"))

    notes: list[str] = values.get("revision_notes") or []
    if notes:
        console.print(
            Panel(
                "\n".join(f"{i + 1}. {n}" for i, n in enumerate(notes)),
                title="Revision history",
                border_style="yellow",
            )
        )
    console.print(Panel(values.get("draft_markdown", "(no draft)"), title="Draft", border_style="white"))


@review_app.command("approve")
def review_approve(
    thread_id: str = typer.Argument(...),
    reviewer: str = typer.Option("anonymous", "--reviewer"),
) -> None:
    """Stamp the draft as MaRe Verified and write the final artifact."""
    values = _resume(thread_id, {"action": "approve", "reviewer": reviewer})
    path = values.get("published_path")
    console.print(
        Panel(
            f"[bold green]MaRe Verified[/bold green] by [bold]{reviewer}[/bold]\n"
            f"Thread: {thread_id}\n"
            f"Iterations: {values.get('iteration', 1)}\n"
            f"Published: {path or '(no path)'}",
            title="Approved",
            border_style="green",
        )
    )


@review_app.command("revise")
def review_revise(
    thread_id: str = typer.Argument(...),
    notes: str = typer.Option(..., "--notes", help="Concrete, actionable feedback for the next pass."),
) -> None:
    """Bounce the draft back for another generation pass with reviewer feedback."""
    values = _resume(thread_id, {"action": "revise", "notes": notes})
    lint = values.get("lint") or {}
    console.print(
        Panel(
            f"[bold]Revised.[/bold] Now on iteration {values.get('iteration', '?')}.\n"
            f"Auto-lint: "
            + ("[green]clean[/green]" if lint.get("clean") else "[yellow]flagged[/yellow]")
            + f"\nStatus: {values.get('status')}\n\n"
            f"View the new draft: [cyan]python -m mare review show {thread_id}[/cyan]",
            title="Revision complete",
            border_style="yellow",
        )
    )


@review_app.command("reject")
def review_reject(
    thread_id: str = typer.Argument(...),
    reason: str = typer.Option("", "--reason"),
    reviewer: str = typer.Option("anonymous", "--reviewer"),
) -> None:
    """Archive the draft without publishing."""
    values = _resume(thread_id, {"action": "reject", "reason": reason, "reviewer": reviewer})
    console.print(
        Panel(
            f"Status: [red]{values.get('status')}[/red]\n"
            f"Reason: {values.get('rejection_reason') or '(none)'}",
            title="Rejected",
            border_style="red",
        )
    )


if __name__ == "__main__":
    app()
