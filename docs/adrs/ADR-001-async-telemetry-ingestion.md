# ADR-001: Asynchronous Click Ingestion and Eventual Consistency

## Status

Accepted

## Context

Every successful short-code redirect can produce a click record containing the
short code, event ID, timestamp, client IP, User-Agent, and referrer. User-Agent
metadata is enriched by the analytics worker. Persisting the event inline with
the redirect would add database work to a response whose primary purpose is to
send the visitor to the destination.

## Decision

The redirect view resolves the destination, creates a UUID event ID, submits a
`record_click_event` task to Celery, and returns an HTTP 302 without waiting for
the task to finish. Redis database 1 is the default Celery broker; Redis
database 0 is used for the URL cache.

The worker enriches the User-Agent, inserts a click row, and increments
`ShortURL.total_clicks` using a database `F()` expression. The event ID has a
unique database constraint to guard against duplicate task delivery. Celery
tasks use late acknowledgement and retry failures up to three times with
jittered delays.

If task submission raises an exception, the redirect is still returned and a
warning is logged. After task retries are exhausted, the task failure hook
logs a critical quarantine-style record. It does not persist the failed event
to a durable dead-letter queue.

## Consequences

### Positive

- Database ingestion does not block the redirect response.
- Broker buffering can absorb short-lived differences between click arrival
  and worker throughput.
- Unique event IDs and atomic counter expressions help prevent duplicate
  counts and lost increments during concurrent processing.

### Negative and trade-offs

- Click analytics are eventually consistent and may not include the latest
  redirect immediately.
- If the broker is unavailable at enqueue time, the redirect succeeds but its
  event is not queued.
- If worker retries are exhausted, the failure is logged but no durable
  dead-letter queue currently retains the event.
- Click creation and counter increment are separate database operations, not a
  single transaction; failure between them can leave the record and denormalized
  count inconsistent until reconciled.
- The design requires operating and monitoring a Celery worker and Redis
  broker.

No latency or throughput target is recorded here because the repository does
not include reproducible benchmark results for those figures.
