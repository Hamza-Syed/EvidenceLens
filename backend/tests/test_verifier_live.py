"""Optional model benchmark; no mocks. Requires a configured live verifier endpoint."""
import os

import pytest

from app.config import Settings
from app.models import Claim
from app.verification import EvidenceGroundedVerifier
from app.verifier_provider import ChatCompletionProvider
from test_verification import CASES, passages

pytestmark = [pytest.mark.verifier_model, pytest.mark.skipif(os.environ.get("EVIDENCELENS_TEST_VERIFIER") != "1", reason="Set EVIDENCELENS_TEST_VERIFIER=1 with a running verifier endpoint.")]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_live_verification_benchmark(case):
    verifier = EvidenceGroundedVerifier(ChatCompletionProvider(Settings.from_env()))
    result = verifier.verify(Claim(text=case["claim"]), passages(case["sources"]))
    assert result.classification == case["expected"], result.explanation
