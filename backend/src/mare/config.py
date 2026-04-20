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


_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in _TRUTHY


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

    # --- Vertex AI routing (optional) --------------------------------------
    # When `use_vertex_*` is True, the corresponding renderer routes through
    # Google Cloud Vertex AI instead of the AI Studio key. This bypasses AI
    # Studio free-tier caps and uses your GCP billing. Auth is Application
    # Default Credentials — run:
    #   gcloud auth application-default login
    # on the machine where this pipeline runs, OR set
    # GOOGLE_APPLICATION_CREDENTIALS to a service account JSON path.
    vertex_project: str | None
    vertex_location: str
    use_vertex_for_text: bool
    use_vertex_for_images: bool
    # Optional: absolute path to a service account JSON key. If set, it
    # overrides ADC. The google-genai SDK auto-reads GOOGLE_APPLICATION_CREDENTIALS,
    # but we surface it explicitly so we can validate and log the auth mode.
    google_application_credentials: Path | None

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

        vertex_project = (os.getenv("VERTEX_PROJECT") or "").strip() or None
        vertex_location = (os.getenv("VERTEX_LOCATION") or "us-central1").strip()
        use_vertex_for_text = _env_bool("USE_VERTEX_FOR_TEXT", default=False)
        use_vertex_for_images = _env_bool("USE_VERTEX_FOR_IMAGES", default=False)

        raw_creds = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
        gac: Path | None = None
        if raw_creds:
            gac_path = Path(raw_creds).expanduser()
            if not gac_path.is_absolute():
                gac_path = (REPO_ROOT / gac_path).resolve()
            gac = gac_path
            # Re-export the resolved absolute path so the google-auth library
            # picks it up even if the original was relative to the repo root.
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(gac)

        return cls(
            gemini_api_key=key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            gemini_reasoning_model=os.getenv("GEMINI_REASONING_MODEL", "gemini-2.5-pro"),
            gemini_fallback_model=fallback_model,
            gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            gemini_max_output_tokens=int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS", "2048")),
            artifact_dir=artifact_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            vertex_project=vertex_project,
            vertex_location=vertex_location,
            use_vertex_for_text=use_vertex_for_text,
            use_vertex_for_images=use_vertex_for_images,
            google_application_credentials=gac,
        )

    def require_vertex(self, *, purpose: str) -> None:
        """Raise a clear error if Vertex is required but not configured.

        `purpose` is a short label like 'image rendering' that gets spliced
        into the error so the caller knows WHY Vertex is being demanded.
        """
        if not self.vertex_project:
            raise RuntimeError(
                f"Vertex AI is required for {purpose} but VERTEX_PROJECT is "
                f"not set. Add VERTEX_PROJECT=<your-gcp-project-id> to .env "
                f"(and optionally VERTEX_LOCATION=us-central1). Then set up "
                f"auth one of two ways:\n"
                f"  (a) Service account JSON: set GOOGLE_APPLICATION_CREDENTIALS=<path> in .env\n"
                f"  (b) gcloud CLI: run `gcloud auth application-default login`"
            )

        # If GOOGLE_APPLICATION_CREDENTIALS is set, validate the file exists.
        # A stale path is a common failure mode and the SDK's error message
        # for it is cryptic ("DefaultCredentialsError: ..."). Be explicit.
        if self.google_application_credentials is not None:
            if not self.google_application_credentials.exists():
                raise RuntimeError(
                    f"GOOGLE_APPLICATION_CREDENTIALS points to "
                    f"{self.google_application_credentials}, but that file "
                    f"does not exist. Check the path in .env."
                )

    @property
    def vertex_auth_mode(self) -> str:
        """Human-readable auth mode for logs/CLI output."""
        if self.google_application_credentials is not None:
            return f"Service Account ({self.google_application_credentials.name})"
        return "Application Default Credentials (gcloud)"
