# Team science statement

AEGIS began with a practical question: how can a poultry distributor use public food-safety and environmental evidence to make better delivery decisions while keeping food available? As the idea developed, we connected retrospective risk research to a simulated Missouri distribution network, then added temperature-history replay, freshness-aware allocation, routing alternatives and a driver view. Our central contribution is an auditable path from evidence to an operational choice that a person can review.

| Contributor | Project contribution reported by the team lead |
|---|---|
| **Isaac Jenkins** | Led the disease and public-health perspective, including disease-related databases and the use of CDC evidence. |
| **Micky** | Fact-checked code and helped establish the GitHub repository and collaboration setup. |
| **Project lead** | Led supply-chain logistics, gathered the remaining data, defined the application's purpose and designed its operational features and extensions. |

These roles describe project contributions, not professional credentials. Codex assisted implementation, documentation and automated testing. Micky's surname and the lead's preferred author name may be added during final author review.

**A decision changed by another perspective.** Isaac's disease-side input helped broaden the original logistics concept to include CDC data, especially BEAM, and examination of historical patterns. This changed the evidence available to the research pipeline. It also made a scientific boundary essential: human surveillance can provide regional context, but cannot identify a fictional shipment as contaminated. The lead's feedback about confusing controls and driver distraction subsequently shaped guided questions, clearer map workflows and parked-use reporting. These are reported project decisions, not a formal external usability study.

**What integration taught us.** FSIS selected poultry samples supply the outcome, PulseNet-derived BEAM aggregates supply human-surveillance context, and NOAA supplies an ambient-weather index. NORS historical outbreaks and USDA Food Environment Atlas county context add two domains beyond those core sources. On 171 held-out Missouri samples, the core model's Brier score was 0.11246 versus 0.11431 for the prevalence baseline. BEAM and NOAA marginal intervals included zero. Adding NORS worsened Brier to 0.12449; its old, constant holdout feature limits interpretation. More data did not automatically produce a better prediction. USDA remains contextual because simulated recipients have no verified population-need crosswalk.

**How the question evolved.** Rather than turn uncertain surveillance into automatic shipment holds, we kept scientific estimates separate from binding recall/hold exclusions and human approval. Freshness replay and constrained scenario comparisons show how timing, eligible inventory and destination service interact. Their quality parameters and all logistics outcomes are simulated; they do not establish measured spoilage, prevented illness or real-world savings.

**Next collaboration.** A refrigerated distributor working with a public-health or food-safety partner could supply deidentified lot/establishment/time traceability, actual release timestamps, calibrated cargo histories and receiving/demand data. That would enable prospective validation and stronger food-access analysis. Authors will review credit and claims before submission. **Kiro was not used**; prepared specs and steering files do not satisfy genuine Kiro use.
