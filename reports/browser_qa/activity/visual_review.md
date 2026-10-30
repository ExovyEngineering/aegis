# Activity history: actual Chrome review

Checked October 29, 2026, America/Chicago. Final `results.json` records
**109 checks passed**, six screenshots and zero unexpected application HTTP,
JavaScript or console errors. Served JavaScript/CSS asset names and browser
version are included in the result.

Every action and fixture write used the verified isolated offline session on
port 8016. Actual control API calls recorded simulated events, an explicit plan
approval, parked status, driver acknowledgment, incident reporting, a dispatcher
instruction and its acknowledgment. Repeated temperature settings intentionally
created enough records for paging; they are not independent physical observations
or a count of real disruptions. Browser history controls, navigation, details and
exports issued no operational POST requests.

Verified actual action and explicit-shipment filtering, unapplied draft inputs,
invalid-input rejection, a valid empty result, coherent older pages and captured
JSON exports matching the exact returned API pages. A deliberately recorded
newer action stayed outside the existing paged snapshot until explicit refresh.
Repeated **Recent activity** clicks refocused the existing panel without silently
refreshing it. Links opened current inspection views and selected the current
candidate trip without replaying a historical action. All nine existing
workspaces retained the shared entry point, while dedicated Drive omitted it.

Two explicitly labeled SQL fixtures in the owned QA database exercised corrupt
and oversized payloads plus naive original timestamps. The UI retained their
internal row identity, original time, metadata errors and unavailable payload
status, and labeled a prefix checksum separately from a full payload checksum.
One browser-injected HTTP 409 tested captured-record retention and explicit
refresh recovery. These fixtures and that response are identified in the result;
neither is an invented real action or a public-provider failure.

The initial failed run and its notes remain in `initial_failed_results.json`,
`initial_failure_notes.md` and the explicitly historical screenshot. That run
found an overly specific QA close-button assertion and a legacy `/api/audit`
JSON parsing failure on the injected corrupt row. The final rerun used the
corrected visibility check and hardened legacy endpoint; no HTTP 500 recurred.

Opened and inspected all six final screenshots: captured desktop history,
unreadable-record evidence, approval filter, explicit paging conflict, mobile
history and mobile instruction evidence. Text, provenance and controls were
readable, error feedback stayed visible, payloads remained contained and no
page-level horizontal overflow was observed. The result records matching
SQLite/sidecar hashes for history-only actions, plus unchanged operator database,
every operator sidecar, dated source fixtures and cache bytes over the whole run.

No public source, real OSRM service or language model was queried. Basemap tiles
are separate browser requests. These checks establish software behavior in a
simulated workflow, not authentication, immutable audit integrity, live transport,
scientific model skill or a timed human presentation.
