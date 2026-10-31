# Sensor ingestion contract

No physical IoT platform is connected or validated in this release. The working
replay is explicitly simulated. The optional HTTP gateway accepts separately
labeled gateway-reported packets; all linked logistics entities remain fictional.

## Connect a local gateway

1. Generate a secret of at least 32 characters outside source control and set
   `AEGIS_SENSOR_INGEST_TOKEN` in the server's environment or local `.env`.
   Never put this value in browser code, screenshots, reports or Git.
2. Create a freshness session using `POST /api/freshness/sessions`, with
   `scenario: "gateway"`, the displayed integer `expected_network_revision`,
   `shipment_id`, and explicit `devices` bindings. Each binding contains
   `device_id`, a known simulated `lot_id` and `profile`.
3. The profile declares `started_at` with timezone, reference temperature/life,
   initial equivalent age, Q10/cases, forecast product temperature, maximum hold
   interval and `temperature_basis` (`product` or `container_air_proxy`). These
   are assumptions; the endpoint does not accept a claim of validated calibration.
   Supply a baseline observation at that exact baseline time.
4. Send `POST /api/freshness/telemetry` with the server-side header
   `Authorization: Bearer <your token>`. Body:

```json
{
  "session_id": "<UUID returned by session creation>",
  "frames": [{
    "device_id": "reefer-product-probe",
    "event_id": "unique-observation-id",
    "observed_at": "2026-10-31T09:00:00-05:00",
    "temperature_c": 4.0,
    "ambient_temperature_c": 27.0,
    "humidity_percent": 78.0,
    "vibration_g": 0.03,
    "ethylene_ppm": 0.02
  }]
}
```

The example is synthetic protocol documentation, not a sensor observation. Use
your actual observation timestamps and declared units; do not replay its date as
if it were current. Product temperature is nullable, but a missing value makes
the affected quality calculation unscored. Ambient does not fill it in.

## Integrity and operating bounds

- At most 128 frames per batch, 12,000 frames per experiment, and 4,096 readings
  per device/model history. Repeated identical event IDs remain idempotent at the
  limits. A new frame beyond a limit is rejected before insertion; no history is
  silently truncated or age reset. Production high-frequency archives and
  checkpointing are outside this bounded student demo.
- Device times must increase strictly within a binding. An exact retry preserves
  the original observation/retrieval row. Conflicting IDs, reversed time, unknown
  devices, nonfinite numbers or invalid channel bounds fail visibly. A batch is
  atomic; a later bad frame rolls back its earlier inserts.
- UTC is used for elapsed time; original timestamp strings and server retrieval
  timestamps are preserved. Gateway observations over five minutes in the future
  are rejected. A future observation inside that tolerance is still not scored
  before its time arrives.
- Replay and gateway sources cannot be mixed. Forty retained experiments are
  supported per local database; use an existing experiment or a separate fresh
  rehearsal database for another controlled demonstration.
- Gateway clocks consume elapsed time within the explicit bounded hold
  assumption. Gaps make coverage unscored. No new packet means no invented
  measurement. Polling every five seconds reads stored state rather than claiming
  that a physical sensor was sampled every five seconds.
- Only a separate identified, versioned approval replaces operational
  assignments. New readings require renewed review. Sensor credentials do not
  grant dispatcher approval, modify holds or certify food safety.

The loopback application and self-declared reviewer identity do not provide
production role authentication, remote ingress isolation or device certification.
Use the existing offline rehearsal and tests before connecting any real platform.
