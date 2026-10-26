# Operational feature browser evidence

Real installed Chrome exercised the app on **127.0.0.1:8001 only**, using the isolated `.tools/browser-qa/features.sqlite` database. The operator's port 8000 app and database were not reset or changed by this rehearsal.

The final run passed **50 assertions** (including HTTP read/action status assertions), with eight screenshots. It verified custom longitude editing through a partial minus sign; invalid-input disablement; canonical custom routes without mutating presets/dispatch state; explicit scenario approval; reporting against the selected nonfirst truck trip; dispatcher identity/reason; versioned incident review/instructions; stale instruction rejection; exact-version driver acknowledgment; human hold removal of affected assignments; release without redispatch; incident resolution with the original reporting snapshot; and the resulting audit events.

Mobile custom editing, Drive and dispatcher views fit a 390-pixel document without horizontal overflow. The final report records zero uncaught JavaScript errors, zero application resource HTTP failures, and zero failed requests. One cosmetic browser-default favicon console 404 remains.

`results.json` contains the actual run time, installed browser version, assertions and screenshots. The earlier failed trial was a Playwright exact-label selector mismatch involving nested select options, not a missing driver control; the corrected test still checks the exact selected shipment ID. `scripts/browser_operations_qa.mjs` reproduces this check after an isolated backend has been started on port 8001. It deliberately hardcodes that QA address and does not mutate port 8000.

Real Kiro sign-in/spec execution is separate and was not performed by this test.
