# Browser acceptance evidence

The authoritative completed run is `final/results.json`, captured October 26, 2026 with the installed Chrome browser. All **26 checks passed**. Earlier folders retain observed failures and intermediate screenshots; they are not the final result.

Verified desktop Command/Evidence/Model, actual OSM tile loading, farm route generation, multi-origin fleet routing, capacity sensitivity, illustrative refrigeration-fault response, mobile layout, explicit approval and driver acknowledgment/incident reporting. The route experiment produced two active farm routes and three regional routes across two origins. Reducing capacity to one 100 kg truck exposed 2,400 kg of unmet demand with zero reported hard-constraint violations.

No uncaught JavaScript errors or application resource failures were present in the final run. A cosmetic browser `/favicon.ico` request returned 404. The earlier broken Leaflet marker assets and map teardown error were corrected and the full sequence was rerun. A loaded base map does not certify road data coverage or truck-safe navigation.

Screenshots were inspected for stable route lines, legible layouts and the parked-use driver warning. Both Route Lab and Drive had no document-level horizontal overflow at a 390 x 844 viewport. The workflow created 12 simulated assignments in an isolated database, then recorded an acknowledgment and incident report. The user's operational database was not changed by browser QA.

## Reproduce

`scripts/browser_qa.mjs` uses `playwright-core` installed separately under `.tools/browser-qa`, plus an existing Chrome executable. It does not add production dependencies or download a browser. Set `AEGIS_CHROME_PATH` if the installed Chrome path differs.

Start a separate backend on `127.0.0.1:8001` with `AEGIS_DB_PATH` pointing to a disposable database, then run:

```powershell
.tools/node.exe scripts/browser_qa.mjs --base-url http://127.0.0.1:8001 --workflow --route-lab --run final
```

The script rejects workflow mutations on any other URL. It resets the isolated simulated network and exercises UI controls. Normal map-tile access requires network permissions. The production app on port 8000 is not reset or approved by this test.
