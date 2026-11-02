# User-supplied five-task requirements

Received November 1, 2026. Verbatim task text supplied by the project owner; the linked Google document was not accessible during this review. This is the implementation reference, not evidence of organizer signoff.

Task 1 — Define the One Health system and build the integrated data layer

Start with the decision-maker—not the model. Select a primary supply-chain actor and define that actor’s decisions, time horizon, geography, commodity scope, operational constraints, and acceptable actions. Then construct a One Health data model that connects the required datasets and your team-selected additions.

● Create a system map showing human, food/animal, environmental, supply-chain, and food-security pathways relevant to the decision.

● Define common spatial and temporal units and document how datasets are aligned, lagged, aggregated, or cross-walked.

● Create a data dictionary and provenance table.

● Identify known limitations and avoid treating temporal or genomic similarity as proof of outbreak causation.

● Define the target decision and the model outcome that will support that decision.

Expected output: One Health system diagram, data inventory/provenance table, harmonized analytic dataset, and a short decision statement describing who will use the tool, what decision they face, and when the decision must be made.



Task 2 — Develop and validate a proactive food-safety risk model

Build a data-science model that estimates near-term elevated risk at a decision-relevant unit such as commodity × region, establishment × time, or distribution corridor × time. Teams may use classification, anomaly detection, forecasting, spatial modeling, or an ensemble approach, but must justify the target and horizon.

● Create a transparent baseline model using a limited set of variables.

● Develop an integrated model using PulseNet-derived, FSIS, NOAA, and additional team-selected features.

● Use time-aware validation; avoid random train/test splits when they leak future information.

● Report discrimination and calibration metrics appropriate to the task, not accuracy alone.

● Quantify uncertainty and examine false-positive and false-negative consequences.

● Evaluate the marginal value of at least one added dataset or data domain.

Expected output: Reproducible modeling pipeline, performance metrics, calibration/uncertainty results, feature or signal interpretation, and a map or time series showing where/when elevated risk is identified.



Task 3 — Convert risk prediction into a food safety + food security decision model

Prediction is not decision support. Translate the risk model into explicit actions for the selected supply-chain actor and show how recommendations change when both food safety and food availability are considered.

● Define feasible actions such as inspect, hold for review, expedite, reroute, prioritize, or request additional information.

● Define operational constraints such as inventory, perishability, transport time, storage capacity, geography, and population need.

● Include at least one food-security or equity objective, such as preserving food volume, maintaining service to high-need communities, or minimizing disruption to vulnerable populations.

● Compare a simple rule-based or status-quo policy with the model-guided policy.

● Use scenario analysis or optimization to demonstrate trade-offs among risk reduction, food retained/distributed, travel or delay, and equitable access.

● Require human review for high-consequence decisions; the tool must support—not replace—regulatory and operational judgment.

Expected output: Decision logic or optimization formulation, at least three scenario comparisons, and quantitative measures showing both food-safety and food-security consequences.



Task 4 — Operationalize the decision support tool with AWS Kiro

Use AWS Kiro to translate the analytics into a working decision-support application. The model and decision logic should be visible to the user through an interface that supports action, not just visualization.

● Use Kiro Specs or equivalent structured prompts to define user requirements, technical design, and implementation tasks.

● Use Kiro steering files or project guidance to encode the selected actor, data definitions, decision rules, uncertainty language, and safety constraints consistently across the application.

● Build an interactive web application (React is recommended for consistency with prior NAFSI Hub challenges) that can be deployed from the team repository.

● At minimum, include: a current-risk view, a prioritized alert/attention queue, a scenario builder, a recommended-action panel, and an explanation/evidence panel.

● Display uncertainty and the data signals supporting each recommendation. Do not label a food, establishment, or shipment “safe” or “unsafe” solely from the model.

● Export or precompute model outputs as reproducible CSV/JSON artifacts if a live backend is not practical. No additional AWS service is required beyond Kiro.

Expected output: Functional decision-support application, Kiro specification/prompt files, reproducible build instructions, and a documented link between model outputs and user-facing recommendations.



Task 5 — Demonstrate team science and the value of new data

This challenge is intentionally broader than a single-discipline modeling exercise. Teams should combine food safety, public health, data science, agriculture/environment, supply-chain, and/or user-design perspectives.

● Assign and document team roles; roles may overlap, but each team must show how different expertise shaped the solution.

● Integrate at least two additional datasets beyond the three required core sources.

● Run an ablation or comparison showing what changed when at least one new dataset or domain was added.

● Document at least one team decision that changed because of input from another discipline or stakeholder perspective.

● Identify the next dataset or partner that would most improve the tool if the project continued.

Expected output: One-page team science statement and a concise analysis of the added value of multi-source data integration.