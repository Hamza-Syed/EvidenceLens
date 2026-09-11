"""Chat-completions transport, usable with local or hosted compatible providers."""
import json
import logging

import httpx2

from .config import Settings
from .errors import VerifierOutputError, VerifierUnavailableError

logger = logging.getLogger(__name__)


def generation_schema(value):
    """Keep structural constraints portable; enforce size bounds in Pydantic.

    Repeated bounded strings inside bounded arrays can exceed local grammar limits.
    Output token/byte limits still bound transport and the full schema is checked locally.
    """
    if isinstance(value, dict):
        return {key: generation_schema(item) for key, item in value.items()
                if key not in {"minLength", "maxLength", "minItems", "maxItems"}}
    if isinstance(value, list):
        return [generation_schema(item) for item in value]
    return value


class ChatCompletionProvider:
    def __init__(self, settings: Settings, *, transport: httpx2.BaseTransport | None = None):
        self.settings = settings
        self.transport = transport

    def complete(self, *, system: str, data: str, schema: dict) -> str:
        headers = {}
        key = self.settings.verifier_api_key.get_secret_value()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        body = {
            "model": self.settings.verifier_model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": data}],
            "temperature": 0, "max_tokens": 1600, "stream": False,
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "evidence_verdict", "strict": True, "schema": generation_schema(schema),
            }},
        }
        try:
            with httpx2.Client(timeout=self.settings.verifier_timeout_seconds, transport=self.transport,
                               trust_env=False, follow_redirects=False) as client:
                with client.stream("POST", self.settings.verifier_base_url.rstrip("/") + "/chat/completions",
                                   headers=headers, json=body) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    for part in response.iter_bytes():
                        raw.extend(part)
                        if len(raw) > 100000:
                            raise VerifierOutputError("The verification provider returned an oversized response.")
            envelope = json.loads(raw)
            choice = envelope["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete or refused completion")
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("Missing structured completion")
            return content
        except httpx2.HTTPError as exc:
            logger.warning("verifier_transport_failure type=%s", type(exc).__name__)
            raise VerifierUnavailableError("The verification provider is unavailable or timed out. Check its configuration and retry.") from exc
        except (KeyError, IndexError, AttributeError, TypeError, ValueError) as exc:
            logger.warning("verifier_envelope_rejected type=%s", type(exc).__name__)
            raise VerifierOutputError("The verification provider returned an invalid response.") from exc
