"""Check loopback readiness and prewarm the real verifier using synthetic data."""
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx2

from app.config import Settings
from app.models import Claim, Passage
from app.verification import EvidenceGroundedVerifier
from app.verifier_provider import ChatCompletionProvider


def wait_until_ready(base_url: str, *, seconds: float = 120) -> float:
    url = urlsplit(base_url)
    if url.scheme != 'http' or url.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('Prewarming is restricted to a local loopback verifier.')
    start = time.perf_counter()
    with httpx2.Client(timeout=2, trust_env=False, follow_redirects=False) as client:
        while time.perf_counter() - start < seconds:
            try:
                if client.get(f'{url.scheme}://{url.netloc}/health').status_code == 200:
                    return time.perf_counter() - start
            except httpx2.HTTPError:
                pass
            time.sleep(1)
    raise TimeoutError('Local verifier did not become healthy. Start scripts/start_local_verifier.ps1 and retry.')


def main():
    settings = Settings.from_env()
    waited = wait_until_ready(settings.verifier_base_url)
    print(f'Verifier healthy after {waited:.2f}s. Warming the instruction prefix with synthetic evidence…', flush=True)
    start = time.perf_counter()
    result = EvidenceGroundedVerifier(ChatCompletionProvider(settings)).verify(
        Claim(text='The study recruited 312 adult participants.'),
        [Passage(document_id=uuid4(), document_name='warmup.pdf', page_number=1, text='The trial enrolled 312 adults.')],
    )
    if result.classification.value != 'supported':
        raise RuntimeError('Warmup completed but the synthetic check did not return support. Inspect the verifier before demonstrating.')
    print(f'Validated warmup completed in {time.perf_counter() - start:.2f}s. Keep the server running; results are not cached by the application.')


if __name__ == '__main__':
    main()
