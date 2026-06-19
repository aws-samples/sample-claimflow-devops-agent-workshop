"""Amazon Comprehend integration — DetectEntities and DetectKeyPhrases."""

import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class ComprehendClient:
    """Client for Amazon Comprehend NLP analysis."""

    def __init__(self):
        self.client = boto3.client("comprehend", region_name=settings.aws_region)

    def detect_entities(self, text: str) -> list[dict]:
        """Detect entities in text.

        Returns:
            List of dicts with 'text', 'entity_type', and 'confidence' keys.
        """
        if not text.strip():
            return []

        try:
            # Comprehend has a 5000 byte limit per request
            truncated_text = text[:4900]

            response = self.client.detect_entities(
                Text=truncated_text,
                LanguageCode="en",
            )

            entities = []
            for entity in response.get("Entities", []):
                entities.append({
                    "text": entity["Text"],
                    "entity_type": entity["Type"],
                    "confidence": entity["Score"],
                })

            return entities

        except Exception as e:
            logger.warning(f"Comprehend DetectEntities failed: {e}")
            raise

    def detect_key_phrases(self, text: str) -> list[dict]:
        """Detect key phrases in text.

        Returns:
            List of dicts with 'text' and 'confidence' keys.
        """
        if not text.strip():
            return []

        try:
            truncated_text = text[:4900]

            response = self.client.detect_key_phrases(
                Text=truncated_text,
                LanguageCode="en",
            )

            phrases = []
            for phrase in response.get("KeyPhrases", []):
                phrases.append({
                    "text": phrase["Text"],
                    "confidence": phrase["Score"],
                })

            return phrases

        except Exception as e:
            logger.warning(f"Comprehend DetectKeyPhrases failed: {e}")
            raise
