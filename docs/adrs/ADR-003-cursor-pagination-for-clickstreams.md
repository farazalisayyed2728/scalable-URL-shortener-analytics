# ADR-003: Keyset (Cursor) Pagination for Append-Only Telemetry Streams

## Status
Accepted

## Context
The endpoint `GET /api/urls/<short_code>/clicks/` exposes the raw stream of click events for a given short code. High-volume links can accumulate millions of click records.

### The Problem with Offset Pagination (`OFFSET 100000 LIMIT 20`)
1. **$O(N)$ Database Degradation:** PostgreSQL must scan all 100,000 preceding rows/index pointers and discard them before returning the 20 requested rows. Query latency increases linearly with page depth.
2. **Page Drift:** As new clicks are inserted continuously at the head of the table, existing rows shift down by one position per insert. A user paginating to Page 2 will see duplicate rows that were already displayed on Page 1.

## Decision
We implement **Keyset (Cursor) Pagination** (`StandardCursorPagination`) for raw click streams:
- Queries execute as:
  ```sql
  SELECT * FROM analytics_click 
  WHERE short_code = $1 AND (clicked_at, id) < ($cursor_time, $cursor_id) 
  ORDER BY clicked_at DESC, id DESC 
  LIMIT 20;