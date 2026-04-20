"""Tests for Vertex AI routing — config + client factories.

We mock `genai.Client` so no real Vertex / AI Studio calls are made. The
point of these tests is to verify that:

  - `.env` flags route to the right backend
  - missing VERTEX_PROJECT fails loudly (not silently, not lazily)
  - explicit client factories override env
  - routing_label is accurate for logs and CLI output
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _clear_vertex_env(monkeypatch):
    """Each test controls Vertex env explicitly; clear any inherited values.

    The repo-root `.env` may set GOOGLE_APPLICATION_CREDENTIALS / VERTEX_*
    vars. Without clearing, tests couple to the dev machine's config.
    """
    for var in (
        "VERTEX_PROJECT",
        "VERTEX_LOCATION",
        "USE_VERTEX_FOR_IMAGES",
        "USE_VERTEX_FOR_TEXT",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(var, raising=False)


# --- Settings ------------------------------------------------------------


def test_settings_defaults_vertex_off(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.delenv("VERTEX_PROJECT", raising=False)
    monkeypatch.delenv("USE_VERTEX_FOR_IMAGES", raising=False)
    monkeypatch.delenv("USE_VERTEX_FOR_TEXT", raising=False)

    from mare.config import Settings
    s = Settings.load()
    assert s.vertex_project is None
    assert s.vertex_location == "us-central1"
    assert s.use_vertex_for_images is False
    assert s.use_vertex_for_text is False


def test_settings_reads_vertex_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    monkeypatch.setenv("VERTEX_LOCATION", "europe-west4")
    monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", "true")
    monkeypatch.setenv("USE_VERTEX_FOR_TEXT", "yes")

    from mare.config import Settings
    s = Settings.load()
    assert s.vertex_project == "mare-prod"
    assert s.vertex_location == "europe-west4"
    assert s.use_vertex_for_images is True
    assert s.use_vertex_for_text is True


def test_settings_env_bool_accepts_multiple_truthy(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    from mare.config import Settings
    for truthy in ("true", "TRUE", "1", "yes", "on"):
        monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", truthy)
        assert Settings.load().use_vertex_for_images is True
    for falsy in ("false", "0", "no", "off", ""):
        monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", falsy)
        assert Settings.load().use_vertex_for_images is False


def test_require_vertex_raises_clear_error_when_unset(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.delenv("VERTEX_PROJECT", raising=False)

    from mare.config import Settings
    s = Settings.load()
    with pytest.raises(RuntimeError) as exc:
        s.require_vertex(purpose="image rendering")
    msg = str(exc.value)
    assert "VERTEX_PROJECT" in msg
    assert "image rendering" in msg
    assert "gcloud auth application-default login" in msg


def test_require_vertex_passes_when_set(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    from mare.config import Settings
    Settings.load().require_vertex(purpose="testing")  # no raise


# --- GeminiClient factories ---------------------------------------------


def test_from_env_uses_api_key_not_vertex(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        c = GeminiClient.from_env()
        FakeClient.assert_called_once_with(api_key="fake-key")
        assert c.is_vertex is False
        assert "AI Studio" in c.routing_label


def test_from_vertex_env_uses_vertexai_true(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    monkeypatch.setenv("VERTEX_LOCATION", "us-central1")
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        c = GeminiClient.from_vertex_env()
        FakeClient.assert_called_once_with(
            vertexai=True, project="mare-prod", location="us-central1"
        )
        assert c.is_vertex is True
        assert "Vertex" in c.routing_label
        assert "mare-prod" in c.routing_label


def test_from_vertex_env_raises_without_project(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.delenv("VERTEX_PROJECT", raising=False)
    from mare.gemini_client import GeminiClient
    with pytest.raises(RuntimeError, match="VERTEX_PROJECT"):
        GeminiClient.from_vertex_env()


def test_from_vertex_explicit_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "env-project")
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        GeminiClient.from_vertex(project="override-project", location="europe-west4")
        FakeClient.assert_called_once_with(
            vertexai=True, project="override-project", location="europe-west4"
        )


def test_for_images_routes_to_vertex_when_flag_on(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", "true")
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        c = GeminiClient.for_images()
        assert c.is_vertex is True
        FakeClient.assert_called_once_with(
            vertexai=True, project="mare-prod", location="us-central1"
        )


def test_for_images_stays_on_ai_studio_when_flag_off(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", "false")
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        c = GeminiClient.for_images()
        assert c.is_vertex is False
        FakeClient.assert_called_once_with(api_key="fake-key")


def test_for_images_raises_when_flag_on_but_no_project(monkeypatch, tmp_path):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.delenv("VERTEX_PROJECT", raising=False)
    monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", "true")
    from mare.gemini_client import GeminiClient
    with pytest.raises(RuntimeError, match="VERTEX_PROJECT"):
        GeminiClient.for_images()


def test_for_text_routes_independently_from_images(monkeypatch, tmp_path):
    """Text and image routing flags are independent — flip one, not the other."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    monkeypatch.setenv("VERTEX_PROJECT", "mare-prod")
    monkeypatch.setenv("USE_VERTEX_FOR_TEXT", "true")
    monkeypatch.setenv("USE_VERTEX_FOR_IMAGES", "false")
    with patch("mare.gemini_client.genai.Client") as FakeClient:
        from mare.gemini_client import GeminiClient
        t = GeminiClient.for_text()
        i = GeminiClient.for_images()
        assert t.is_vertex is True
        assert i.is_vertex is False
        assert FakeClient.call_count == 2
