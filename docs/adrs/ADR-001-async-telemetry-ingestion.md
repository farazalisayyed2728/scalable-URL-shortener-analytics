# ADR-001: Asynchronous Click Ingestion & Eventual Consistency

## Status
Accepted

## Context
A URL shortener's traffic profile is heavily skewed toward reads: over 90% of requests are redirects (`GET /<short_code>`). Target latency for redirects is under 15ms.

Each redirect requires capturing client analytics: IP address, User-Agent (device, OS, browser), referrer, timestamp, and incrementing the total click counter.

Synchronous database writes (`INSERT INTO analytics_click`) introduce several problems:
1. Disk I/O and row-level locks inflate redirect response times to 25–60ms.
2. Under viral traffic spikes (e.g., 5,000 req/sec), PostgreSQL connection pools become exhausted, causing subsequent redirect requests to fail with HTTP 504 Gateway Timeouts.

## Decision
We decouple the redirect response path from telemetry writes using an asynchronous task pipeline:
1. The web server resolves the destination via Redis (Cache-Aside), enqueues a `record_click_event` message to Redis (DB 1), and immediately returns `302 Found`.
2. A separate Celery worker consumes the task, enriches the User-Agent, inserts the record, and increments `ShortURL.total_clicks` using an atomic `F()` expression.
3. If the Celery broker is unreachable, the task enqueue operation is caught and swallowed; telemetry failure must never degrade client redirection.

## Consequences
### Positive
- Sub-5ms redirect responses under high concurrency.
- Database write spikes are smoothed by the broker queue (load leveling).
- Fault isolation: database slowdowns do not block HTTP redirect threads.

### Negative / Trade-offs
- Analytics dashboards display eventual consistency (50–500ms delay between click and dashboard visibility).
- Requires operating and monitoring a background worker pool and Celery task broker.