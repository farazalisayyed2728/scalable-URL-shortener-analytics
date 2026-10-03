# ADR-002: Sliding Window Counter Rate Limiting in Redis

## Status
Accepted

## Context
Public URL shortening endpoints are targets for automated abuse, link spamming, and denial-of-service attempts. We require rate limiting to restrict clients to 100 creation requests per 60-second window.

### Considered Alternatives
1. **In-Memory Rate Limiting (Django Process Memory):**
   - *Flaw:* In multi-worker (Gunicorn) or multi-container environments, requests hit different processes, allowing clients to bypass limits by distributing requests across workers.
2. **Fixed-Window Counter in Redis:**
   - *Flaw:* Resets at rigid clock boundaries (e.g., 12:00:00 to 12:01:00). A client can burst 100 requests at 12:00:59 and another 100 requests at 12:01:01, pushing 200 requests within a 2-second span (the 2x boundary burst vulnerability).
3. **Sliding Window Log (Sorted Sets `ZSET`):**
   - *Flaw:* Stores a timestamp for every request. High-throughput endpoints encounter memory bloat storing millions of individual timestamp elements.

## Decision
We implement a **Redis Sliding Window Counter** using atomic Redis pipelines:
- Time is partitioned into 60-second blocks.
- The algorithm estimates traffic by computing:
  $$\text{Current Requests} + \text{Previous Window Requests} \times (1 - \text{Elapsed Window Fraction})$$
- Atomic execution is guaranteed via Redis Lua scripting/pipelines.

## Consequences
### Positive
- Smooth rate-limit enforcement across boundary transitions without 2x burst vulnerability.
- Minimal memory footprint ($O(1)$ memory per client IP: two integer counters).
- Centralized across all container instances.

### Negative / Trade-offs
- An approximation algorithm (maximum 0.05% error margin on rolling traffic boundaries), which is acceptable for API rate limiting.