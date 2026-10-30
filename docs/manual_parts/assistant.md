## Evidence assistant: explain a captured decision context

Open **Evidence assistant** when you want help understanding a delivery plan or its evidence. Start by typing **chicken** in **Your evidence question**, then click **Ask AEGIS**. The helper offers **Choose what to check** choices; click one to get a cited explanation. A broad word is a starting point, not a failed search or an illness prediction.

The factual engine is **Deterministic evidence summary**. Its sentences are authored by the application and populated with values from a captured network and dated reports. It is not an illness model, an autonomous dispatcher or an unrestricted chatbot. It has no tool for approving, holding, releasing, dispatching, refreshing a provider or rewriting scientific metrics.

### Capture context and choose an explanation

| Control | What to do | What happens |
| --- | --- | --- |
| Reload evidence context | Capture the current network and saved evidence again | Clears obsolete answer context and records a new content-addressed snapshot |
| Guided question cards | Click one of the six supported questions | Immediately requests its explanation; no second click is needed |
| Simulated shipment to review | Choose the candidate trip when reviewing a shipment | Used only for shipment-specific explanations; candidate and approved assignment can differ |
| Get answer | Ask again for the selected question and shipment | Returns facts from the captured context with source labels and limits |
| Your evidence question / Ask AEGIS | Enter 1–400 characters, such as **chicken**, **late truck** or a full question | Matches a supported topic or offers useful choices when the wording is broad or unfamiliar |
| Example questions | Click **Chicken** or another example | Fills in the wording and immediately asks it |
| Export captured answer JSON | Save the displayed answer and citations | Downloads a captured explanation; it does not create an assignment or future live update |
| Suggested workspace links | Open the relevant existing screen | Navigates for review; consequential decisions still require their ordinary explicit forms |

Expand **What this helper can do** for the captured snapshot and technical explanation. Within an answer, expand **Sources & provenance** to inspect source paths, retrieval times, checksums and limitations. The snapshot ties facts to captured content and a network revision; saved source reports retain their own dates.

If the network, assignments or report files change, a question using an old snapshot is rejected. Reload the context and inspect it before asking again. Changed topic, shipment or wording marks an already displayed briefing as belonging to the previous request. Do not treat an earlier answer as an explanation of newly edited inputs.

An action request such as “approve this plan” shows an explanation and **Open Dispatcher desk**. It keeps the evidence context available so you can choose another question. The link opens the decision workspace; it does not approve anything. A stale snapshot or an inconsistent answer instead requires **Reload evidence context**.

### Six useful topics

- **Compare response scenarios:** inspect cost, unmet demand, selected shipments, solver status and modeled constraints together. Scenario D can substitute eligible lots on fixed trips; this is not automatic rerouting. Scenario C's described holds remain proposals until a separate human approval.
- **Review a simulated shipment:** read candidate lot/truck/temperature and direct modeled exclusions. The current approved assignment may use a different lot. Passing a single-candidate check does not establish aggregate plan feasibility or product safety.
- **Explain model performance:** see the actual historical baseline/model metrics, sampling target and availability limitations. Positivity is not consumer illness probability; no new model is trained.
- **Explain source coverage:** distinguish saved HTTP probes, dated source evidence and numeric observation coverage. Reading a report does not refresh the provider or turn a stale success into a current success.
- **Explain the driver handoff:** distinguish approval, targeted verification, parked attestation, acknowledgment and incident reporting. A report or acknowledgment does not impose a hold or complete every readiness check.
- **Find the next review steps:** follow read-only navigation to the appropriate workspace. A suggestion is not an executed recommendation or an approval.

Expand a fact's evidence details to inspect its source path, available retrieval timestamp, checksum and uncertainty. A missing or unusable report produces an explicit unavailable fact rather than a fabricated metric. CDC evidence stays separate from FSIS outcomes. Historical observations, forecasts, cargo simulation and illustrative thermal projections retain their different meanings.

### Optional Ollama topic selection

The default requires no language model. **Advanced matching options** is collapsed when none is configured. A technical teammate can explicitly configure an Ollama service at a permitted loopback address. If configured, the interface offers an opt-in checkbox for that request. Only the question text and fixed topic descriptions are sent; operational records, source payloads, actor names and decision tools are not supplied to the model.

The model can return only a supported topic identifier. The server then selects the same authored, cited facts used by the guided questions. Invalid output, tool calls, extra claims, model-identity mismatch, excessive response size or service failure falls back visibly to rules where the question is supported. Offline rehearsal disables the optional model request entirely.

A loopback endpoint does not independently certify how the service runs its model. Configuration is not a successful request, a measured quality evaluation or validated advice. No actual configured model inference has been established by the mocked connector tests. The screen distinguishes **LLM topic selection only** from the deterministic factual engine. No new scientific probability or decision authority comes from enabling it.

### Practice use case

Type **chicken**, click **Ask AEGIS**, then choose **Compare response scenarios** from the suggested choices. Inspect a fact's sources. Open Command to examine the proposed trips, then return, select a shipment and click **Review a simulated shipment**. Export the captured answer for discussion. Make consequential decisions separately in the human-review workflow.

If a question is ambiguous or matched to the wrong topic, choose the appropriate guided card instead. Topic matching is not proof that the system understood every intention. Requests such as “approve this plan” do not execute anything; the assistant explains the read-only boundary. For credentials, installation and connector protocol details, a technical teammate can consult docs/evidence_assistant.md and .env.example without putting secrets into chat or Git.
