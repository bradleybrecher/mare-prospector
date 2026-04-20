"""Probe: is Vertex AI routing ready for image generation?

Checks, in order:
  1. VERTEX_PROJECT is set in .env.
  2. Application Default Credentials are resolvable.
  3. A tiny Imagen 4 call succeeds via Vertex.

Does NOT cost much ($0.02-ish for one `imagen-4.0-fast-generate-001` image).
We use `fast` tier to minimize spend on a probe.

Typical failure modes and what they mean:
  - VERTEX_PROJECT empty         → add it to .env and re-run
  - google.auth.exceptions       → `gcloud auth application-default login`
  - 403 PERMISSION_DENIED        → enable Vertex AI API on the project
  - 429 RESOURCE_EXHAUSTED       → quota; request increase in Cloud Console
  - 400 with "publisher model"   → Imagen not allowlisted in your region;
                                   try VERTEX_LOCATION=us-central1
"""

from __future__ import annotations

import sys
from pathlib import Path

from google.genai import errors as genai_errors
from google.genai import types

from mare.config import Settings
from mare.gemini_client import GeminiClient


def main() -> int:
    settings = Settings.load()
    creds = settings.google_application_credentials
    print("[probe] --- Config ---")
    print(f"[probe]   VERTEX_PROJECT                 : {settings.vertex_project or '(not set)'}")
    print(f"[probe]   VERTEX_LOCATION                : {settings.vertex_location}")
    print(f"[probe]   USE_VERTEX_FOR_IMAGES          : {settings.use_vertex_for_images}")
    print(f"[probe]   USE_VERTEX_FOR_TEXT            : {settings.use_vertex_for_text}")
    print(f"[probe]   GOOGLE_APPLICATION_CREDENTIALS : {creds or '(not set — will try ADC)'}")
    print()

    if not settings.vertex_project:
        print("[verdict] VERTEX_PROJECT is empty. Add the following to .env:")
        print("[verdict]   VERTEX_PROJECT=<your-gcp-project-id>")
        print("[verdict]   VERTEX_LOCATION=us-central1")
        print("[verdict] Then re-run this probe.")
        return 2

    if creds is not None and not creds.exists():
        print(f"[verdict] GOOGLE_APPLICATION_CREDENTIALS points to {creds}")
        print("[verdict] but that file does not exist. Check the path in .env.")
        return 3

    try:
        client = GeminiClient.from_vertex_env()
    except RuntimeError as exc:
        print(f"[probe] Config error: {exc}")
        return 3
    except Exception as exc:
        print(f"[probe] Failed to build Vertex client: {type(exc).__name__}: {exc}")
        if creds is None:
            print("[verdict] No service account JSON configured. Either:")
            print("[verdict]   (a) Set GOOGLE_APPLICATION_CREDENTIALS=<path> in .env, or")
            print("[verdict]   (b) Run `gcloud auth application-default login`")
        return 3

    print(f"[probe] Routing: {client.routing_label}")
    print("[probe] Submitting ONE Imagen 4 Fast render (9:16, 1 image)...")
    print()

    try:
        response = client.raw_client.models.generate_images(
            model="imagen-4.0-fast-generate-001",
            prompt=(
                "An empty wooden countertop in soft morning daylight, a single "
                "clear glass of water, editorial restraint, mobile-first 9:16."
            ),
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="9:16",
            ),
        )
    except genai_errors.ClientError as exc:
        code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        print(f"[probe] === REJECTED (HTTP {code}) ===")
        print(f"[probe] {exc}")
        print()
        if code == 403:
            print("[verdict] Vertex auth worked, but the project is NOT authorized")
            print("[verdict] for Vertex AI. Run:")
            print(f"[verdict]   gcloud services enable aiplatform.googleapis.com \\")
            print(f"[verdict]     --project {settings.vertex_project}")
        elif code == 429:
            print("[verdict] Vertex quota exhausted. Check quotas in GCP Console:")
            print("[verdict]   https://console.cloud.google.com/iam-admin/quotas")
        elif code == 400:
            print("[verdict] Request was rejected. If the message mentions")
            print("[verdict] 'publisher model', Imagen isn't allowlisted in your")
            print(f"[verdict] region. Try VERTEX_LOCATION=us-central1 (currently")
            print(f"[verdict] {settings.vertex_location}).")
        return 4
    except genai_errors.ServerError as exc:
        print(f"[probe] Vertex returned transient 5xx: {exc}")
        print("[verdict] Retry in a minute.")
        return 5
    except Exception as exc:
        msg = str(exc)
        print(f"[probe] Unexpected: {type(exc).__name__}: {msg}")
        if "default credentials" in msg.lower() or "adc" in msg.lower():
            print("[verdict] Run `gcloud auth application-default login` and retry.")
            return 6
        return 1

    if not response.generated_images:
        print("[probe] Vertex accepted the call but returned no images.")
        print("[verdict] Likely a safety filter — this is rare for neutral prompts.")
        return 7

    img = response.generated_images[0]
    if not img.image.image_bytes:
        print("[probe] Response had no image bytes.")
        return 8

    artifact_dir = settings.artifact_dir / "_probe"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    out_path = artifact_dir / "vertex_probe.png"
    out_path.write_bytes(img.image.image_bytes)
    size_kib = out_path.stat().st_size / 1024

    print("[probe] === SUCCESS ===")
    print(f"[probe] Wrote {out_path} ({size_kib:.1f} KiB)")
    print()
    print("[verdict] Vertex AI routing works for this project.")
    print("[verdict] Flip USE_VERTEX_FOR_IMAGES=true in .env to use it by default.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
