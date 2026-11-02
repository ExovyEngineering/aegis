## Sources & evidence: understand where each claim comes from

**Use this workspace when you need to answer:** What data do we actually have? When was it obtained? Is a displayed number a real observation, a forecast, a historical summary, or a simulation? What failed or remains missing?

Open **Sources & evidence** in the main navigation. The screen contains the USDA county-context comparison, the ingested-data explorer, the NOAA coverage audit, import results, public-source cards, recall notices, connectivity results, and the supplied-file inventory. It is an evidence workspace. Selecting a county or filtering a source does not change inventory, dispatch a vehicle, impose a hold, or retrain the model.

### Five labels to understand before reading the screen

| Label or term | Plain-language meaning | What it does not establish |
|---|---|---|
| Observed historical weather | Weather reported for a past station/date and retained from NOAA/NCEI | Temperature inside a refrigerated truck or current weather everywhere along a route |
| Weather forecast | A provider's prediction for upcoming weather | A past observed measurement or a measured cargo temperature |
| Historical reanalysis | A provider's reconstructed historical weather product | The same data stream as NOAA station observations |
| Simulated cargo temperature | Fictional truck/cargo readings used in the digital twin | A connected physical sensor or a verified condition of real poultry |
| Dated fixture / cached response | A saved public response with a retrieval time | A request that just succeeded, complete coverage, or guaranteed current conditions |

**Provenance** means the record of where a value came from and how it was handled. It includes source identity, original filenames and hashes, import status, retrieval time, geographic scope, units, and known limits. A **SHA-256** is a file fingerprint: matching fingerprints support that the same bytes are being used. A fingerprint alone does not prove that a provider is authentic, that a file is complete, or that a scientific linkage is valid.

Read retrieval and observation times separately. A file downloaded today can contain observations from years ago. A forecast valid tomorrow can have been retrieved earlier today. Neither time is a proven FSIS laboratory-result publication date.

### Food access across Missouri

This panel describes the historical operating region using a checked USDA Food Environment Atlas extract. It currently includes **115 Missouri counties/county-equivalents** and **ten measures**. It is useful for explaining the social and retail context in which food distribution happens. It is not a farm safety rating, an outbreak detector, a current demand estimate, or an allocation rule.

| Control | How to use it | Result |
|---|---|---|
| **USDA county** | Choose a county by its displayed name and five-digit FIPS identity | Replaces the main county's values on all ten cards |
| **Compare USDA county** | Choose a second county, or **No comparison** | Adds or removes the second county's value on each card |
| **Definition and denominator** | Expand a measure's explanation | Shows its original field code, definition, and population/housing/store denominator |
| **Download county CSV** | Download the checked local extract | Exports county values and source provenance; numeric source precision is retained |
| **Recheck local extract** | Ask the backend to re-read and verify the saved extract | Checks local integrity; it does not download a new USDA release or refresh weather/recalls |
| **Source provenance and interpretation limits** | Expand the details | Shows source links, original workbook hash, import time, release note, and limitations |
| **Retry USDA context** | Available after a failed read | Retries the local checked extract; it cannot repair a corrupt source automatically |

The values displayed in the cards may be rounded to two decimal places. The CSV retains numeric source precision. The export is a table of this checked historical extract, not a current list of customers or deliveries.

The following ten variables are implemented:

| Source code | Vintage | What the value describes |
|---|---|---|
| `LACCESS_POP19` | 2019 | Estimated people with low foodstore access |
| `PCT_LACCESS_POP19` | 2019 | Percent of total county population with low access |
| `LACCESS_LOWI19` | 2019 | Estimated people with both low income and low access |
| `PCT_LACCESS_LOWI19` | 2019 | Percent of total county population with both conditions; the denominator is not only low-income residents |
| `LACCESS_HHNV19` | 2019 | Estimated housing units without a vehicle and more than one mile from a foodstore |
| `PCT_LACCESS_HHNV19` | 2019 | Percent of all county housing units meeting that definition |
| `GROC20` | 2020 | Grocery stores/supermarkets under the source definition |
| `GROCPTH20` | 2020 | Grocery stores per 1,000 county residents |
| `SNAPS23` | 2023 | Average monthly SNAP-authorized stores under the source definition |
| `SNAPSPTH23` | 2023 | Average monthly SNAP-authorized stores per 1,000 residents |

The access measures combine 2019 store locations with provider-defined historical population, income, and vehicle inputs. They are not ten measurements from one common year. Read the definition before comparing counties, especially when comparing a count with a rate.

**Missing / suppressed** is not zero. In the current extract, `GROC20` and `GROCPTH20` each have 39 missing/suppressed entries. The original missing codes and row identities are retained in the ingestion report. The application does not guess the individual reason or replace those entries with invented observations.

FIPS is the county identity. St. Louis County and St. Louis city are different units, even where original county text is similar. Their FIPS codes prevent them from being collapsed into one location. This feature does not assign simulated destinations to real counties or draw county boundaries on the logistics map.

**Use case: explain regional access without overstating it.** Select Boone County, then compare it with another county. Expand a low-access percentage's denominator, note its year, and export the CSV if the team needs a table. A defensible explanation is, "These are historical county-context measures." It would be unsupported to say that the comparison proves today's demand, the safety of a supplier, or the health risk of a particular shipment.

### Inspect the underlying evidence

This is a read-only browser of recognized, separately ingested tables. The original column names remain visible. The dataset selector identifies both the source and its import availability.

The current local tables checked for this guide are:

| Dataset shown in the selector | Rows | Examples of fields and their purpose |
|---|---:|---|
| **FSIS raw-poultry samples** | 78,607 | Sample/form identifiers, establishment identity/state, project code, collection date, primary Salmonella result, cancellation field, source file |
| **CDC NORS outbreaks** | 66,713 | Year/month/state, transmission mode, etiology, setting, illnesses, hospitalizations, deaths, food/water/animal context |
| **CDC BEAM regional isolates** | 1,650 | Year/quarter/month, HHS region, pathogen, number of isolates, past-two-year average |
| **CDC BEAM source report** | 262,616 | State, source type/site, pathogen, serotype/species, isolates and surveillance summaries |
| **CDC BEAM burden / trajectory** | 484 | Provider-defined food category, serotype, year range, burden/trajectory and illness summaries |
| **CDC BEAM illnesses / outbreaks** | 2,412 | Provider-defined serotype, food category, illness/outbreak counts and year windows |
| **CDC BEAM common serotypes** | 4,818 | Year/quarter/month, pathogen, serotype/species/subgroup and isolate counts |
| **FSIS Missouri establishments** | 175 | Official establishment identifiers, names, activities, addresses and coordinates |

These counts describe saved local extracts. They are not the number of real AEGIS suppliers, customers, trucks, or shipments. An official establishment point does not establish a supply contract. A BEAM source report includes human, animal, and food categories; inspect **Source Type** and **Source Site** before describing its content.

| Control | What it does | Important detail |
|---|---|---|
| **Dataset** | Chooses one recognized table | Unavailable/conflicting sources cannot be treated as a successful current import |
| **Filter column** | Chooses one original column | The filter applies to this column only |
| **Contains text** | Accepts a literal, case-insensitive substring | It is not SQL, a regular expression, an exact numeric comparison, or a geographic boundary query |
| **Apply source filter** | Applies the typed filter and returns to the first page | Typing alone does not change the displayed results |
| **Clear filter** | Removes the applied filter and reloads the first page | It does not erase source observations |
| **Previous rows / Next rows** | Moves through pages of 25 rows | Browser pagination stops at its 10,000-row offset cap; it is not a full-analysis tool |
| **Schema and derived-file integrity** | Shows columns and a file fingerprint | For displayed rows, the hash belongs to the same bounded file snapshot parsed for that response |
| **Source identity and import provenance** | Shows the recognized source key, import status and original-input hashes | Recognition uses supported content schemas, not the filename or order in which files were downloaded |

The heading above the table gives **matching rows** and the displayed row range. Each column reports its number of nulls **on this page only**. The symbol **∅** means a missing cell. A page with zero nulls does not prove the entire dataset is complete.

Filtering one source never joins it to another. Finding the same state, pathogen name, or serotype in two sources does not prove that a human illness, an FSIS laboratory sample, a supplier, and a simulated shipment are connected. These exports do not provide the isolate-level genomic linkage needed for molecular attribution.

There is no full-table export button in this explorer. For complete analysis, the team uses the saved processed tables and source-specific scripts. The USDA county panel has its own separate CSV export.

**Use case: inspect a positive FSIS observation.** Choose **FSIS raw-poultry samples**, choose `salmonella_sp_analysis` under **Filter column**, enter `Positive`, and click **Apply source filter**. Inspect the collection date, establishment state, cancellation field, and source identity. Expand the integrity/provenance sections. Say, "This is a selected primary laboratory result in the saved source." Do not turn that observation into a finding about a simulated lot, a current truck, or a consumer's probability of illness.

### NOAA coverage audit

The **NOAA coverage audit** shows what has actually been obtained from the required historical NOAA/NCEI stream. Its four summary facts are **Verified stations**, **Date-row coverage**, **Metric coverage**, and **Report status**. The station table shows actual station IDs/coordinates, distance from the named city, returned dates, missing variable values, quality flags, and retrieval time or error.

The recorded extract covers **January 1, 2025 through June 30, 2026**. Five verified stations represent Columbia, Kansas City, Jefferson City, Springfield, and St. Louis. There are **2,730 returned station-date rows out of 2,730 requested**, but **nine missing requested variable values**. Metric coverage is approximately **99.89%**, and the report status remains **partial**. Complete date rows do not mean complete temperature and precipitation values.

The station IDs are `USW00003945`, `USW00003947`, `USW00003963`, `USW00013995`, and `USW00013994`, respectively. The coverage report was generated at **2026-10-26 06:39:34 UTC**; individual source retrievals are also retained. See `reports/noaa_coverage.json` for the precise record. This historical report is distinct from the small station/week probe shown in the public-source cards.

The variables are daily maximum temperature (`TMAX`), minimum temperature (`TMIN`), and precipitation (`PRCP`). A flag count describes source quality information; a blank quality flag is not a promise of zero measurement error. Station reporting dates can use local observation periods, so a daily record is not automatically a UTC-midnight reading.

**Use case: answer "Is NOAA complete?"** Read both coverage percentages and the missing-metric counts, then the geographic/date limits. The accurate answer is that the bounded five-station extract has all requested date rows and some missing variable values. It does not cover every establishment or every historical training year. No validated NOAA-to-FSIS model join has been completed. Airport ambient weather is not cargo temperature or a reconstruction of a shipment's exposure.

### Source-specific ingestion

The **Source-specific ingestion** table explains what happened when supplied exports were read. It lists **Supplied export**, **Evidence layer**, **Rows ingested**, and **Validation**. This is an import report, not an upload or merge form.

Read its outcomes literally:

- **Ingested / source schema accepted:** a supported adapter parsed that source structure. This does not establish a scientific linkage to another table.
- **Duplicate:** the same bytes were already represented; no additional observations were added from that download.
- **Unrecognized:** the file is inventoried, but its structure was not accepted as a supported source. It has not been silently merged.
- **Conflict:** different exports matched the same source identity, so the importer requires explicit selection rather than pooling or guessing which is newest.
- **Failed:** inspect the exact error. A previous output may be retained, but its existence is not proof that the latest import succeeded.

For example, the small FSIS ready-to-eat sampling JSON is not a complete primary raw-poultry training set. Secondary typing tables are not additional primary sample outcomes. The UI does not offer a button that reinterprets those files to increase the sample count.

### The five public-source cards

| Card | What it supplies | How to interpret it |
|---|---|---|
| **Open-Meteo forecast** | Columbia-area forecast values | A forecast, not an observed historical NOAA stream |
| **NWS official alerts** | Official Missouri severe-weather warnings in the captured response | Read validity and retrieval context; an empty captured list is not an all-weather safety clearance |
| **NCEI historical observations** | A dated small station probe | Separate from the five-station coverage audit; neither represents cargo telemetry |
| **FSIS official recalls** | Official recall-notice evidence | Real notices remain separate from fictional lots without genuine traceability |
| **MoDOT traveler information** | Captured road-incident layers | Separate geometry evidence; OSRM does not automatically avoid these closures |

The source badge can say **Dated response available**, **Stale response - review age**, or **Coverage gap**. The source stamp identifies a dated fixture or cached response and its retrieval time. Read that stamp before interpreting the contents.

**Open official response** opens the provider endpoint in another tab. It can require internet and can fail even though an older local response remains usable for the demo. It is not a local re-import button.

**Refresh** deliberately checks that source through its adapter. Existing cache lifetimes may allow a valid cached response to be reused; clicking the button does not guarantee a new upstream observation or a new download. An unsuccessful refresh can leave a dated fallback visible with its exact failure. It does not reset the digital twin, approve a response, retrain the scientific model, or transform forecasts into observations. Refresh is disabled in verified offline rehearsal so its dated fixtures stay fixed.

### Official recall notices

The recall list gives a concise preview of saved FSIS notices. **Read official notice**, when supplied, opens the provider's notice. The app requests a bounded preview of up to 20 records and displays six notices. These are the first records in provider response order; the app does **not** establish that they are the six newest recalls.

Notice titles/dates are real source evidence where the response is recognized. Simulated lot IDs do not supply the genuine product/lot/establishment traceability needed to prove that a notice affects a demo shipment. Reading or refreshing a notice does not place a mandatory hold on a fictional lot. The human hold workflow remains separate.

### Connectivity evidence and supplied-file inventory

**Connectivity evidence** shows the source ID, saved test status, HTTP status, latency, content type, and last probe/failure. **JSON evidence** opens the saved probe records. This is dated testing evidence. It does not perform a new request just because the screen is opened, and a reachable documentation webpage is not the same as a working data adapter.

For this guide, the saved registry contains 19 endpoints with 14 recorded HTTP successes. Five earlier FSIS/USDA ERS website probes retain DNS-resolution failures. Their locally imported tables and dated official responses can remain available. Do not replace the recorded errors with an assumed success or say that every integration is live. Later refresh actions and the road workspace have their own independent timestamps and evidence.

**Supplied data inventory** lists the 42 audited original files, their sizes, likely sources, and read status. **Full inventory** opens the complete manifest, including the supported metadata and exact errors where applicable. An **Inspected** file is not necessarily an ingested model input. Workbook dimensions may be declared dimensions rather than an exact parsed count. Unsupported files remain recorded rather than silently merged.

### A useful evidence-review routine

1. Open **Sources & evidence** and read the source time and label before quoting a value.
2. Choose a real ingested dataset and inspect a bounded row, its original column names, and the source-input hash.
3. Read the import status. Resolve an unavailable/conflicting import through the documented source-specific workflow rather than assuming an older file is current.
4. If discussing weather, compare the NOAA date-row and variable coverage. Keep forecast, reanalysis, station weather, and cargo simulation separate.
5. If discussing food access, state the county, FIPS, measure, year, and denominator.
6. If discussing a recall, inspect the official notice and admit when genuine shipment-level matching is absent.
7. Record the data's limitations in the presentation. The evidence screen supports traceable claims; it does not automatically establish a safe operational disposition.

## Model evaluation: understand the measured result

**Use this workspace when you need to answer:** What exactly was predicted? Was it evaluated on later observations? Did a fitted model improve on a simple historical baseline? What can we honestly claim?

Open **Model evaluation** in the main navigation. This is a read-only display of saved scientific evaluation artifacts. Opening it does not train a model, query a live laboratory, change a lot's eligibility, or generate a new individualized risk forecast for the selected shipment.

The target is **Salmonella positivity in a selected national FSIS raw-poultry primary sample**. The unit is a selected laboratory sample. It is not a consumer, shipment, whole farm, or all poultry sold in Missouri. Positive/negative primary results are used only with the implemented cancellation/date rules. CDC outbreaks, BEAM surveillance, NOAA weather, road events, and simulated cargo are not joined into this target.

### The baseline and the fitted model

The **Historical prevalence** baseline gives every held-out observation the same smoothed training-period estimate. Smoothing keeps an estimate from becoming an unjustified absolute zero or one when counts are small. In the saved primary study, that training estimate is approximately **9.00%** selected-sample positivity. The later holdout's observed positivity is approximately **9.81%**. Neither percentage is a consumer-illness probability.

**Logistic regression** is the fitted comparison model. It uses an assumed 90-day-lagged historical prevalence feature plus two calendar-month features that represent seasonality. It does not use live sensor data, weather, consumer symptoms, or a gene-sequence comparison. The more complicated model is useful only if the evaluation shows a defensible improvement. Here it did not establish such an improvement, so the saved **Operational selection** remains **smoothed historical prevalence; prospective skill not established**.

### Primary chronological holdout: the numbers shown

The following values were checked against `reports/model_evaluation.json` for this October 29, 2026 guide. That saved artifact does not record a model-run timestamp; the guide's check date is not an invented training date.

| Quantity | Saved result |
|---|---|
| Training samples | 48,361 |
| Last training collection date | May 30, 2025 |
| Validation samples | 23,472 |
| Validation collection dates | August 29, 2025 through June 30, 2026 |
| Time separation | A 90-day embargo before the validation start is excluded from fitting |
| Baseline Brier score | 0.08855575 |
| Logistic Brier score | 0.08859440 |
| Baseline Brier 95% week-block interval | 0.08543538 to 0.09224387 |
| Logistic Brier 95% week-block interval | 0.08547636 to 0.09229202 |
| Baseline PR-AUC / average precision | 0.09811691 |
| Logistic PR-AUC / average precision | 0.09814105 |
| Baseline ROC-AUC | 0.50000000 |
| Logistic ROC-AUC | 0.49802936 |
| Precision and recall at threshold 0.5 | Both are 0 for both estimators in this saved evaluation |

The **Training samples**, **Validation samples**, **Baseline Brier**, and **Logistic Brier** cards summarize this study. The **Chronological holdout comparison** table includes its metrics and uncertainty intervals. Dates describe collection-date ordering, not verified dates on which results became available to the public.

### What each metric means

| Displayed metric | Plain-language interpretation | Common mistake to avoid |
|---|---|---|
| **Brier** | Average squared difference between a predicted probability and the observed 0/1 outcome; lower is better | It is not an accuracy percentage. A score near 0.0886 does not mean 91.14% accurate |
| **95% week-block CI** | A resampling interval that retains groups of observations from the same validation week | It does not cover unknown publication delays, selection bias, all future periods, or individual shipment uncertainty |
| **PR-AUC (AP)** | How useful the model's ranking is when focusing on the relatively uncommon positive samples | Its reference level depends on how common positives are; a number near 0.10 must be compared with the baseline |
| **ROC-AUC** | Ability to rank positive samples above negative ones | A result near 0.5 provides little useful discrimination in this holdout; it is not a safety certification |
| **Precision @ 0.5** | Among samples predicted positive at the 50% cutoff, the positive fraction under the implementation's reporting rule | Zero here is not a statement that overall accuracy is zero |
| **Recall @ 0.5** | Fraction of actual positive samples selected by that 50% cutoff | These estimates did not produce useful positive classifications at that cutoff; a lower threshold would require its own reviewed evaluation |

The primary baseline's Brier score is slightly lower than the logistic model's. Their displayed Brier intervals overlap closely, the PR-AUC values are essentially similar, and logistic ROC-AUC is near 0.5. The defensible conclusion is that this study did not establish useful improvement over the baseline. It does not support inventing an accuracy figure or adding a more elaborate model solely for presentation.

### Calibration and coefficients

The **Calibration** chart compares the fitted model's predicted probabilities with observed selected-sample positivity in grouped predictions. The dashed reference line is the ideal agreement line. Hovering the chart reveals the plotted values. A curve close to the reference line can be encouraging about those groups, but good-looking calibration alone does not prove useful ranking or valid future deployment.

**Feature coefficients** appear under **Interpretation & limitations**. The current feature names are `lag90_prevalence`, `month_sin`, and `month_cos`. These are fitted associations on the logistic model's scale. They are not causes, degrees of temperature change, supplier rankings, regulatory findings, or instructions to hold stock. A single coefficient should not be quoted as the percentage change in a consumer's illness risk.

### Snapshot timing audit

The **Snapshot timing audit** asks whether the historical information used to fit an estimator could plausibly have existed before the later observations being evaluated. This is a separate retrospective sensitivity study, not an extra validation result to merge into the primary holdout table.

The cards show **Training snapshot cutoff**, **Training samples**, **Later samples**, and **Public release verified**. In the current saved audit:

- The training snapshot cutoff is **March 19, 2026**.
- There are **57,459** earlier training samples and **7,754** later validation samples.
- The later sample window is **March 20 through June 30, 2026**.
- **Public release verified** is **No**. A file-creation date is not proof of its first public release.
- The snapshot baseline Brier is approximately **0.09297314**; the calendar-only logistic comparison is approximately **0.09293427**. Logistic ROC-AUC is approximately **0.49920**.

The audit artifact was generated at **2026-10-26 06:42:45 UTC** (`reports/model_timing.json`). Training labels are frozen to earlier source snapshots; held-out outcomes do not update those fitted parameters or that frozen baseline. Actual row-level result availability and an authoritative historical as-of archive remain unavailable. The FY2026 evaluation file can contain later retrospective revisions. This audit improves transparency, but it does not turn the project into a validated prospective forecasting system.

Why are the two studies' sample counts and scores different? They use different time/snapshot rules and different held-out samples. A result from one study cannot be substituted into the other study's denominator, dates, or uncertainty interval.

### Where the fitted model makes errors

Expand **Inspect measured state-level error analysis** inside **Where the fitted model makes errors**. The table shows establishment state, holdout sample count, observed sample positivity, and logistic Brier loss. Only states with at least 30 held-out samples are included; 42 groups are currently recorded.

These are descriptive slices of the same national holdout. They are not independent state-level validation, farm ratings, or supplier league tables. Differences can reflect which samples were selected. A state absent from the table has not been assigned a zero risk or a perfect score. The study does not establish subgroup uncertainty or prospective state-level performance.

### A useful science-presentation routine

1. State the target and unit first: a selected FSIS primary raw-poultry sample and its Salmonella outcome.
2. Show the chronological dates and sample counts. Explain the assumed reporting lag and embargo without presenting them as verified publication history.
3. Compare the baseline and logistic Brier scores, then PR-AUC and ROC-AUC. Explain why the baseline is retained.
4. Show calibration as one diagnostic, not a substitute for the other results.
5. Expand the state error breakdown to demonstrate inspection, and identify its subgroup limitations.
6. Read **Snapshot timing audit** and **Public release verified: No**. Explain what remains unknown.
7. End with the supported contribution: measured evaluation, reproducible evidence, visible uncertainty, and human-reviewed operational choices.

A defensible presentation sentence is: "We evaluated a national retrospective sampling target chronologically, compared it with a transparent baseline, and retained the baseline because the fitted model did not establish useful improvement." Avoid "We predict which consumer will become ill," "This farm is unsafe," or "The model automatically orders a hold."

### Evidence/science troubleshooting and current boundaries

| What you see | What it usually means | Appropriate next action |
|---|---|---|
| A stale source card with an older retrieval time | The saved response has aged or a new request failed | Read its date/error; deliberately refresh in the operator app if needed, or demonstrate the dated fixture honestly |
| A failed FSIS/ERS connectivity row while local rows still display | A saved provider request failed, but valid local data remains | Keep these facts separate; a website outage does not erase a prior input, and a prior input does not prove a new request worked |
| A dataset is disabled/unreadable/conflicting | A recognized current import or integrity check is unavailable | Have the developer inspect the exact report and source-specific adapter; do not invent rows or mix snapshots |
| A filter returns zero rows | The literal substring did not match that column in the selected source | Check the selected dataset/column, copy an actual visible value, or use **Clear filter**; do not interpret it as no real-world cases |
| ∅ or Missing / suppressed | The source does not supply a usable value for that cell | Keep it missing; do not substitute zero |
| A NOAA status of partial despite 100% date-row coverage | Returned dates and complete variables are different checks | Review metric missingness, flags, station/date scope and the lack of a validated FSIS join |
| No recall notices or an unrecognized schema message | No supported saved preview is available | Inspect the dated source response; do not infer that no recall exists |
| Missing model metrics or a timing-report error | The required saved evaluation artifact cannot be read | Restore/reproduce the documented scientific artifact through the developer workflow; no values are inferred by opening the page |

The app does not currently provide isolate-level molecular attribution, a validated weather-to-FSIS prediction, live cargo sensing, or a verified real recall-to-demo-lot match. Missing per-result publication timing remains a scientific limitation. Broader NOAA historical coverage is incomplete. Genuine signed-in Kiro specification execution, author/rubric review, and the timed team presentation remain separate project gates; polished evidence screens do not complete those gates automatically.

For deeper source records, consult `docs/data_catalog.md`, `docs/ingestion_provenance.md`, `docs/food_access_context.md`, `docs/model_card.md`, `reports/model_evaluation.json`, `reports/model_timing.json`, `reports/noaa_coverage.json`, and the source-specific import manifests. These files support the screen; they should not be described as additional live integrations.

### Separate Missouri integrated study

Model evaluation now also shows **One Health model: what did integration add?**
It compares prevalence, FSIS history, added BEAM, core BEAM/NOAA and added NORS on
the same supported Missouri cohort at a seven-day lead. Only 490 of 1,534 samples
meet coverage; primary validation has 171 samples and 22 positives. Monthly gaps
remain missing, not zero. Open the assumptions/calibration/error section and
download the model JSON or aligned CSV. The original national study remains
separate and unchanged.

The core Brier score is about 0.11246 versus baseline 0.11431. Marginal BEAM/NOAA
intervals include zero; NORS worsens this cohort's result. No prospective
activation, consumer illness, genomic causation or individual-lot inference is
allowed. This is an exploratory aggregate alignment, not a validated production
weather-to-FSIS predictor. The final five-task PDF includes exact metrics,
uncertainty and the resulting limits. The owner disclosed Kiro non-use.
