"""Runtime configuration loaded from the repo-root `.env` file.

We intentionally walk up from this file's location so the config works whether
the CLI is invoked from `backend/`, from the repo root, or from elsewhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _find_repo_root(start: Path) -> Path:
    """Walk upward looking for the `.env` (or `.git`) marker."""
    for candidate in [start, *start.parents]:
        if (candidate / ".env").exists() or (candidate / ".git").exists():
            return candidate
    return start


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
load_dotenv(REPO_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    gemini_reasoning_model: str
    gemini_fallback_model: str | None
    gemini_temperature: float
    gemini_max_output_tokens: int
    artifact_dir: Path
    log_level: str

    @classmethod
    def load(cls) -> "Settings":
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Copy `.env.example` to `.env` in the repo root "
                "and paste your key from https://aistudio.google.com/app/apikey."
            )

        artifact_dir = Path(os.getenv("ARTIFACT_DIR", "./artifacts"))
        if not artifact_dir.is_absolute():
            artifact_dir = (REPO_ROOT / artifact_dir).resolve()
        artifact_dir.mkdir(parents=True, exist_ok=True)

        raw_fallback = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash").strip()
        fallback_model: str | None = raw_fallback or None
        if fallback_model and fallback_model.lower() in {"none", "off", "disabled"}:
            fallback_model = None

        return cls(
            gemini_api_key=key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            gemini_reasoning_model=os.getenv("GEMINI_REASONING_MODEL", "gemini-2.5-pro"),
            gemini_fallback_model=fallback_model,
            gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            gemini_max_output_tokens=int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")),
            artifact_dir=artifact_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )
