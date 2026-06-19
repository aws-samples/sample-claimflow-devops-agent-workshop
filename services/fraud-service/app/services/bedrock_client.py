"""Amazon Bedrock integration — InvokeModel for fraud analysis."""

import json
import logging

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Client for Amazon Bedrock model invocation."""

    def __init__(self):
        self.client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
        self.model_id = settings.bedrock_model_id

    def analyze_claim_for_fraud(self, claim_data: dict) -> dict:
        """Analyze a claim for potential fraud using Claude.

        Args:
            claim_data: Dictionary containing claim details.

        Returns:
            dict with 'score' (0-100), 'risk_level', 'explanation', and 'indicators'.
        """
        prompt = self._build_prompt(claim_data)

        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0.1,
            })

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            content = response_body["content"][0]["text"]

            return self._parse_response(content)

        except Exception as e:
            logger.error(f"Bedrock InvokeModel failed: {e}")
            # Return a conservative default on failure
            return {
                "score": 50,
                "risk_level": "Medium",
                "explanation": "Unable to complete AI analysis. Manual review recommended.",
                "indicators": ["AI analysis unavailable"],
            }

    def _build_prompt(self, claim_data: dict) -> str:
        """Build the fraud analysis prompt."""
        return f"""You are a fraud detection analyst for an insurance company. Analyze the following claim for potential fraud indicators.

Claim Details:
- Claim ID: {claim_data.get('claim_id', 'N/A')}
- Claim Type: {claim_data.get('claim_type', 'N/A')}
- Amount: ${claim_data.get('amount', 0):,.2f}
- Description: {claim_data.get('description', 'N/A')}
- Policy Number: {claim_data.get('policy_number', 'N/A')}
- Incident Date: {claim_data.get('incident_date', 'N/A')}
- Hospital Name: {claim_data.get('hospital_name', 'N/A')}
- Diagnosis: {claim_data.get('diagnosis', 'N/A')}
- Vehicle Details: {claim_data.get('vehicle_details', 'N/A')}
- Incident Location: {claim_data.get('incident_location', 'N/A')}

Respond ONLY with a valid JSON object in this exact format:
{{
    "score": <integer 0-100, where 0 is no fraud risk and 100 is definite fraud>,
    "risk_level": "<Low|Medium|High>",
    "explanation": "<brief explanation of the assessment>",
    "indicators": ["<indicator 1>", "<indicator 2>"]
}}

Rules:
- Score 0-29: Low risk
- Score 30-69: Medium risk
- Score 70-100: High risk
- Consider claim amount relative to claim type
- Look for inconsistencies in the description
- Flag unusually high amounts or suspicious patterns"""

    def _parse_response(self, content: str) -> dict:
        """Parse the model response into structured data."""
        try:
            # Try to extract JSON from the response
            # Handle cases where model wraps JSON in markdown code blocks
            cleaned = content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                json_lines = [l for l in lines if not l.startswith("```")]
                cleaned = "\n".join(json_lines)

            result = json.loads(cleaned)

            # Validate and normalize
            score = max(0, min(100, int(result.get("score", 50))))

            if score >= 70:
                risk_level = "High"
            elif score >= 30:
                risk_level = "Medium"
            else:
                risk_level = "Low"

            return {
                "score": score,
                "risk_level": risk_level,
                "explanation": result.get("explanation", "Analysis complete."),
                "indicators": result.get("indicators", []),
            }

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Failed to parse Bedrock response: {e}")
            return {
                "score": 50,
                "risk_level": "Medium",
                "explanation": "Unable to parse AI response. Manual review recommended.",
                "indicators": ["Parse error in AI response"],
            }
