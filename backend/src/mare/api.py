"""HTTP API for the Next.js dashboard — thin wrapper around the content pipeline.

Two endpoints that matter for the MVP:
  GET  /api/channels        → distribution channels and their render specs
  POST /api/render          → server-sent-events stream of a full Short render

Shape of SSE events (JSON-encoded in the `data:` field):
  { type: "status",  message: "Generating script..." }
  { type: "script",  script: {... ShortScript model ...} }
  { type: "prompts", prompts: {... ImagePromptSet model ...} }
  { type: "beat",    beat: N, image_url: "/api/artifact/...", prompt: "..." }
  { type: "done",    slug: "...", summary: "..." }
  { type: "error",   message: "..." }

The frontend consumes this with EventSource. Each event updates a single
section of the UI so the user watches the pipeline unfold, rather than
staring at a spinner for two minutes.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import re
from typing import Any, AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from mare.config import Settings
from mare.content.brief import ContentBrief
from mare.content.channels import CHANNELS, DEFAULT_CHANNEL_ID, get_channel
from mare.content.image_prompts import generate_image_prompts
from mare.content.image_renderer import IMAGEN_TIERS, _merge_negative
from mare.content.shorts import generate_short_script


logger = logging.getLogger(__name__)


# --- Request / response schemas -----------------------------------------


class RenderRequest(BaseModel):
    """Inputs the dashboard form collects."""

    topic: str = Field(..., min_length=4, max_length=120)
    audience: str = Field("high_end_client")
    proof_point: str | None = Field(None, max_length=400)
    call_to_action: str | None = Field(None, max_length=160)
    channel: str = Field(DEFAULT_CHANNEL_ID)
    tier: str = Field("standard", pattern="^(fast|standard|ultra)$")


class ChannelSummary(BaseModel):
    id: str
    label: str
    target_aspect: str
    render_aspect: str
    is_mobile_first: bool
    platform_notes: str


class HealthResponse(BaseModel):
    status: str
    vertex: dict[str, Any]


# --- App setup ----------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title="MaRe Studio API",
        description="Thin HTTP layer over the MaRe content pipeline.",
        version="0.1.0",
    )

    # CORS: the Next.js dev server runs on :3000, this on :8000. In production
    # the dashboard would be served from the same origin, but for dev we allow
    # the common Next.js ports.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ----- Health / config -----------------------------------------------

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        s = Settings.load()
        return HealthResponse(
            status="ok",
            vertex={
                "project": s.vertex_project,
                "location": s.vertex_location,
                "text": s.use_vertex_for_text,
                "images": s.use_vertex_for_images,
                "auth_mode": s.vertex_auth_mode if s.vertex_project else None,
            },
        )

    @app.get("/api/channels", response_model=list[ChannelSummary])
    def channels() -> list[ChannelSummary]:
        return [
            ChannelSummary(
                id=c.id,
                label=c.label,
                target_aspect=c.target_aspect,
                render_aspect=c.render_aspect,
                is_mobile_first=c.is_mobile_first,
                platform_notes=c.platform_notes,
            )
            for c in CHANNELS
        ]

    @app.get("/api/tiers")
    def tiers() -> dict[str, dict[str, str]]:
        # Rough per-image cost on Vertex (US pricing, subject to change).
        cost_usd = {
            "fast": "~$0.02 / image",
            "standard": "~$0.04 / image",
            "ultra": "~$0.08 / image",
        }
        notes = {
            "fast": "Batch & social b-roll. Fast, cheap, occasional prompt drift on complex scenes.",
            "standard": "Default. Best quality/cost for published content.",
            "ultra": "Hero shots, postcard fronts, campaigns.",
        }
        return {
            t: {"model": IMAGEN_TIERS[t], "cost": cost_usd[t], "notes": notes[t]}
            for t in ("fast", "standard", "ultra")
        }

    # ----- Artifact serving ---------------------------------------------
    # The pipeline writes to ARTIFACT_DIR. The dashboard needs to display
    # rendered images, so expose that folder as read-only static content
    # under /api/artifact/... — scoped so it can't escape the artifact root.

    @app.get("/api/artifact/{subpath:path}")
    def serve_artifact(subpath: str) -> FileResponse:
        s = Settings.load()
        root = s.artifact_dir.resolve()
        candidate = (root / subpath).resolve()
        # Directory-traversal guard: candidate must stay inside root.
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid path") from exc
        if not candidate.exists() or not candidate.is_file():
            raise HTTPException(status_code=404, detail="Artifact not found")
        return FileResponse(candidate)

    # ----- Render pipeline (SSE) ----------------------------------------

    @app.post("/api/render")
    async def render(req: RenderRequest):  # noqa: D401 — handler returns SSE response
        """Stream the full render as server-sent events."""

        async def events() -> AsyncGenerator[dict[str, str], None]:
            # Force an immediate flush so the browser knows the stream is live
            # BEFORE any blocking work starts (Gemini script draft ~15s, Imagen
            # renders ~5–30s each with quota backoff). Without this, some
            # intermediaries (Chrome's cross-origin streaming, proxies) hold
            # bytes until the first "real" chunk and the UI looks stuck.
            yield {
                "data": json.dumps({"type": "status", "message": "Connected — preparing pipeline..."})
            }
            async for evt in _render_pipeline(req):
                yield {"data": json.dumps(evt)}

        # ping=1 sends ": ping\n\n" every second, which keeps the TCP stream
        # warm and gives the browser's fetch reader something to chew on even
        # when the pipeline is idle (quota backoff, long LLM calls).
        # X-Accel-Buffering=no tells nginx/Next.js rewrite proxies NOT to
        # buffer — without it, dev-server proxies hold the entire stream
        # until it closes and the UI looks dead.
        return EventSourceResponse(
            events(),
            ping=1,
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache, no-transform",
            },
        )

    return app


# --- Pipeline runner ----------------------------------------------------


def _slugify(s: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return slug[:60] or "untitled"


def _to_jsonable(obj: Any) -> Any:
    """Recursively convert dataclasses / pydantic / Paths into JSON-safe dicts.

    `ShortScript` and `ImagePromptSet` are stdlib dataclasses. Channels are
    dataclasses too. Pydantic models go through `.model_dump()`. Paths become
    strings. Everything else we trust the default JSON encoder to handle.
    """
    if hasattr(obj, "model_dump"):  # pydantic v2
        return obj.model_dump()
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(v) for v in obj]
    # Paths, enums, anything else — fall back to str representation for safety.
    if hasattr(obj, "__fspath__"):
        return str(obj)
    return obj


async def _render_pipeline(req: RenderRequest) -> AsyncGenerator[dict[str, Any], None]:
    """Drive the pipeline on a worker thread, yielding SSE events as we go.

    `generate_short_script`, `generate_image_prompts`, and `render_image_prompts`
    are blocking. Running them directly on the event loop would freeze every
    other request. We offload via `asyncio.to_thread` so the ASGI worker stays
    responsive (and multiple users could render in parallel someday).
    """
    settings = Settings.load()

    try:
        ch = get_channel(req.channel)
    except Exception as exc:
        yield {"type": "error", "message": f"Unknown channel: {req.channel}"}
        logger.warning("Unknown channel in render request: %s", exc)
        return

    try:
        brief = ContentBrief(
            topic=req.topic,
            audience=req.audience,  # type: ignore[arg-type]
            proof_point=req.proof_point,
            call_to_action=req.call_to_action,
        )
    except Exception as exc:
        yield {
            "type": "error",
            "message": f"Invalid brief: {exc}",
        }
        logger.warning("Invalid brief in render request: %s", exc)
        return

    slug = _slugify(req.topic)
    out_dir = settings.artifact_dir / "content" / "shorts" / slug / ch.id
    out_dir.mkdir(parents=True, exist_ok=True)

    yield {
        "type": "status",
        "message": f"Starting render on {settings.vertex_auth_mode if settings.use_vertex_for_text else 'AI Studio'}...",
    }

    # --- 1. Script --------------------------------------------------------
    yield {"type": "status", "message": "Drafting Short script with Gemini 2.5 Pro..."}
    try:
        script = await asyncio.to_thread(generate_short_script, brief)
    except Exception as exc:
        logger.exception("Script generation failed")
        yield {"type": "error", "message": f"Script generation failed: {exc}"}
        return

    (out_dir / "script.md").write_text(script.to_markdown())
    yield {"type": "script", "script": _to_jsonable(script)}

    # --- 2. Image prompts ------------------------------------------------
    yield {"type": "status", "message": "Writing per-beat image prompts..."}
    try:
        prompts = await asyncio.to_thread(generate_image_prompts, script, channel=ch)
    except Exception as exc:
        logger.exception("Image prompt generation failed")
        yield {"type": "error", "message": f"Image prompt generation failed: {exc}"}
        return

    (out_dir / "image_prompts.md").write_text(prompts.to_markdown())
    yield {"type": "prompts", "prompts": _to_jsonable(prompts)}

    # --- 3. Render beats one at a time, emitting as they land -----------
    # We render one beat per `asyncio.to_thread` call so the UI sees
    # progressive results instead of a single 2-minute blob at the end.
    images_dir = out_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    from mare.content.image_renderer import _generate_with_backoff  # local: private helper
    from mare.gemini_client import GeminiClient
    from google.genai import types  # type: ignore

    client = GeminiClient.for_images()
    model = IMAGEN_TIERS.get(req.tier)
    if not model:
        yield {"type": "error", "message": f"Unknown tier: {req.tier}"}
        return

    yield {
        "type": "status",
        "message": (
            f"Rendering {len(prompts.items)} beats via {client.routing_label} "
            f"at {req.tier} tier ({model})..."
        ),
    }

    for item in prompts.items:
        yield {"type": "status", "message": f"Rendering beat {item.beat} of {len(prompts.items)}..."}
        config = types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=ch.render_aspect,
            negative_prompt=_merge_negative(item.negative),
        )
        try:
            response = await asyncio.to_thread(
                _generate_with_backoff,
                client,
                model=model,
                prompt=item.imagen_prompt,
                config=config,
                beat_label=f"beat {item.beat}",
            )
        except Exception as exc:
            logger.exception("Beat %d render failed", item.beat)
            yield {
                "type": "error",
                "message": f"Beat {item.beat} failed: {exc}",
            }
            return

        if not response.generated_images:
            yield {
                "type": "error",
                "message": f"Beat {item.beat}: Imagen returned no image (safety filter?).",
            }
            return
        img_bytes = response.generated_images[0].image.image_bytes
        if not img_bytes:
            yield {
                "type": "error",
                "message": f"Beat {item.beat}: response had no image bytes.",
            }
            return

        out_path = images_dir / f"{ch.id}_beat_{item.beat}.png"
        out_path.write_bytes(img_bytes)
        rel_path = out_path.relative_to(settings.artifact_dir)

        yield {
            "type": "beat",
            "beat": item.beat,
            "image_url": f"/api/artifact/{rel_path.as_posix()}",
            "prompt": item.imagen_prompt,
            "subject": item.subject,
        }

    # --- 4. Done ---------------------------------------------------------
    yield {
        "type": "done",
        "slug": slug,
        "channel_id": ch.id,
        "beat_count": len(prompts.items),
        "artifact_dir": f"/api/artifact/content/shorts/{slug}/{ch.id}/",
    }


# Uvicorn entrypoint: `uvicorn mare.api:app`
app = create_app()
