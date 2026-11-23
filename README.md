# Urban Tranquillity Score

An English-language Streamlit workspace for assessing an urban development and turning its weaknesses into a costed improvement plan.

## What the workspace does

- **Overview:** assessment coverage, score bounds, concerns and progress by theme.
- **Assess the project:** 22 subcriteria across the original seven themes, with problem statements, examples of consequences, contextual 0–4 rubrics and evidence prompts.
- **Build an action plan:** 28 interventions, including practical adjustments, design changes and advanced tools. Each option explains expected benefits, prerequisites, trade-offs and editable investment and annual operating allowances.
- **Report and save:** printable HTML report, ratings/evidence CSV, action-plan CSV and a validated JSON backup that can be restored in a later session.

Lighting is broken down into dark gaps, glare/spill, night-time schedules and fault management. Options include rebalancing existing lights, targeted installation, shielding, schedule changes, adaptive control and remote fault monitoring. Advanced tools are options to evaluate, not automatic score improvements.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. Use **Load fictional sample** in the sidebar for a clearly labelled demonstration, or start with an unassessed project. Save a JSON backup before closing the browser; session data is not persisted to a database.

## Scoring and scenario assumptions

The original default weights are retained: visibility 15, lighting 15, mobility 20, accessibility 10, comfort 15, maintenance 15 and community 10. Ratings remain 0–4 and weights are normalised automatically.

Within each theme, applicable subcriteria have equal weight. An unassessed item remains in the denominator for coverage and possible-score bounds. It is neither a zero nor an invented midpoint. A complete score is available when every positive-weight applicable item has a rating. An entirely non-applicable theme is excluded, with remaining weights renormalised. Zero-weight themes do not contribute to the score. Reported completeness does not certify evidence: missing references and unjustified exclusions are flagged separately.

Expected action targets are **user-entered scenarios**, not causal estimates. New actions start with the current rating, so selecting hardware or a study creates no automatic gain. Multiple actions on one subcriterion use the highest target, not a sum of improvements. Zero quantities and unassessed items cannot produce projected gains. Cross-theme assumptions can explicitly override targets, including a lower rating for an adverse effect. Baseline data is never changed by a scenario.

Investment is quantity × editable unit-price range. Annual operation is quantity × editable annual allowance. The multi-year estimate adds undiscounted recurring allowances. Inflation, energy tariff changes, replacement and residual values are not modelled. Site area is contextual; it is not used as a universal quantity multiplier. Avoid selecting mutually exclusive alternatives together because costs are additive.

## Sources and limitations

Each subcriterion cites the PDF viewer pages of the Nexity `plaquette-amenagement-tranquilite-oct-V2.pdf`. The problem examples are situations to investigate, not findings about a real site. Supplementary method sources are the hackathon brief (slides 13–17), Engagement & Territoires support (sections 8 and 12) and Paris&Co × Efus (pages 7, 11, 43–44, 50 and 55). Source documents are not redistributed.

Rubrics, subcriterion aggregation, default action targets and **all price allowances are hackathon proposals**, not official Nexity standards, certified safety scores or supplier quotations. A model, sensor or AI service must be validated against actual users and conditions. Document an assessment's scope, locations, times and project stage consistently before comparing results. Urgent concerns must be reviewed regardless of the overall score.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover weighted scores, missing/not-applicable items, zero weights, scenario isolation, adverse effects, cost arithmetic, backup validation and Streamlit user journeys. On Windows, Streamlit's test runner needs local socket access; a restrictive sandbox may prevent its event loop from starting.

## Files

- `streamlit_app.py`: UI, session workflow and report exports.
- `catalogue.py`: criteria, rating guidance and action library.
- `scoring.py`: scoring, scenario, costing and backup validation.
- `.streamlit/config.toml`: theme, upload limit and telemetry preference.
- `tests/`: pure logic and Streamlit integration tests.

## Deploy to Render

1. Connect the full repository, including `catalogue.py`, `scoring.py` and `.streamlit/config.toml`.
2. In Render, select **New > Blueprint**, then connect your repository.
3. Render reads `render.yaml` and builds the Streamlit web service.

Hosting is not changed automatically by editing or pushing a branch. Select the intended branch in your hosting configuration when ready.
