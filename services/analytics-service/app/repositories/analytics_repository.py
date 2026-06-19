"""Analytics repository — reads from DynamoDB, writes to Aurora PostgreSQL."""

import json
import logging
from datetime import datetime
from typing import Any, Optional

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from app.config import settings

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Handles data sync from DynamoDB claims table to Aurora PostgreSQL."""

    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
        self.claims_table = self.dynamodb.Table(settings.claims_table)
        self.secrets_client = boto3.client(
            "secretsmanager", region_name=settings.aws_region
        )

    def _get_aurora_connection(self):
        """Get Aurora PostgreSQL connection using credentials from Secrets Manager."""
        credentials = self._get_db_credentials()
        return psycopg2.connect(
            host=settings.aurora_host,
            port=settings.aurora_port,
            database=settings.aurora_database,
            user=credentials["username"],
            password=credentials["password"],
        )

    def _get_db_credentials(self) -> dict:
        """Retrieve database credentials from AWS Secrets Manager."""
        if not settings.aurora_secret_arn:
            return {"username": "postgres", "password": "postgres"}

        response = self.secrets_client.get_secret_value(
            SecretId=settings.aurora_secret_arn
        )
        return json.loads(response["SecretString"])

    def scan_claims_from_dynamodb(self) -> list[dict[str, Any]]:
        """Scan all claims from DynamoDB for sync."""
        items = []
        response = self.claims_table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = self.claims_table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        logger.info(f"Scanned {len(items)} claims from DynamoDB")
        return items

    def sync_to_aurora(self, claims: list[dict[str, Any]]) -> int:
        """Write claims data to Aurora PostgreSQL analytics tables."""
        if not claims:
            return 0

        conn = self._get_aurora_connection()
        try:
            with conn.cursor() as cur:
                # Ensure analytics table exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS claims_analytics (
                        claim_id VARCHAR(64) PRIMARY KEY,
                        claim_type VARCHAR(32),
                        status VARCHAR(32),
                        amount DECIMAL(12, 2),
                        fraud_score DECIMAL(5, 4),
                        submitted_at TIMESTAMP,
                        resolved_at TIMESTAMP,
                        processing_time_hours DECIMAL(10, 2),
                        synced_at TIMESTAMP DEFAULT NOW()
                    )
                """)

                # Upsert claims data
                values = []
                for claim in claims:
                    submitted_at = claim.get("submitted_at")
                    resolved_at = claim.get("resolved_at")
                    processing_hours = None
                    if submitted_at and resolved_at:
                        try:
                            sub_dt = datetime.fromisoformat(submitted_at)
                            res_dt = datetime.fromisoformat(resolved_at)
                            processing_hours = (
                                res_dt - sub_dt
                            ).total_seconds() / 3600
                        except (ValueError, TypeError):
                            pass

                    values.append((
                        claim.get("claim_id"),
                        claim.get("claim_type"),
                        claim.get("status"),
                        claim.get("amount"),
                        claim.get("fraud_score"),
                        submitted_at,
                        resolved_at,
                        processing_hours,
                    ))

                execute_values(
                    cur,
                    """
                    INSERT INTO claims_analytics
                        (claim_id, claim_type, status, amount, fraud_score,
                         submitted_at, resolved_at, processing_time_hours)
                    VALUES %s
                    ON CONFLICT (claim_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        amount = EXCLUDED.amount,
                        fraud_score = EXCLUDED.fraud_score,
                        resolved_at = EXCLUDED.resolved_at,
                        processing_time_hours = EXCLUDED.processing_time_hours,
                        synced_at = NOW()
                    """,
                    values,
                )
                conn.commit()
                logger.info(f"Synced {len(values)} records to Aurora")
                return len(values)
        finally:
            conn.close()

    def get_metrics(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        claim_type: Optional[str] = None,
    ) -> dict[str, Any]:
        """Query aggregated metrics from Aurora PostgreSQL."""
        conn = self._get_aurora_connection()
        try:
            with conn.cursor() as cur:
                # Build the query using psycopg2.sql composition. Filter values
                # are passed as bound parameters; the WHERE clause is assembled
                # from composable sql.SQL objects rather than string formatting,
                # so no untrusted input is ever interpolated into the SQL text.
                conditions = []
                params: list[Any] = []

                if date_from:
                    conditions.append(sql.SQL("submitted_at >= %s"))
                    params.append(date_from)
                if date_to:
                    conditions.append(sql.SQL("submitted_at <= %s"))
                    params.append(date_to)
                if claim_type:
                    conditions.append(sql.SQL("claim_type = %s"))
                    params.append(claim_type)

                base_query = sql.SQL(
                    """
                    SELECT
                        COUNT(*) as total_claims,
                        COUNT(*) FILTER (WHERE status = 'approved') as approved_count,
                        COUNT(*) FILTER (WHERE status = 'rejected') as rejected_count,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                        COALESCE(AVG(processing_time_hours), 0) as avg_processing_time_hours,
                        COALESCE(
                            COUNT(*) FILTER (WHERE fraud_score > 0.7)::FLOAT /
                            NULLIF(COUNT(*), 0), 0
                        ) as fraud_detection_rate,
                        COALESCE(
                            COUNT(*) FILTER (WHERE status = 'approved')::FLOAT /
                            NULLIF(COUNT(*), 0), 0
                        ) as approval_rate
                    FROM claims_analytics
                    """
                )

                if conditions:
                    query = base_query + sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conditions)
                else:
                    query = base_query

                cur.execute(query, params)

                row = cur.fetchone()
                return {
                    "total_claims": row[0],
                    "approved_count": row[1],
                    "rejected_count": row[2],
                    "pending_count": row[3],
                    "avg_processing_time_hours": float(row[4]),
                    "fraud_detection_rate": float(row[5]),
                    "approval_rate": float(row[6]),
                }
        finally:
            conn.close()
