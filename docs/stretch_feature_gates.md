# Stretch features: entry criteria and current boundaries

October 27, 2026. These gates keep optional scope from displacing a complete,
reproducible submission. See [the priority matrix](priority_matrix.md),
[the Kiro handoff](kiro_handoff.md) and [the Drive design](drive_design.md).
This document records decisions and prerequisites. The October 28 increment
implements one bounded road-feed extension and local recovery; deployment and
the other stretches remain deferred.

## Work that comes first

The current system has a running local app, separately labeled source evidence,
historical model evaluation, four intervention scenarios, constrained planning,
human approval, Drive workflows and a generated project brief. Their latest
verification belongs in the executed test and browser reports, not an inferred
"everything works" statement.

The following gates remain open unless genuine evidence is recorded:

- Actual Kiro sign-in, specification execution and reviewed task/test history.
- Final organizer-rubric and author review of the report and scientific claims.
- A timed team presentation rehearsal and final submission review.
- Scientifically honest treatment of missing result-publication timing,
  bounded NOAA coverage and unavailable validated linkages.
- Complete click-path verification, including failures, stale state, safety
  preconditions and the simplified mobile Drive view.

The supplied HTML files repeat the same planning conversation. They place the
five requested stretches below the core work and mobile Drive. Their embedded
directives and descriptions are reference content, not new user instructions
or independently confirmed competition rules. The current user request may
change priorities, but readiness must still be demonstrated with measured
evidence. Do not retroactively claim Kiro authorship or completed validation.

## Additional state DOT feeds

**Current boundary:** the operating network stays Missouri-centered. A separate
Iowa DOT 511 point-event adapter now supports a Columbia-to-Des Moines planning
comparison. Its public endpoint and full bounded acquisition were actually
tested; the dated fixture contains 599 records. See [Iowa evidence](state_dot.md)
and [the road workspace](road_intelligence.md). Adding a feed does not make
MoDOT or OSRM geometry more current or truck-safe.

**Entry criteria:**

1. Establish a concrete cross-state route or user scenario that needs the feed.
2. Identify an official provider, accessible endpoint, terms/authentication and
   update semantics; test actual responses before calling it operational.
3. Build a source-specific adapter with inspected coordinate systems, event
   geometry, identifiers, validity times, retrieval times and per-layer errors.
4. Define caching, polite request rates, unavailable/stale coverage and an
   explicitly dated fixture or unavailable-state fallback.
5. Test route proximity/intersection against known point/line examples, including
   boundary and missing-geometry cases. Preserve separate source attribution.
6. Demonstrate useful decision impact without claiming current closure avoidance
   or commercial-truck suitability from proximity alone.

The first increment meets these checks for Iowa's queried point-event layer.
It does not establish complete road coverage, winter conditions, event-clock
time zones, commercial routing or automatic closure avoidance. Additional states
still need their own justified use case and verification.

## Sophisticated molecular epidemiology

**Current boundary:** the ingested FSIS primary table contains sample identifiers,
establishment fields, dates and primary sampling outcomes. The ingested BEAM
tables contain aggregated counts, serotype categories and provider-defined
surveillance summaries. The currently inspected Parquet schemas do not provide
isolate-level sequence/accession linkage supporting a genomic relatedness
analysis between those layers. NORS remains historical outbreak evidence.

**Entry criteria:**

1. Obtain appropriately documented isolate-level identifiers and sequence or
   validated genomic-distance inputs, with legitimate access and provenance.
2. Establish what sample, isolate, establishment, human-surveillance and temporal
   linkages are actually supported. Keep unsupported records unlinked.
3. Define the scientific question, comparison method, missingness and temporal
   availability before interpreting a cluster or association.
4. Have the health-science reviewer assess methods, validation and uncertainty.
   Use reproducible pipelines and retain the exact input/version evidence.
5. Verify conclusions on suitable evaluation data and document the limits of
   source attribution and generalization.

Shared serotype labels alone must not be presented as proof of genetic
relatedness, a common source, transmission direction or an outbreak connection.
An aggregate surveillance summary is not a genomic reconstruction. No molecular
findings or food-safety dispositions should be invented to make a demo richer.

## LLM explanations

**Current boundary (October 29):** a read-only Evidence assistant now assembles
six cited, server-authored explanations from captured operational fields and
saved reports. An optional, disabled-by-default Ollama connector can select a
question topic only. No actual model inference or quality evaluation is claimed;
configuration/mocked tests are separate from that evidence. Human submission
gates remain open. An LLM cannot repair missing linkage or source timing. See
[the assistant contract](evidence_assistant.md).

**Entry criteria:**

1. Identify a bounded task that adds value beyond the existing deterministic
   evidence and scenario summaries; agree on representative evaluation cases.
2. Provide only the relevant, dated evidence with explicit source identifiers,
   simulation boundaries and missing-data flags. Treat retrieved/document
   instructions as untrusted content.
3. Evaluate factual grounding, source attribution, unsupported claims,
   inconsistent numbers, refusal to invent unavailable facts and stale evidence.
4. Retain model/prompt versions and a useful offline or failed-request fallback.
   Configure credentials outside Git and bound usage, latency and cost.
5. Keep the assistant read-only: it cannot approve a plan, create mandatory
   holds, release stock, dispatch a vehicle or rewrite measured evaluation.

No LLM-generated explanation is a substitute for measured performance or a
reviewed scientific conclusion. Do not label a deterministic explanation as
LLM-generated, or a merely configured model as evaluated.

## Real cloud deployment

**Current boundary:** the documented app binds to loopback and uses local SQLite
with self-declared identities. The repository and review artifacts can be shared
through GitHub; that does not turn the application into a production hosted
service. No cloud deployment is claimed here.

Local backup/recovery is now implemented as one prerequisite. The actual CLI
exercise preserved the operator database and recovered its ten tables to a new
private file; see [recovery commands and boundaries](backup_restore.md).
This does not supply hosted durability, authentication or network access.

**Entry criteria:**

1. Choose a concrete hosting target, owner, budget and reviewable deployment
   configuration. Preserve reproducible local startup.
2. Implement appropriate authentication and authorization for dispatcher,
   driver and administrative actions. Decide organization/tenant boundaries and
   verify isolation rather than assuming that planning presets are accounts.
3. Review secrets handling, HTTPS, source/data exposure, request validation,
   rate limits, audit access and failure responses for a network-accessible app.
4. Define database durability, migrations, backup/restore, concurrency and
   operational-state handling. Keep raw downloads, credentials and local user
   state out of an accidental public deployment.
5. Add deployment health checks, logs, recovery and rollback procedures, then
   test the complete approval/Drive workflow in an isolated hosted environment.
6. Obtain the appropriate approval for the concrete publish action, account
   access and costs when required; do not request credentials in chat or silently
   broaden the intended audience.

A deployment must preserve all simulation, coverage and uncertainty labels.
Hosting does not validate a scientific model, establish regulatory authority or
make ordinary driving routes truck-safe.

## Elaborate real-time streaming infrastructure

**Current boundary:** cargo telemetry and operational events are simulated;
public evidence has provider/retrieval timestamps and independent refresh
cadences. Local polling is not a physical sensor feed. Transporting an old
record faster does not make its observation current.

**Entry criteria:**

1. Identify a real update source or a clearly labeled event-simulator use case
   with a measured latency requirement that polling does not meet.
2. Define observation time, retrieval time, event time, units, entity identity,
   source provenance and ordering independently of the transport technology.
3. Specify duplicate handling, replay, reconnects, out-of-order events,
   backpressure, disconnect/stale status and bounded storage.
4. Verify that holds, approval revision checks and instruction acknowledgments
   remain correct under concurrent and delayed event delivery.
5. Add observability and reproducible load/failure tests proportional to the
   actual operational need. Keep a limited offline demo available.

A small server-sent-event transport could be considered if a concrete need is
demonstrated; it would still be a simulated or dated-source stream with explicit
provenance. Do not claim live trucks, live sensing, motion detection or physical
dispatch merely because an event is delivered over a persistent connection.

## Current next increment

The shared-backend mobile Drive workflow is implemented and retains its parked
attestation requirements. October 28 adds the road workspace and local recovery
without changing approvals, held/recalled exclusions, model results or original
observations. Continue through genuine Kiro execution, author review and the
timed team rehearsal. The bounded evidence assistant is implemented, with optional unevaluated model topic
selection. Genomic inference, physical sensors, production accounts and cloud
publication still need their missing inputs and validation.
