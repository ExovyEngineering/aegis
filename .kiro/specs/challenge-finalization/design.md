# Design

Prepared specification, not authenticated Kiro history. Source adapters retain
original schemas. `integrated_study.py` builds a gated retrospective regional
cohort; `decision_study.py` solves separate simulated policy comparisons. The
original national model and operational optimizer stay separate.

`challenge.py` serves bounded read-only reports and allowlisted artifacts.
`ChallengeEvidence.tsx` renders missing metrics as unavailable and exposes
uncertainty, scenario scope and pending gates. `build_final_handoff.py` compiles
the task mapping, actual results, diagram, ten-menu guide and presentation.
`build_final_release.py` orchestrates deterministic reproduction, test/build,
safe isolated demos and verified ZIP creation without deployment or state reset.
