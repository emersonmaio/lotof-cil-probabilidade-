"""Guardas estáticos sobre os workflows do GitHub Actions."""
import re
from pathlib import Path

import pytest
import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows"
FILES = sorted(WF.glob("*.yml"))


def _text(p):
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("p", FILES, ids=lambda p: p.name)
def test_workflow_is_valid_yaml_with_jobs(p):
    doc = yaml.safe_load(_text(p))
    assert doc.get("jobs"), p.name


@pytest.mark.parametrize("p", FILES, ids=lambda p: p.name)
def test_no_workflow_overwrites_repository_history(p):
    t = _text(p)
    assert not re.search(r"(curl|wget)[^\n]*(-o|-O|>)\s*data/lotofacil\.csv", t), p.name


def test_only_freeze_workflow_freezes_portfolios():
    owners = [p.name for p in FILES if re.search(r"freeze_portfolio\.py[^\n]*--seed", _text(p))]
    assert owners == ["freeze-portfolio.yml"]


def test_freeze_workflow_commits_record_and_checks_integrity():
    t = _text(WF / "freeze-portfolio.yml")
    assert "contents: write" in t
    assert "git add results/frozen" in t
    assert "--verify-only" in t
    assert "score_frozen.py" in t and "results/prospective" in t
    assert "--allow-retroactive" not in t
    assert "branches: [main]" in t


def test_workflows_detect_last_contest_dynamically():
    t = _text(WF / "v6.yml")
    assert "HOLDOUT_END=$(" in t
    assert not re.search(r"--holdout-end\s+3\d{3}\b", t)
