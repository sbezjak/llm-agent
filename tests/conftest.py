import asyncio
import datetime as dt
from pathlib import Path

import pytest
import respx
from httpx import Response

from llm_agent.providers.ollama import OllamaProvider
from llm_agent.runners.run import SUT_MODEL


def pytest_configure(config):
    """Rewrite the pytest-html output path to a unique UTC-timestamped file so
    no run ever overwrites another (a structural guarantee). A
    descriptive path passed explicitly (e.g. --html=reports/report-findings.html)
    is preserved - only the default is auto-renamed - so a report meant to be
    committed keeps its name."""
    if not hasattr(config.option, "htmlpath"):
        return
    config.option.self_contained_html = True
    if config.option.htmlpath not in (None, "reports/report.html"):
        return
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    reports = Path("reports")
    reports.mkdir(exist_ok=True)
    config.option.htmlpath = str(reports / f"report-{ts}.html")


def pytest_collection_modifyitems(items):
    """Every live test depends on warm_sut_model, so a cold backend can never
    masquerade as an agent failure."""
    for item in items:
        if item.get_closest_marker("live"):
            item.fixturenames.insert(0, "warm_sut_model")


@pytest.fixture(scope="session")
def warm_sut_model():
    """Fire one trivial generate at SUT_MODEL before any live test runs.
    Model load can eat the provider's whole 60s budget (the first live run can
    die on httpx.ReadTimeout with the model unloaded), so the warm-up
    gets its own generous timeout. Sync + asyncio.run because a session
    fixture cannot share pytest-asyncio's function-scoped event loop."""
    asyncio.run(OllamaProvider(model=SUT_MODEL, timeout=300.0).generate("Reply with the word: ok"))


@pytest.fixture
def script_chat():
    """Mock /api/chat with a fixed sequence of assistant messages (the
    scripted model). Returns the respx route so tests can assert call_count.
    Use inside a @respx.mock test."""

    def _script(*messages: dict):
        return respx.post("http://localhost:11434/api/chat").mock(
            side_effect=[Response(200, json={"message": m, "done": True}) for m in messages]
        )

    return _script
