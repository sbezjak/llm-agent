"""Findings showcase - the deterministic, network-free consolidation of every
documented finding, rendered into the committed pytest-html report.

Why this exists: the live suite (`-m live`) hits a non-deterministic model, so no
single live run ever contains every finding, and a run that surfaced one can be
lost to the next auto-timestamped report. This module instead reads the curated
catalog (reports/findings.json) and logs each finding's full narrative at INFO, so
ONE report shows them all the same way every run. The DETECTOR behaviour behind each
agent finding (F1-F8) is locked separately and replayed against the real captured
replies in tests/checkers/test_deterministic_checkers.py - run that file into the same
report for the verdicts alongside these narratives. F9 is a cross-check of the judge
itself (a live calibration, not a captured-replay detector), so it carries its own
live test rather than a replayed one.

Source of truth: reports/findings.json (hand-maintained; a finding = a distinct
failure mode locked by a test, never a test count). This module also locks that
file's shape so a dropped field or id fails loudly instead of drifting.
"""

import json
import logging
from pathlib import Path

import pytest

logger = logging.getLogger("tests")

pytestmark = pytest.mark.mocked

FINDINGS_FILE = Path(__file__).resolve().parent.parent / "reports" / "findings.json"

_REQUIRED = ("id", "title", "family", "severity", "dimensions", "mechanism", "test", "evidence")


def _load() -> dict:
    return json.loads(FINDINGS_FILE.read_text())


CATALOG = _load()
FINDINGS = CATALOG["findings"]


def test_campaign_overview():
    """Render the campaign header into the report (counts, dimensions, severity)."""
    dims = sorted({d for f in FINDINGS for d in f.get("dimensions", [])})
    sev = {s: sum(1 for f in FINDINGS if f.get("severity") == s) for s in ("high", "medium", "low")}
    logger.info(
        "\n=== AGENT-TESTING FINDINGS OVERVIEW ===\n"
        "findings: %d (%s-%s) - a finding is a distinct failure mode locked by a test\n"
        "SUT: qwen2.5:7b via Ollama (llama3.2 for the F2 type-handling probe)\n"
        "dimensions exercised: %s\n"
        "severity: high=%d medium=%d low=%d\n"
        "each finding was calibrated live (traces read end to end), then locked "
        "detector-side because the live behaviour is non-deterministic - the "
        "detectors are replayed against the captured replies in "
        "tests/checkers/test_deterministic_checkers.py.\n"
        "note: %s",
        CATALOG["count"],
        FINDINGS[0]["id"],
        FINDINGS[-1]["id"],
        ", ".join(dims),
        sev["high"],
        sev["medium"],
        sev["low"],
        CATALOG.get("note", ""),
    )


def test_findings_json_shape():
    """Lock the catalog's shape - a dropped field or duplicate id fails here."""
    ids = [f["id"] for f in FINDINGS]
    assert len(ids) == len(set(ids)), f"duplicate finding ids: {ids}"
    assert CATALOG["count"] == len(FINDINGS), "count does not match the findings list"
    for f in FINDINGS:
        missing = [k for k in _REQUIRED if not f.get(k)]
        assert not missing, f"{f.get('id', '?')}: findings.json entry missing {missing}"


@pytest.mark.parametrize("finding", FINDINGS, ids=lambda f: f["id"])
def test_finding_showcase(finding):
    """Render one finding's full narrative into the report."""
    numbers = finding.get("ablation") or finding.get("probe") or {}
    numbers_block = "\n".join(f"  {k}: {v}" for k, v in numbers.items())
    logger.info(
        "\n=== %s  %s ===\n"
        "family=%s  severity=%s  dimensions=%s\n"
        "--- mechanism ---\n%s\n"
        "--- observed rates ---\n%s\n"
        "--- visibility ---\n%s\n"
        "model=%s  captured=%s\n"
        "test: %s\n"
        "evidence: %s\n"
        "report: %s",
        finding["id"],
        finding["title"],
        finding.get("family"),
        finding.get("severity"),
        ", ".join(finding.get("dimensions", [])),
        finding.get("mechanism"),
        numbers_block or "  (none)",
        finding.get("visibility_note", ""),
        finding.get("model"),
        finding.get("captured"),
        finding.get("test"),
        finding.get("evidence"),
        finding.get("report"),
    )
    # A rendered finding must still carry the fields a reader needs to act on it.
    assert finding["mechanism"], f"{finding['id']}: no mechanism recorded"
    assert finding["severity"] in ("high", "medium", "low"), f"{finding['id']}: bad severity"
