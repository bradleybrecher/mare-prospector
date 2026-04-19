"""Video-generation adapters — HeyGen first, room for more later.

Why this is an adapter and not a full integration:
- HeyGen is paid and account-bound. We don't want the Gemini client to depend on it.
- The shape of a HeyGen "create video" request is stable enough to freeze now, but
  the actual API call belongs in a queue worker (one per brand account).
- This module produces a ready-to-send job spec (JSON) from a MaRe ShortScript.
  A thin `HeyGenClient.submit()` is included but defaults to DRY-RUN unless a
  `HEYGEN_API_KEY` is set. This lets the pipeline operate end-to-end offline.

When HEYGEN_API_KEY is configured later, flip `dry_run=False` and the spec is
POSTed to `https://api.heygen.com/v2/video/generate`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from mare.content.shorts import ShortScript


# MaRe default avatar + voice IDs. Replace with the actual IDs once a MaRe avatar
# has been created in HeyGen. These placeholders let the spec validate structurally.
DEFAULT_AVATAR_ID = "mare_placeholder_avatar"
DEFAULT_VOICE_ID = "mare_placeholder_voice_en_us_female_warm"


@dataclass
class HeyGenJobSpec:
    """A ready-to-POST HeyGen v2 video-generation request."""

    title: str
    dimension: dict[str, int] = field(default_factory=lambda: {"width": 1080, "height": 1920})
    video_inputs: list[dict[str, Any]] = field(default_factory=list)
    callback_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "title": self.title,
            "dimension": self.dimension,
            "video_inputs": self.video_inputs,
        }
        if self.callback_id:
            payload["callback_id"] = self.callback_id
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), indent=2)


def script_to_heygen_spec(
    script: ShortScript,
    *,
    avatar_id: str = DEFAULT_AVATAR_ID,
    voice_id: str = DEFAULT_VOICE_ID,
    vertical: bool = True,
) -> HeyGenJobSpec:
    """Translate a MaRe ShortScript into a HeyGen job spec.

    Each voiceover beat becomes one `video_inputs` clip — HeyGen concatenates
    them. The avatar is pinned top-right for mobile readability; replace layout
    once there's a MaRe-approved on-screen frame.
    """
    dimension = {"width": 1080, "height": 1920} if vertical else {"width": 1920, "height": 1080}
    clips: list[dict[str, Any]] = []
    for i, beat in enumerate(script.voiceover):
        vo_text = beat.get("vo", "").strip()
        if not vo_text:
            continue
        clips.append(
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "scale": 0.7,
                    "avatar_style": "circle",
                    "offset": {"x": 0.35, "y": -0.4},
                },
                "voice": {
                    "type": "text",
                    "voice_id": voice_id,
                    "input_text": vo_text,
                },
                "background": {
                    "type": "color",
                    "value": "#F4EDE3",
                },
                "metadata": {
                    "mare_beat_index": i + 1,
                    "b_roll_hint": beat.get("b_roll", ""),
                },
            }
        )
    return HeyGenJobSpec(
        title=script.hook[:80] or "MaRe Short",
        dimension=dimension,
        video_inputs=clips,
        callback_id=f"mare-short-{abs(hash(script.hook)) % 10_000_000}",
    )


@dataclass
class HeyGenSubmission:
    dry_run: bool
    payload: dict[str, Any]
    response: dict[str, Any] | None = None


class HeyGenClient:
    """Thin client. Dry-run unless HEYGEN_API_KEY is set.

    We intentionally don't make HeyGen a hard dependency — it's one of several
    possible downstream video providers. To wire it up for real later:
      1. Set HEYGEN_API_KEY in `.env`.
      2. Create a MaRe avatar and voice in HeyGen; put their IDs into
         `DEFAULT_AVATAR_ID` / `DEFAULT_VOICE_ID`.
      3. `HeyGenClient().submit(spec)` will POST to the v2 endpoint.
    """

    API_URL = "https://api.heygen.com/v2/video/generate"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("HEYGEN_API_KEY", "").strip() or None

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    def submit(self, spec: HeyGenJobSpec) -> HeyGenSubmission:
        payload = spec.to_payload()
        if not self.is_live:
            return HeyGenSubmission(dry_run=True, payload=payload)

        # Real submission path. Imported lazily so httpx isn't mandatory for dry-runs.
        import httpx

        headers = {
            "X-Api-Key": self.api_key or "",
            "Content-Type": "application/json",
        }
        response = httpx.post(self.API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return HeyGenSubmission(dry_run=False, payload=payload, response=response.json())
