# Recorded operational activity

The activity inspector explains saved rows from the local `audit` table. It is
read-only and never performs a recorded action again. Its purpose is to connect
what a user clicked with what the application actually recorded, without
reconstructing historical values that were never stored.

## API contract

Mount `create_activity_router(db_path, root=ROOT)` from `backend/activity.py`.
The path and root may be callables so existing test/runtime configuration stays
dynamic. `GET /api/activity` accepts one value for each supported query:

| Query | Meaning |
| --- | --- |
| `limit` | Records returned on this page; default 25, range 1–100 |
| `action` | One ID from the returned `actions` catalog; omit for all saved actions |
| `shipment_id` | Exact valid explicit top-level `shipment_id` in a readable object payload |
| `cursor` | The opaque `next_cursor` from a preceding page with the same filters |

Unknown action filters, unsupported/repeated query parameters, invalid shipment
identifiers, invalid limits and malformed/mismatched cursors return HTTP 422.
Stored actions outside the catalog remain visible with an unrecognized-action
label and their readable payload. They are not silently reclassified.

The response includes:

| Field | Meaning |
| --- | --- |
| `available`, `read_only`, `operational_state_modified` | True, true and false for a successful history read |
| `generated_at` | UTC time this page was generated, distinct from each recorded action time |
| `records` | Saved entries in descending audit-ID order; ID order is not a corrected or inferred timestamp order |
| `actions` | Known action IDs and plain-language labels for the filter |
| `snapshot_latest_id`, `snapshot_id` | Frozen upper audit ID and digest of the captured bounded stored representation |
| `total_matching`, `returned_records` | Filtered row count within that snapshot and number on this page |
| `next_cursor` | Older-page cursor, or null at the end |
| `filters` | The exact applied action and shipment filters |
| `limitations` | Interpretation, linkage, provenance and capture boundaries |

Each record preserves its numeric ID, valid original timestamp string, actor,
action, authored summary, scope and readable object payload. A suggested existing
workspace is a navigation hint, not an instruction to apply a decision.
`citation` identifies an internal audit row; it is not an official source claim.
Unknown or unavailable metadata stays explicit. `timestamp_raw` preserves bounded
original text separately when the timestamp is invalid or lacks a time zone; no
time zone is invented and action times are never rewritten to retrieval time.

## What history can and cannot establish

- Approval entries record their saved scenario/proposal/reviewer fields. They do
  not contain the entire historical assignment set or its count. The inspector
  does not invent those values from current assignments.
- Event entries currently save the request, including any expected revision or
  preview hash supplied by Command. They do not save every applied field change
  or assignment-removal count. A captured event-impact receipt remains a separate
  artifact with its own evidence.
- Reset entries have an empty payload. The inspector does not infer their
  resulting revision or number of removed trips.
- Driver quick reporting records both an incident and a quick-report link. Two
  audit rows are not two independent incidents. Acknowledgment is not proof of
  departure, delivery or physical inspection.
- Routes, scenario recomputation, source refresh, proposal creation and unsaved
  route calculations do not currently create audit entries. Missing rows do not
  prove a button was unused or failed.
- Shipment filtering excludes global approvals, nested assignment references,
  lot-related lists and truck relationships unless a readable payload contains
  that exact top-level shipment ID. It is deliberately incomplete rather than a
  guessed traceability join.

The audit is a local simulated operational history. Reviewer names are
self-declared, and the SQLite file is mutable. The inspector does not turn it
into authenticated identity, an append-only security log, regulatory authority
or a complete event-sourcing ledger.

## Stable pages and changed history

The first request captures all bounded audit rows up to the current maximum ID.
Older-page cursors retain that upper bound and a content digest. New higher IDs
are excluded until an explicit reload, keeping page counts/order consistent.
Changing the inspected representation or deleting a captured row invalidates
the cursor with HTTP 409 and
requires a fresh snapshot. Actor, timestamp, action, storage type, length and
captured payload representation contribute to identity.

Cursor checksums detect accidental or altered context; they are not a signature
or authorization boundary. The API is already a local read interface. Filters
must match the cursor; the page size may change within the bounded range.

## Read and memory bounds

The module validates the runtime profile before opening SQLite with URI
`mode=ro`, sets `query_only=ON` and `trusted_schema=OFF`, and reads in one
transaction. It never calls the normal initializer, creates directories,
repairs schema, seeds a network, records an action or calls providers/models.
Missing/corrupt databases or unsupported schema produce an explicit HTTP 503.

Captures are limited to 10,000 rows, 16 MiB of inspected text, 2,048 bytes per
metadata field, and 32 KiB per payload. Numeric IDs must remain exactly
representable by the TypeScript client (`2^53 - 1` maximum). Exceeding the overall
inspection limits gives an unavailable response rather than partial totals.

Malformed JSON, duplicate keys, nonfinite numbers, non-object JSON and non-text
storage produce visible per-row payload errors; other rows remain available.
`payload_sha256` is the hash of the exact complete bytes only when those bytes
were within the inspection bound. Oversized payloads have no claimed full hash:
`payload_prefix_sha256` identifies only the inspected prefix, `payload_bytes`
gives the stored full length, and `payload_error` explains that the full payload
was not read. Snapshot identity consequently does not detect edits beyond an
oversized payload's captured prefix when its full length stays identical.

## Verification

The legacy `/api/audit` endpoint retains its cold-start initialization behavior,
then uses the bounded normalizer for its newest 100 rows. Valid legacy fields
retain their shape; unreadable payloads become null with an explicit error and
appropriately scoped hash metadata. A corrupt row no longer hides other valid
entries or makes the initial app load fail. This compatibility path is distinct
from the strictly non-initializing `/api/activity` reader.

`tests/test_legacy_audit.py` checks that compatibility, strict JSON errors,
oversized prefixes, unchanged files and newest-100 bounds even when the full
history exceeds the new inspector's global capture budget.

`tests/test_activity.py` exercises all known action filters, exact shipment
linkage, unknown stored actions, complete-source hashing, corrupt/oversized
rows, metadata/time-zone preservation, bounded captures, stable paging with new
rows, changed/deleted-history rejection, malformed/tampered cursors, invalid
queries, missing/corrupt storage, read-only SQL and database fingerprints.
These checks establish software behavior, not independent incident counts,
security certification, source availability or scientific model performance.
