"""
Shared pytest fixtures for the transcription engine test suite.

All fixtures here are available to every test file in tests/.
"""

import configparser
import os

import pytest
from unittest.mock import MagicMock

from app.services.factory import reset_registry


# ---------------------------------------------------------------------------
# Registry management
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_registry():
    """Reset the ASR provider registry before and after every test."""
    reset_registry()
    yield
    reset_registry()


# ---------------------------------------------------------------------------
# Infrastructure stubs
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_data_writer():
    """Return a MagicMock that satisfies the DataWriter interface."""
    return MagicMock()


# ---------------------------------------------------------------------------
# Test assets
# ---------------------------------------------------------------------------

TEST_AUDIO = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "test",
    "testAssets",
    "audio.mp3",
)


@pytest.fixture
def test_audio_path():
    """Absolute path to the bundled test audio file.

    The test is skipped if the asset is not present (e.g. in a minimal CI
    checkout that doesn't include large binary files).
    """
    if not os.path.exists(TEST_AUDIO):
        pytest.skip(f"Test asset not found: {TEST_AUDIO}")
    return TEST_AUDIO


# ---------------------------------------------------------------------------
# Config patching
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    """Write a temporary config.ini and patch ``settings.config`` to use it.

    Usage::

        def test_something(tmp_config):
            tmp_config({"asr_provider": "whisper", "summarize": "False"})
            # settings.config now reflects the overrides above
    """
    def _make(overrides: dict) -> str:
        config_path = tmp_path / "config.ini"
        parser = configparser.ConfigParser()
        parser["DEFAULT"] = overrides
        with open(config_path, "w") as fh:
            parser.write(fh)

        # Re-read the section so callers get a real SectionProxy (not a dict).
        fresh = configparser.ConfigParser()
        fresh.read(str(config_path))

        # Patch settings so the app code sees the test config.
        from app.config import settings
        monkeypatch.setattr(settings, "config", fresh["DEFAULT"])
        return str(config_path)

    return _make


# ---------------------------------------------------------------------------
# Common env-var helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def dummy_openai_key(monkeypatch):
    """Inject a dummy OPENAI_API_KEY so import-time key checks don't raise."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-dummy-openai")


@pytest.fixture
def dummy_deepgram_key(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dummy-deepgram")


@pytest.fixture
def dummy_google_key(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "dummy-google")


@pytest.fixture
def dummy_claude_key(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "dummy-claude")
