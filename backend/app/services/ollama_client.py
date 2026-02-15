"""Optional Ollama LLM client for enhanced name detection verification."""

from __future__ import annotations

import json
import logging
import os

import httpx

from app.services.detector import DetectedEntity

logger = logging.getLogger(__name__)

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OLLAMA_MODEL = "llama3.1:8b"

_VERIFY_PROMPT = """You are a name verification assistant. Given a text and a list of detected entities, determine whether each entity is truly a person name, company/organization name, email, or phone number.

Text:
{text}

Detected entities:
{entities_json}

For each entity, respond with a JSON array of objects, each with:
- "text": the entity text
- "is_valid": true if it's genuinely a name/email/phone, false if it's a false positive
- "entity_type": the corrected type (PERSON, ORG, EMAIL, PHONE)

Respond ONLY with the JSON array, no other text."""


class OllamaClient:
    """Client for optional Ollama LLM-based entity verification.

    Provides enhanced name detection by asking a local LLM to verify
    borderline entity detections from spaCy. Fully optional — the tool
    works without Ollama running.
    """

    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Ollama client.

        Args:
            url: Ollama API URL. Defaults to OLLAMA_URL env var or localhost:11434.
            model: Model name. Defaults to OLLAMA_MODEL env var or llama3.1:8b.
            timeout: HTTP timeout in seconds.
        """
        self._url = url or os.environ.get("OLLAMA_URL", _DEFAULT_OLLAMA_URL)
        self._model = model or os.environ.get("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)
        self._timeout = timeout
        self._client = httpx.Client(timeout=self._timeout)

    def is_available(self) -> bool:
        """Check if Ollama is running and reachable.

        Returns:
            True if Ollama API responds, False otherwise.
        """
        try:
            response = self._client.get(f"{self._url}/api/tags")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            logger.debug("Ollama not available at %s", self._url)
            return False

    def verify_entities(
        self, text: str, entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Ask Ollama to verify detected entities.

        Sends the text and entity list to the LLM for verification.
        Entities marked as invalid by the LLM are filtered out.

        Args:
            text: The original text being analyzed.
            entities: List of entities detected by spaCy/regex.

        Returns:
            Filtered list of entities confirmed by the LLM.
            On any error, returns the original list unchanged.
        """
        if not entities:
            return entities

        entities_for_prompt = [
            {"text": e.text, "type": e.entity_type, "confidence": e.confidence}
            for e in entities
        ]

        prompt = _VERIFY_PROMPT.format(
            text=text,
            entities_json=json.dumps(entities_for_prompt, indent=2),
        )

        try:
            response = self._client.post(
                f"{self._url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()

            result = response.json()
            llm_text = result.get("response", "")
            verified = self._parse_verification(llm_text, entities)
            return verified

        except Exception:
            logger.warning(
                "Ollama verification failed, using original detections",
                exc_info=True,
            )
            return entities

    def _parse_verification(
        self, llm_response: str, original_entities: list[DetectedEntity]
    ) -> list[DetectedEntity]:
        """Parse the LLM's JSON response and filter entities.

        Args:
            llm_response: Raw text response from the LLM.
            original_entities: The original entity list for fallback.

        Returns:
            Filtered entity list based on LLM verification.
        """
        try:
            # Try to extract JSON from the response
            text = llm_response.strip()
            # Handle cases where LLM wraps in markdown code blocks
            if "```" in text:
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    text = text[start:end]

            verified_list = json.loads(text)

            # Build set of valid entity texts
            valid_texts = {
                item["text"]
                for item in verified_list
                if item.get("is_valid", True)
            }

            # Filter original entities
            return [e for e in original_entities if e.text in valid_texts]

        except (json.JSONDecodeError, KeyError, TypeError):
            logger.debug("Could not parse Ollama response, keeping all entities")
            return original_entities
