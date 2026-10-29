## Evidence assistant: explain a captured decision context

Open **Evidence assistant** when you want a concise explanation with inspectable sources instead of moving through several screens to assemble one. It can compare the four current response scenarios, review a simulated candidate shipment, explain saved model results or source coverage, describe the driver handoff, and point to the next review workspace.

The factual engine is **Deterministic evidence summary**. Its sentences are authored by the application and populated with values from a captured network and dated reports. It is not an illness model, an autonomous dispatcher or an unrestricted chatbot. It has no tool for approving, holding, releasing, dispatching, refreshing a provider or rewriting scientific metrics.

### Capture context and choose an explanation

| Control | What to do | What happens |
| --- | --- | --- |
| Reload evidence context | Capture the current network and saved evidence again | Clears obsolete answer context and records a new content-addressed snapshot |
| Guided question cards | Choose one of the six supported topics | Selects a topic; this alone does not submit a question or change operations |
| Simulated shipment to review | Choose the candidate trip when reviewing a shipment | Used only for shipment-specific explanations; candidate and approved assignment can differ |
| Explain captured evidence | Request the selected topic for the captured context | Returns only facts from that context, with their source labels and limits |
| Your evidence question / Interpret question | Phrase one supported question in your own words | Rules match the text to one of the same six topics; unsupported or action requests are rejected |
| Export captured answer JSON | Save the displayed answer and citations | Downloads a captured explanation; it does not create an assignment or future live update |
| Suggested workspace links | Open the relevant existing screen | Navigates for review; consequential decisions still require their ordinary explicit forms |

The snapshot identifier ties the answer to captured content and the network revision. Network and assignment fields share a single read-only SQLite transaction. Each report is read independently from a bounded byte snapshot; this is not a globally atomic snapshot of all providers. Source times and the report hashes remain important.

If the network, assignments or report files change, a question using an old snapshot is rejected. Reload the context and inspect it before asking again. Changed topic, shipment or wording marks an already displayed briefing as belonging to the previous request. Do not treat an earlier answer as an explanation of newly edited inputs.

### Six useful topics

- **Compare response scenarios:** inspect cost, unmet demand, selected shipments, solver status and modeled constraints together. Scenario D can substitute eligible lots on fixed trips; this is not automatic rerouting. Scenario C's described holds remain proposals until a separate human approval.
- **Review a simulated shipment:** read candidate lot/truck/temperature and direct modeled exclusions. The current approved assignment may use a different lot. Passing a single-candidate check does not establish aggregate plan feasibility or product safety.
- **Explain model performance:** see the actual historical baseline/model metrics, sampling target and availability limitations. Positivity is not consumer illness probability; no new model is trained.
- **Explain source coverage:** distinguish saved HTTP probes, dated source evidence and numeric observation coverage. Reading a report does not refresh the provider or turn a stale success into a current success.
- **Explain the driver handoff:** distinguish approval, targeted verification, parked attestation, acknowledgment and incident reporting. A report or acknowledgment does not impose a hold or complete every readiness check.
- **Find the next review steps:** follow read-only navigation to the appropriate workspace. A suggestion is not an executed recommendation or an approval.

Expand a fact's evidence details to inspect its source path, available retrieval timestamp, checksum and uncertainty. A missing or unusable report produces an explicit unavailable fact rather than a fabricated metric. CDC evidence stays separate from FSIS outcomes. Historical observations, forecasts, cargo simulation and illustrative thermal projections retain their different meanings.

### Optional Ollama topic selection

The default requires no language model. A technical teammate can explicitly configure an Ollama service at a permitted loopback address. If configured, the interface offers an opt-in checkbox for that request. Only the question text and fixed topic descriptions are sent; operational records, source payloads, actor names and decision tools are not supplied to the model.

The model can return only a supported topic identifier. The server then selects the same authored, cited facts used by the guided questions. Invalid output, tool calls, extra claims, model-identity mismatch, excessive response size or service failure falls back visibly to rules where the question is supported. Offline rehearsal disables the optional model request entirely.

A loopback endpoint does not independently certify how the service runs its model. Configuration is not a successful request, a measured quality evaluation or validated advice. No actual configured model inference has been established by the mocked connector tests. The screen distinguishes **LLM topic selection only** from the deterministic factual engine. No new scientific probability or decision authority comes from enabling it.

### Practice use case

Capture context, choose **Compare response scenarios**, and inspect the cited scenario facts. Open Command to examine the constraints. Return, choose a shipment and request its review. Then ask “Why did the historical baseline beat the model?” and inspect which topic was selected and which measured facts support the answer. Export the briefing if useful for discussion. Make any consequential decision separately in the existing human-review workflow.

If a question is ambiguous or matched to the wrong topic, choose the appropriate guided card instead. Topic matching is not proof that the system understood every intention. Requests such as “approve this plan” do not execute anything; the assistant explains the read-only boundary. For credentials, installation and connector protocol details, a technical teammate can consult docs/evidence_assistant.md and .env.example without putting secrets into chat or Git.
