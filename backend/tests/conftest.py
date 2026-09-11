import pytest


@pytest.fixture(autouse=True)
def offline_verifier_default(monkeypatch):
    """Existing regressions use the exact baseline; semantic tests inject providers."""
    monkeypatch.setenv("EVIDENCELENS_VERIFIER_MODE", "exact")
