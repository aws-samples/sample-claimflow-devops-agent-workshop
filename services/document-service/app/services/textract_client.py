"""Amazon Textract integration — AnalyzeDocument and DetectDocumentText."""

import logging
from typing import Optional

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class TextractClient:
    """Client for Amazon Textract document analysis."""

    def __init__(self):
        self.client = boto3.client("textract", region_name=settings.aws_region)

    def detect_text(self, bucket: str, s3_key: str) -> dict:
        """Detect text in a document stored in S3.

        Returns:
            dict with 'raw_text' and 'confidence' keys.
        """
        try:
            response = self.client.detect_document_text(
                Document={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": s3_key,
                    }
                }
            )

            blocks = response.get("Blocks", [])
            lines = []
            confidences = []

            for block in blocks:
                if block["BlockType"] == "LINE":
                    lines.append(block.get("Text", ""))
                    confidences.append(block.get("Confidence", 0.0))

            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            return {
                "raw_text": "\n".join(lines),
                "confidence": avg_confidence / 100.0,  # Normalize to 0-1
            }

        except Exception as e:
            logger.warning(f"Textract DetectDocumentText failed: {e}")
            raise

    def analyze_document(self, bucket: str, s3_key: str, feature_types: Optional[list] = None) -> dict:
        """Analyze document with specified feature types.

        Args:
            bucket: S3 bucket name.
            s3_key: S3 object key.
            feature_types: List of feature types (TABLES, FORMS, etc.).

        Returns:
            dict with 'raw_text', 'tables', 'forms', and 'confidence' keys.
        """
        if feature_types is None:
            feature_types = ["TABLES", "FORMS"]

        try:
            response = self.client.analyze_document(
                Document={
                    "S3Object": {
                        "Bucket": bucket,
                        "Name": s3_key,
                    }
                },
                FeatureTypes=feature_types,
            )

            blocks = response.get("Blocks", [])
            lines = []
            confidences = []

            for block in blocks:
                if block["BlockType"] == "LINE":
                    lines.append(block.get("Text", ""))
                    confidences.append(block.get("Confidence", 0.0))

            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            return {
                "raw_text": "\n".join(lines),
                "confidence": avg_confidence / 100.0,
                "blocks": blocks,
            }

        except Exception as e:
            logger.warning(f"Textract AnalyzeDocument failed: {e}")
            raise
