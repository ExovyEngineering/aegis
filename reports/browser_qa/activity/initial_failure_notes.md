# Initial activity QA failure record

The first actual Chrome run is preserved in `initial_failed_results.json`.
It recorded 97 checks and six screenshots before stopping at the close-control
assertion. The panel had closed correctly; the QA script incorrectly required
an `aria-expanded="false"` attribute on a one-way open button. The corrected
check observes the closed panel, available open control and unchanged POST count.

The same run exposed a separate product error: the two deliberately inserted
corrupt/oversized audit fixtures were handled by `/api/activity`, while the
legacy `/api/audit` parser returned HTTP 500 during normal application loads.
Both HTTP and console failures remain in the saved result. This was an internal
JSON parsing failure caused by explicit QA fixture data, not a public-provider
connection failure. The parent implementation hardened that legacy path before
the successful 109-check final rerun, where no HTTP 500 recurred.

All action and fixture writes used the verified isolated offline database on
port 8016. No operator or public-source mutations were requested. The initial
run ended before its final preservation checks; use the final `results.json`
for measured end-to-end fingerprints after the successful rerun.
