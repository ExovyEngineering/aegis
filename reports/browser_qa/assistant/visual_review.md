# Evidence assistant browser review

Reviewed October 29, 2026 against the running operator application at `http://127.0.0.1:8000`, using Chrome 156.0.8078.48. Reproduce with `.tools/node.exe scripts/browser_assistant_qa.mjs` after starting the application.

All 81 automated checks passed. The run recorded nine screenshots, zero browser JavaScript errors, and zero unexpected HTTP failures. The six guided explanations used actual captured backend facts and retained their citations, uncertainty, snapshot, and simulation labels. Model numbers were compared with the saved evaluation report rather than expected constants. The downloaded JSON matched its captured response, and typed question text was omitted from that export.

The reviewer opened `desktop-cited-scenario-fact.png`, `mobile-assistant-intro.png`, and `mobile-cited-model-briefing.png`. Desktop provenance, file hashes, scenario distinctions, and interpretation limits are readable. At 390 by 844 pixels the cards, export control, snapshot wrapping, measured model explanation, and uncertainty box fit the viewport. The horizontally scrolling bottom navigation keeps the active assistant tab visible; the automated check also reached all nine navigation items. Navigation to Model evaluation and Sources & evidence was exercised and returned to the assistant.

One actual request to perform a dispatch action returned the expected HTTP 422 and cleared the previous context until explicit reload. A stale-context HTTP 409 and a foreign-fact HTTP 200 were injected only in the browser to exercise defensive behavior; neither demonstrates an actual server conflict or a provider result. Both were rejected as intended. These expected cases are recorded separately in `results.json`.

No source refresh, dispatch, hold, approval, reset, driver event, or other operational mutation was requested. The operator SQLite file remained 143,360 bytes with SHA-256 `d8d062d68a73f7923a3f7893b578fbf0b9b1fea29978c014ebb0abca58424560` before and after. SQLite WAL, SHM, and journal sidecars were absent both times.

The actual engine reported no configured Ollama service. Guided answers and the typed question used deterministic facts and rule-based topic selection. No actual language model was queried or evaluated; this review does not establish model quality, live sensor operation, truck-route suitability, or predictive consumer illness risk.

See `results.json`, `context_snapshot.json`, `actual-guided-answers.json`, and the screenshots in this directory for the captured evidence. Browser response injections are explicitly identified in the results.
