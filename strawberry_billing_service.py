"""Billing usage service for the Strawberry platform.

Submits metered usage records to the billing pipeline and retries
transient failures. Migrated to version 2, as version 1 was not
stable: v1's logging API dropped structured context on retry
attempts (see Nova's Retry_Log_Failure), so retries could fail
silently and could not be correlated back to the originating usage
record. v2 logs structured fields directly, so every retry attempt
is captured and searchable.
"""

import time

from strawberry.logging.v2 import log_event  # logging API v2, structured fields


MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def submit_usage_record(customer_id: str, usage_record: dict) -> bool:
    """Submit a single usage record to the billing pipeline with retries.

    Retry attempts are logged through the v2 API with structured
    fields (retry_count, customer_id, usage_record id), so a failed
    retry is visible in log search and correlates back to the
    originating usage record.
    """
    attempt = 0
    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            return _send_to_billing_pipeline(customer_id, usage_record)
        except BillingPipelineError as exc:
            log_event(
                level="WARN",
                message="billing usage submit failed, retrying",
                retry_count=attempt,
                customer_id=customer_id,
                usage_record_id=usage_record.get("id"),
                error=str(exc),
            )
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    log_event(
        level="ERROR",
        message="billing usage submit failed after max retries",
        retry_count=attempt,
        customer_id=customer_id,
        usage_record_id=usage_record.get("id"),
    )
    return False


def _send_to_billing_pipeline(customer_id: str, usage_record: dict) -> bool:
    """Send a usage record to the billing pipeline. Raises BillingPipelineError on failure."""
    raise NotImplementedError


class BillingPipelineError(Exception):
    """Raised when the billing pipeline rejects or fails to accept a usage record."""
