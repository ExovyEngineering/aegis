# Analysis reproduction and scope

Start with [the notebooks](../notebooks/README.md). Four executed Jupyter
notebooks cover provenance, preprocessing/integration, national and integrated
modeling/evaluation, and constrained scenario/FEFO analysis. They call the same
Python modules and entry scripts used to generate the reported results.

The optional notebook environment is pinned in `requirements-notebooks.txt` and
includes the application dependency lock. It is separate from the basic judge
demo setup. HTML previews can be read without installing Jupyter. The runner
uses an explicit kernel for its exact interpreter and fails on cell errors.

Each notebook receives a separate copied project. Child script output, source
hashes and preservation checks are recorded in its `RUN_MANIFEST.json`; the
top-level execution report records actual cell counts and outcomes. Published
scientific artifacts are baseline inputs, not overwritten by notebook execution.

Two modes are distinguished:

- **Bundled snapshots:** included source-specific processed tables and original
  selected NOAA responses support feature reconstruction, model fitting,
  evaluation, scenario optimization and comparisons with published results.
- **Original source replay:** explicit access to the provenance-listed original
  FSIS JSON, CDC CSV, directory CSV and USDA workbook is required. The helper
  validates hashes and stages copies before running the maintained adapters;
  missing/changed sources fail. The raw profile is not silently substituted for
  the default mode. Bulk originals remain excluded from the judge ZIP.

The scientific model's assumptions and limitations remain in
[the model card](model_card.md) and [alignment notes](analytic_alignment.md).
Reproducibility is not evidence of valid historic publication timing, shipment
exposure linkage, consumer risk, connected hardware or actual Kiro execution.
