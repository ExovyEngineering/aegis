# Shelf-life projection: scientific contract

AEGIS estimates a **conditional quality budget** from a declared temperature
history. It does not measure molecular freshness, calculate an actual spoilage
rate, establish pathogen growth or clear food for consumption. The implemented
algorithm is deterministic; it is not a trained AI model. No prospective quality
accuracy, validated sensor calibration or physical IoT connection is claimed by
running the demonstration.

## Scientific basis and calibration boundary

Food-quality rates often depend on temperature. Q10 expresses a rate ratio for a
10°C increase; Arrhenius-type relationships are another common empirical
description. These relationships do not establish the underlying mechanism of a
complex food or justify extrapolation to arbitrary temperatures.
[Taoukis, *Modelling food quality*](https://academic.oup.com/fst/article/32/1/38/7818609).

A packaged-chicken study developed quality models using experimental quality
indices and temperature conditions. Its product-specific work supports the need
for measurement and validation; its coefficients and performance are not being
transferred to AEGIS lots. Product, packaging and initial condition matter.
[Yimenu et al., 2019](https://doi.org/10.3382/ps/pez461).

USDA distinguishes bacteria associated with spoilage from disease-causing
organisms, which can be present without visible or sensory deterioration. A
quality clock therefore cannot substitute for a separate safety assessment.
[USDA FSIS](https://ask.fsis.usda.gov/article/Can-bacteria-grow-in-the-refrigerator).

The demonstration chooses Q10=2, reference temperature=4°C and reference
quality-life budget=240 hours. **These are illustrative assumptions, not fitted
poultry parameters, a recommended storage life or a validated use-by date.**
The default Q10 cases 1.5/2/3 are deliberately exposed. The configured 0–30°C
model domain is an implementation assumption, not an experimentally validated
range; observations outside it are unscored. Production use needs a justified,
product-specific temperature domain and calibrated quality endpoint.

## Equivalent age and the forward clock

For product-temperature input T, reference temperature Tref and chosen Q10:

```text
rate(T) = Q10 ^ ((T - Tref) / 10)
equivalent_age = declared_initial_equivalent_age + sum(interval_hours * rate(T))
remaining_reference_hours = max(0, reference_life_hours - equivalent_age)
remaining_hours_at_forecast_temperature = remaining_reference_hours / rate(Tfuture)
```

The engine holds each preceding temperature sample constant until the next
sample or evaluation time, within an explicit maximum gap. This is an assumption
about unobserved intervals, not continuous direct measurement or interpolation.
The initial age and baseline timestamp are declared; the first sample must cover
that baseline. Cooling never reverses consumed equivalent age. Changing the
assumed **future** product temperature can change the forward clock, while the
same historical equivalent age remains intact.

`remaining_quality_hours` is the smallest forward-clock result among the chosen
Q10 cases. It is conservative **among those cases only**. The displayed range is
parameter sensitivity, not a statistical confidence interval or guaranteed bound.
Reference-equivalent hours must not be used directly as travel time when the
chosen future temperature differs from the reference.

The caller must also enforce any manufacturer/use-by limit and all independent
eligibility constraints. A modeled quality estimate can shorten a planning
window; it cannot extend a label date, release a hold or override a recall.

## What the sensor channels mean

`temperature_c` is the declared modeled product-temperature channel.
`ambient_temperature_c` stays separate. If a container-air sensor is used as a
proxy, the profile must explicitly say `container_air_proxy`; the result warns
that product/core temperature is unestablished. Ambient-only data cannot silently
become product temperature. Gateway-reported data need separate device, mapping
and calibration validation; authentication alone does not establish measurement
accuracy or genuine physical traceability.

Humidity (% RH), vibration (declared g) and ethylene (ppm) are retained as context,
with units and numeric bounds. They receive no arbitrary poultry degradation
coefficients. Air RH is not measured product water activity; a vibration reading
needs its instrument definition and a damage relationship. Ethylene response is
commodity-specific: the UC Davis grape fact sheet, for example, distinguishes
humidity, respiration, ethylene and handling effects for that commodity. Such
produce relationships do not establish an ethylene-driven poultry decay model.
[UC Davis grape fact sheet](https://postharvest.ucdavis.edu/produce-facts-sheets/grape).

## Coverage and reproducibility

`evaluate_freshness(readings, profile, evaluation_at)` in
`backend/freshness_kinetics.py` is pure and preserves input records. It requires
timezone-aware timestamps, maintains original timestamp strings, computes elapsed
time in UTC and does not silently sort or deduplicate observations. Missing
temperature/history, duplicates, reversed timestamps, future samples, unsupported
temperatures or a hold interval beyond `max_gap_minutes` produce an unscored
result with null remaining-life fields. Malformed values/units are rejected.

Results carry method version, assumptions, source kinds, covered/uncovered time,
an interval timeline, contextual channels, case sensitivity, limitations and
primary-source links. A missing-data result is excluded from model-driven FEFO
and rescue eligibility; it is not replaced by a fresh default clock. All four
channels remain distinguishable from simulated data and weather forecasts.

Tests check analytical rate identities, irreversibility, sensitivity cases,
timezone offsets, coverage gaps and malformed data. These are software/mathematical
checks, not a product challenge study or measured predictive performance. Sources
were consulted October 30, 2026; no observations or calibration data were acquired
from these references.
