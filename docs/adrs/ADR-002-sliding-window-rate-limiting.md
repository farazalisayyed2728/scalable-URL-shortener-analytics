# ADR-002: Atomic Fixed-Window Rate Limiting in Redis

## Status

Accepted

## Context

Public URL creation is rate-limited per client IP to reduce automated abuse.
The default limit is 100 requests in a 60-second period. The counter must be
shared across web workers and containers rather than stored in process memory.

## Considered alternatives

1. **In-process counters:** Each Django process would maintain a separate
   counter, making the effective limit dependent on which worker receives a
   request.
2. **Redis fixed-window counter:** A compact counter with a clear reset
   boundary. It is simple to share and update atomically, but permits bursts
   across adjacent window boundaries.
3. **Sliding-window counter or log:** Smooths boundary behavior but requires
   an algorithm and state representation that the current implementation does
   not provide.

## Decision

Use an atomic Redis fixed-window counter. The window start is aligned to the
Unix epoch in 60-second intervals. A Redis Lua script increments the key,
sets its expiration on first use, and returns its count and remaining TTL.
The request is allowed when the count is at or below the configured limit.

Rate limiting currently applies to URL creation requests and uses the client
IP resolved by the proxy-aware helper. If Redis fails, the default
`RATE_LIMIT_FAIL_OPEN=True` configuration allows the request and logs a
warning; deployments can configure fail-closed behavior.

## Consequences

### Positive

- The counter is shared across processes and containers using the same Redis
  service.
- The increment and first-use expiry are performed atomically.
- Storage is bounded to a counter key per client and window, rather than one
  timestamp per request.

### Negative and trade-offs

- This is not a sliding window. A client can make nearly twice the configured
  limit in a short span by sending requests on both sides of a window
  boundary.
- Fail-open behavior favors API availability over abuse prevention while
  Redis is unavailable.
- Correct client-IP attribution depends on configuring the number of trusted
  proxies accurately.

## Implementation note

The filename retains the original `sliding-window` label for compatibility
with the documentation plan, but the implemented and accepted algorithm is a
fixed window. The algorithm should be changed in code and this record updated
before describing it as sliding-window rate limiting.
