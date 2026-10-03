# ADR-003: Cursor Pagination for Click Streams

## Status

Accepted

## Context

`GET /api/urls/<short_code>/clicks/` returns click records for a link. A
high-volume link can accumulate many rows. Offset pagination must walk past
earlier rows as the requested page gets deeper and generally requires a count
query for page-number metadata.

## Decision

Use Django REST Framework's `CursorPagination` for click logs. The queryset is
filtered by short code and ordered by `-clicked_at`; the default page size is
20 and clients may request up to 100. The `analytics_click` table has a
composite B-tree index on `(short_code, -clicked_at)`.

The cursor token is generated and interpreted by DRF. Conceptually, subsequent
requests continue through the ordered click stream from the cursor position;
the application does not expose arbitrary page numbers or calculate a total
row count for this endpoint.

## Consequences

### Positive

- Pagination does not need the total count used by page-number pagination.
- Query work is not proportional to the number of rows skipped by a large
  `OFFSET`; the short-code/time index supports the stream lookup.
- Clients can traverse a large stream using opaque next/previous cursor links.

### Negative and trade-offs

- Clients cannot jump directly to an arbitrary page number.
- Cursor traversal relies on `clicked_at`, which is not unique. The current
  ordering does not add the click row ID as a deterministic tie-breaker, so
  DRF may use an offset among rows with equal timestamps. The implementation
  therefore does not guarantee fully drift-free traversal for timestamp ties
  under concurrent ingestion.
- Index lookup is not literally constant-time; performance depends on the
  database and index, though it avoids scanning and discarding all preceding
  pages as offset pagination does.

## Future consideration

If deterministic ordering across timestamp ties becomes a requirement, add a
unique secondary ordering field such as the click ID and align the database
index with that ordering. Update this record and add pagination tests with
duplicate timestamps before making that change.
