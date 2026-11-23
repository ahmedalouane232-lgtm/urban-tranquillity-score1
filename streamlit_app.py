"""Guided urban diagnosis, transparent scoring and action planning."""
from copy import deepcopy
from html import escape
import json

import pandas as pd
import streamlit as st

from catalogue import (CRITERIA, ISSUES, ISSUE_CRITERION, ACTIONS, ACTION_BY_ID,
                       RATING_LABELS, STATUSES, SEVERITIES)
from scoring import (new_assessment, default_weights, evaluate, default_action,
                     project_scenario, cost_totals, validate_snapshot)

st.set_page_config(page_title="Urban Tranquillity Score", page_icon="◉", layout="wide")
st.markdown("""<style>
.block-container {max-width:1240px;padding-top:4rem;padding-bottom:3rem}
h1 {letter-spacing:-.04em} h2 {letter-spacing:-.02em}
[data-testid="stMetricValue"] {font-variant-numeric:tabular-nums}
[data-testid="stSidebar"] {border-right:1px solid #dce5e1}
.eyebrow {font-size:.75rem;font-weight:700;letter-spacing:.13em;color:#45675d;margin-bottom:.5rem}
.intro {font-size:1.08rem;max-width:760px;color:#4d615a;line-height:1.6}
</style>""", unsafe_allow_html=True)

DEFAULT_PROJECT = {"name": "My development project", "area": 5000, "stage": "Planning", "budget": 25000, "years": 5}
ROUTES = ["Overview", "Assess the project", "Build an action plan", "Report and save"]
for key, value in {"project": DEFAULT_PROJECT, "assessment": new_assessment(), "weights": default_weights(), "plan": {}, "adjustments": {}, "sample": False}.items():
    if key not in st.session_state:
        st.session_state[key] = deepcopy(value)


def clear_widgets():
    for key in list(st.session_state):
        if key.startswith("_"):
            del st.session_state[key]


def load_sample():
    clear_widgets()
    st.session_state.project = {**DEFAULT_PROJECT, "name": "Example · Station-to-home quarter"}
    st.session_state.assessment = new_assessment()
    st.session_state.weights = default_weights()
    st.session_state.plan = {}
    st.session_state.adjustments = {}
    st.session_state.sample = True
    for item in st.session_state.assessment.values():
        item.update(status="Assessed", rating=2, evidence="Fictional walkthrough record — demonstration only.")
    for key in ("dark_gaps", "night_use", "lighting_faults"):
        st.session_state.assessment[key].update(rating=1, severity="Significant concern")
    st.session_state.assessment["dark_gaps"]["observation"] = "Example: a dark transition between the bus stop and residential forecourt."
    st.session_state.assessment["glare"].update(rating=1, observation="Example: a luminaire faces residential windows.")


def reset_assessment():
    clear_widgets()
    st.session_state.assessment = new_assessment()
    st.session_state.weights = default_weights()
    st.session_state.plan = {}
    st.session_state.adjustments = {}
    st.session_state.sample = False


def snapshot():
    return {"schema_version": 1, **{k: st.session_state[k] for k in ("project", "assessment", "weights", "plan", "adjustments", "sample")}}


def restore():
    upload = st.session_state.get("_upload")
    try:
        if upload is None or upload.size > 1_000_000:
            raise ValueError("Choose an assessment JSON smaller than 1 MB.")
        data = validate_snapshot(json.loads(upload.getvalue()))
        clear_widgets()
        for key in ("project", "assessment", "weights", "plan"):
            st.session_state[key] = deepcopy(data[key])
        st.session_state.adjustments = deepcopy(data.get("adjustments", {}))
        st.session_state.sample = data.get("sample") is True
        st.session_state.restore_error = ""
        st.session_state.restore_success = True
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        st.session_state.restore_error = "Choose a valid version 1 assessment JSON, smaller than 1 MB. Check its criteria, ratings and cost ranges."


def go_assess():
    st.session_state._route = ROUTES[1]


def widget_key(key, default):
    # Keep durable assessment data separate from Streamlit's disposable widget state.
    if key not in st.session_state:
        st.session_state[key] = default
    return key


def euro(value):
    return f"€{value:,.0f}"


def score_text(result):
    return f"{result['score']:.1f} / 100" if result["complete"] else "Not complete"


def assessment_rows():
    result = evaluate(st.session_state.assessment, st.session_state.weights)
    scenario = project_scenario(st.session_state.assessment, st.session_state.plan, st.session_state.adjustments)
    norm = {r["id"]: r["normalised_weight"] for r in result["rows"]}
    rows = []
    for criterion in CRITERIA:
        for issue in criterion["issues"]:
            item = st.session_state.assessment[issue["id"]]
            rows.append({"Project": st.session_state.project["name"], "Stage": st.session_state.project["stage"],
                "Area (m²)": st.session_state.project["area"], "Criterion": criterion["name"],
                "Normalised weight (%)": round(norm[criterion["id"]], 2), "Subcriterion": issue["title"],
                "Status": item["status"], "Rating (0–4)": item["rating"] if item["status"] == "Assessed" else None,
                "Scenario rating (assumption)": scenario[issue["id"]]["rating"] if item["status"] == "Assessed" else None,
                "Concern": item["severity"], "Observed problem": item["observation"],
                "Evidence": item["evidence"], "Exclusion reason": item.get("na_reason", ""), "Source": issue["source"]})
    return rows


def selected_actions():
    rows = []
    for key, config in st.session_state.plan.items():
        if config["selected"]:
            a = ACTION_BY_ID[key]
            rows.append({"Action": a["title"], "Problem": ISSUES[a["issue"]]["title"], "Type": a["kind"],
                "Unit": a["unit"], "Quantity": config["quantity"],
                "Unit investment low (EUR)": config["low"], "Unit investment high (EUR)": config["high"],
                "Unit annual allowance (EUR)": config["annual"],
                "Investment low (EUR)": config["quantity"] * config["low"],
                "Investment high (EUR)": config["quantity"] * config["high"],
                "Annual operating allowance (EUR)": config["quantity"] * config["annual"],
                "Expected rating (0–4)": config["target"], "Owner": config["owner"], "Timing": config["timing"],
                "Trade-off": a["tradeoff"], "Prerequisite": a["prerequisite"], "Price basis": a["cost_basis"]})
    return rows


def csv_bytes(rows):
    safe = [{k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
             for k, v in row.items()} for row in rows]
    return pd.DataFrame(safe).to_csv(index=False).encode("utf-8-sig")


def report_html():
    base = evaluate(st.session_state.assessment, st.session_state.weights)
    future = evaluate(project_scenario(st.session_state.assessment, st.session_state.plan, st.session_state.adjustments), st.session_state.weights)
    costs = cost_totals(st.session_state.plan, st.session_state.project["years"])
    def table(rows):
        return pd.DataFrame(rows).to_html(index=False, escape=True, na_rep="Not assessed") if rows else "<p>No actions selected.</p>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Urban Tranquillity Assessment</title>
    <style>body{{font:15px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#182c25}}
    table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #ccd5d0;padding:8px;text-align:left;overflow-wrap:anywhere}}
    @media print{{body{{margin:0}}thead{{display:table-header-group}}tr{{break-inside:avoid}}}}</style>
    <h1>{escape(st.session_state.project['name'])}</h1>
    <p>{escape(st.session_state.project['stage'])} · {st.session_state.project['area']:,} m²</p>
    <p>{'FICTIONAL SAMPLE — not a real site assessment.' if st.session_state.sample else 'Project assessment — entered by the project team.'}</p>
    <h2>Assessment and scenario</h2><p>Baseline: {score_text(base)}. Weighted assessment coverage: {base['coverage']:.1f}%.
    Scenario: {score_text(future)}. Expected targets require verification and are not measured improvements.</p>
    <p>Investment allowance: {euro(costs['low'])}–{euro(costs['high'])}. Annual operating allowance: {euro(costs['annual'])}.
    Prices are editable hackathon assumptions, excluding tax, with no supplier quote implied.</p>
    <h2>Criteria and evidence</h2>{table(assessment_rows())}<h2>Selected action plan</h2>{table(selected_actions())}
    <h2>Cross-theme scenario assumptions</h2>{table([{'Subcriterion': ISSUES[k]['title'], 'Expected rating override': v} for k, v in st.session_state.adjustments.items()])}
    <h2>Method</h2><p>Ratings 0–4; equal subcriterion weights within each theme; adjustable theme weights normalised across applicable themes.
    Missing ratings keep the overall score incomplete. Non-applicable items require a reason. Complete scores are self-ratings, not independent certification.
    Multiple actions on one item use the highest expected target, never a sum of gains. Equipment or a study is not proof of an improved outcome.
    Review urgent concerns and missing evidence regardless of the overall score.</p>
    <p>Source: Nexity, plaquette-amenagement-tranquilite-oct-V2.pdf (viewer pages cited above);
    Hackathon_Tranquillite_deck_etudiants.pptx, slides 13–17. Rubrics, aggregation and prices are project proposals.</p></html>"""


def overview():
    result = evaluate(st.session_state.assessment, st.session_state.weights)
    left, right = st.columns([3, 2], gap="large")
    with left:
        st.subheader("Understand the place. Choose what to improve.")
        st.write("Assess everyday journeys and shared spaces, document the problems, then compare practical interventions before committing a budget.")
        st.button("Start or continue assessment", type="primary", on_click=go_assess)
        if not result["assessed"]:
            st.button("Explore a fictional example", on_click=load_sample)
    with right:
        st.metric("Weighted assessment coverage", f"{result['coverage']:.0f}%")
        st.progress(min(1.0, result["coverage"] / 100))
        st.caption(f"{result['assessed']} of {result['applicable']} applicable subcriteria assessed. Zero-weight themes do not contribute to weighted coverage.")
    st.divider()
    a, b, c = st.columns(3)
    a.metric("Overall score", score_text(result))
    b.metric("Selected actions", len(selected_actions()))
    c.metric("Urgent concerns", sum(s["severity"] == "Urgent concern" and s["status"] != "Not applicable" for s in st.session_state.assessment.values()))
    if result["total_weight"] == 0:
        st.warning("No applicable theme has a positive weight. Adjust weights or applicability before scoring.")
    elif not result["complete"]:
        st.info(f"The overall score is incomplete. Given the assessed items, the full weighted score could range from {result['lower']:.1f} to {result['upper']:.1f}/100. These are mathematical bounds, not a risk prediction.")
    chart = pd.DataFrame([{"Theme": r["name"], "Assessed-item average (0–4)": r["rating"]} for r in result["rows"] if r["rating"] is not None and r["normalised_weight"] > 0])
    if not chart.empty:
        st.subheader("Where the assessment stands")
        st.vega_lite_chart(chart, {
            "mark": {"type": "bar", "color": "#1E6654"},
            "encoding": {
                "x": {"field": "Assessed-item average (0–4)", "type": "quantitative", "scale": {"domain": [0, 4]}, "title": "Assessed-item average (0–4)"},
                "y": {"field": "Theme", "type": "nominal", "sort": None, "title": None},
                "tooltip": [{"field": "Theme"}, {"field": "Assessed-item average (0–4)", "format": ".2f"}],
            },
        }, width="stretch")
        st.caption("Only assessed items are shown; a theme bar may be partial. Check coverage before comparing themes.")
    st.subheader("A clear path from diagnosis to action")
    for title, text in [
        ("01 · Diagnose", "Review problem examples, select a rating using the rubric and record what you actually observed."),
        ("02 · Compare", "Choose low-tech or advanced responses, inspect their trade-offs and enter actual quantities and prices."),
        ("03 · Verify", "Assign owners and expected targets. Export the plan, then reassess after implementation.")]:
        st.markdown(f"**{title}**  \n{text}")


def assess():
    st.subheader("Assess one theme at a time")
    st.caption("0 = confirmed not addressed · 1 = initial · 2 = partly addressed · 3 = well addressed · 4 = fully addressed and verified for this stage.")
    selected = st.selectbox("Assessment theme", [c["name"] for c in CRITERIA], key="_theme")
    criterion = next(c for c in CRITERIA if c["name"] == selected)
    st.write("In planning, use drawings, specifications and commitments. In operation, use observed performance and maintenance records. A planned response is not an observed outcome.")
    for issue in criterion["issues"]:
        item = st.session_state.assessment[issue["id"]]
        with st.container(border=True):
            st.markdown(f"### {issue['title']}")
            a, b = st.columns(2, gap="large")
            a.markdown(f"**Problem to look for**  \n{issue['problem']}")
            b.markdown(f"**Possible consequences**  \n{issue['consequence']}")
            st.caption("Illustrative situations to investigate; not findings about your project.")
            item["status"] = st.selectbox("Assessment status", STATUSES, key=widget_key(f"_status_{issue['id']}", item["status"]))
            if item["status"] == "Assessed":
                item["rating"] = st.select_slider("Rating", options=list(range(5)), format_func=lambda n: f"{n} · {RATING_LABELS[n]}",
                    key=widget_key(f"_rating_{issue['id']}", item["rating"]))
                st.info(issue["rubric"][item["rating"]])
                with st.expander("Compare all rating levels"):
                    for rubric in issue["rubric"]:
                        st.write(rubric)
            if item["status"] != "Not applicable":
                item["severity"] = st.selectbox("Concern requiring attention", SEVERITIES, key=widget_key(f"_severity_{issue['id']}", item["severity"]))
                item["observation"] = st.text_area("Your observation · location, time and affected users", max_chars=10000,
                    key=widget_key(f"_observation_{issue['id']}", item["observation"]))
            if item["status"] == "Not applicable":
                item["na_reason"] = st.text_area("Why is this not applicable?", max_chars=10000,
                    key=widget_key(f"_na_{issue['id']}", item.get("na_reason", "")))
            else:
                item["evidence"] = st.text_area("Evidence reference", help=issue["evidence"], max_chars=10000,
                    key=widget_key(f"_evidence_{issue['id']}_False", item["evidence"]))
            if item["status"] == "Assessed" and not item["evidence"].strip():
                st.warning("This is an undocumented self-rating. Add evidence before using it for a decision.")
            if item["status"] == "Not applicable" and not item.get("na_reason", "").strip():
                st.warning("Record a reason for excluding this item. Applicability changes the denominator.")
            st.caption(f"Evidence to consider: {issue['evidence']}")
            st.caption(f"Source: {issue['source']}. Rating descriptions are proposed for this prototype.")
    row = next(r for r in evaluate(st.session_state.assessment, st.session_state.weights)["rows"] if r["id"] == criterion["id"])
    st.caption(f"Theme completion: {row['assessed']}/{row['applicable']} applicable items. Changes are retained across views; download a backup before closing.")


def plan_summary():
    base = evaluate(st.session_state.assessment, st.session_state.weights)
    future = evaluate(project_scenario(st.session_state.assessment, st.session_state.plan, st.session_state.adjustments), st.session_state.weights)
    costs = cost_totals(st.session_state.plan, st.session_state.project["years"])
    a, b, c, d = st.columns(4)
    a.metric("Baseline score", score_text(base))
    b.metric("Scenario score", score_text(future), f"{future['score'] - base['score']:+.1f} expected points" if base["complete"] else None)
    c.metric("Investment allowance", f"{euro(costs['low'])}–{euro(costs['high'])}")
    d.metric("Annual operating allowance", euro(costs["annual"]))
    st.caption(f"{st.session_state.project['years']}-year investment + operating allowance: {euro(costs['lifecycle_low'])}–{euro(costs['lifecycle_high'])}. No discounting, inflation, tariff escalation, replacement or residual value is modelled.")
    if costs["high"] > st.session_state.project["budget"]:
        st.warning(f"The high investment estimate exceeds your {euro(st.session_state.project['budget'])} investment budget by {euro(costs['high'] - st.session_state.project['budget'])}.")
    if not base["complete"]:
        st.info("Complete the positive-weight assessment to compare overall scores. You can still prepare quantities, costs and responsibilities.")
    if selected_actions():
        st.dataframe(pd.DataFrame(selected_actions())[["Action", "Quantity", "Investment low (EUR)", "Investment high (EUR)", "Owner", "Timing"]], hide_index=True, width="stretch")


def action_plan():
    st.subheader("Choose a response, understand its consequences")
    st.write("Start with the problem, not the equipment. Price each intervention using its actual quantity; site area is context, not a multiplier for every action.")
    a, b = st.columns([2, 1])
    focus = a.selectbox("Theme to improve", ["All themes"] + [c["name"] for c in CRITERIA], key="_plan_theme")
    kind = b.selectbox("Intervention type", ["All types", "Quick win", "Design change", "Advanced tool"], key="_plan_kind")
    include = st.checkbox("Also show unassessed items and items rated 3 or 4", key="_show_all")
    summary_rows = evaluate(st.session_state.assessment, st.session_state.weights)["rows"]
    norm = {r["id"]: r["normalised_weight"] for r in summary_rows}
    counts = {r["id"]: r["applicable"] for r in summary_rows}
    def headroom(action):
        item = st.session_state.assessment[action["issue"]]
        cid = ISSUE_CRITERION[action["issue"]]
        return (4 - item["rating"]) / 4 * norm[cid] / max(1, counts[cid]) if item["status"] == "Assessed" else 0
    candidates = []
    for action in ACTIONS:
        item = st.session_state.assessment[action["issue"]]
        criterion = next(c for c in CRITERIA if c["id"] == ISSUE_CRITERION[action["issue"]])
        selected = st.session_state.plan.get(action["id"], {}).get("selected", False)
        if focus != "All themes" and criterion["name"] != focus or kind != "All types" and action["kind"] != kind:
            continue
        if item["status"] == "Not applicable" and not selected:
            continue
        if not include and not selected and item["severity"] == "Routine review" and (item["status"] != "Assessed" or item["rating"] >= 3):
            continue
        candidates.append(action)
    candidates.sort(key=lambda a: (-SEVERITIES.index(st.session_state.assessment[a["issue"]]["severity"]),
        -headroom(a), a["low"]))
    st.caption("Options are ordered by concern level, then remaining weighted score headroom, then starting unit allowance. Headroom is not a predicted benefit or a cost-effectiveness estimate.")
    if not candidates:
        st.info("No interventions match these filters. Assess a problem first, or include unassessed items to explore the library.")
    for action in candidates:
        item = st.session_state.assessment[action["issue"]]
        if action["id"] not in st.session_state.plan:
            config = default_action(action)
            config["target"] = item["rating"]
            st.session_state.plan[action["id"]] = config
        config = st.session_state.plan[action["id"]]
        prefix = f"_action_{action['id']}"
        label = ("Selected · " if config["selected"] else "") + f"{action['title']} · {action['kind']}"
        with st.expander(label, expanded=config["selected"]):
            st.markdown(f"**Problem:** {ISSUES[action['issue']]['problem']}")
            st.write(f"Possible consequence: {ISSUES[action['issue']]['consequence']}")
            if item["observation"]:
                st.write("Your observation: " + item["observation"])
            st.caption(f"Current assessment: {item['status']}" + (f" · {item['rating']}/4" if item["status"] == "Assessed" else "") + f" · {item['severity']}")
            if item["status"] == "Assessed":
                st.caption(f"Maximum remaining score headroom for this subcriterion: {headroom(action):.2f} points. Actions addressing the same item share this headroom.")
            if item["status"] == "Not applicable":
                st.warning("This item is now excluded from assessment. Deselect the action if it is no longer needed; its costs remain in the plan until removed.")
            left, right = st.columns(2)
            left.markdown(f"**Expected benefit**  \n{action['benefit']}")
            right.markdown(f"**Trade-offs and side effects**  \n{action['tradeoff']}")
            st.write("Before committing: " + action["prerequisite"])
            st.caption(f"Starting allowance: {euro(action['low'])}–{euro(action['high'])} per {action['unit']}; annual operation {euro(action['annual'])} per unit. {action['cost_basis']}")
            config["selected"] = st.checkbox("Include in my action plan", key=widget_key(prefix + "_selected", config["selected"]))
            if config["selected"]:
                cols = st.columns(4)
                for col, field, title in zip(cols, ("quantity", "low", "high", "annual"),
                    (f"Quantity · {action['unit']}", "Unit investment low (€)", "Unit investment high (€)", "Annual cost per unit (€)")):
                    config[field] = col.number_input(title, min_value=0.0, max_value=1e9, step=1.0,
                        key=widget_key(prefix + "_" + field, float(config[field])))
                if config["low"] > config["high"]:
                    st.error("The low unit cost must not exceed the high unit cost. Correct it before comparing or exporting.")
                if config["quantity"] == 0:
                    st.warning("Zero quantity: this action has no cost or projected rating effect.")
                if item["status"] == "Assessed":
                    config["target"] = st.slider("Expected rating after implementation and verification", 0, 4,
                        key=widget_key(prefix + "_target", config["target"]), help="Choose a target supported by the rubric. Selecting equipment does not prove improvement.")
                    if config["target"] < item["rating"]:
                        st.caption("A lower target does not reduce the scenario rating. Reassess adverse effects on other themes separately.")
                else:
                    st.caption("No projected gain is assigned to an unassessed item. Establish a baseline first.")
                a, b = st.columns(2)
                config["owner"] = a.text_input("Responsible owner", max_chars=1000, key=widget_key(prefix + "_owner", config["owner"]))
                config["timing"] = b.text_input("Timing or milestone", max_chars=1000, key=widget_key(prefix + "_timing", config["timing"]))
    with st.expander("Account for side effects across themes"):
        st.write("Example: additional lighting may improve a dark route while worsening spill into homes. Add a lower expected rating for glare to see the net effect. These explicit assumptions override action targets for the selected item and never alter the baseline.")
        known = [k for k, item in st.session_state.assessment.items() if item["status"] == "Assessed"]
        if known:
            affected = st.selectbox("Affected subcriterion", known, format_func=lambda k: ISSUES[k]["title"], key="_affected")
            expected = st.slider("Expected rating including side effects", 0, 4,
                key=widget_key("_side_effect_" + affected, st.session_state.assessment[affected]["rating"]))
            if st.button("Add or update scenario assumption"):
                st.session_state.adjustments[affected] = expected
            if st.session_state.adjustments:
                st.dataframe(pd.DataFrame([{"Subcriterion": ISSUES[k]["title"], "Expected rating override": v} for k, v in st.session_state.adjustments.items()]), hide_index=True, width="stretch")
                if st.button("Clear cross-theme assumptions"):
                    st.session_state.adjustments = {}
                    st.rerun()
        else:
            st.write("Assess a baseline item first to model a side effect.")
    st.divider()
    st.subheader("Your investment scenario")
    if any(c["selected"] and c["low"] > c["high"] for c in st.session_state.plan.values()):
        st.error("Resolve invalid cost ranges before the scenario can be calculated.")
    else:
        plan_summary()
    st.caption("Targets are assumptions, not guaranteed outcomes. For several actions on one subcriterion, only the highest target is used. Costs are additive: do not select mutually exclusive options together.")


def report():
    st.subheader("A decision record you can take with you")
    if any(c["selected"] and c["low"] > c["high"] for c in st.session_state.plan.values()):
        st.error("Correct invalid cost ranges in your action plan before exporting.")
        return
    plan_summary()
    undocumented = sum(s["status"] == "Assessed" and not s["evidence"].strip() for s in st.session_state.assessment.values())
    unjustified = sum(s["status"] == "Not applicable" and not s.get("na_reason", "").strip() for s in st.session_state.assessment.values())
    if undocumented or unjustified:
        st.warning(f"Evidence review: {undocumented} assessed items have no evidence reference; {unjustified} exclusions have no justification. Scores are self-ratings, not independently verified.")
    urgent = [ISSUES[k]["title"] for k, s in st.session_state.assessment.items() if s["status"] != "Not applicable" and s["severity"] == "Urgent concern"]
    if urgent:
        st.error("Urgent concerns remain visible regardless of the score: " + "; ".join(urgent))
    st.dataframe(pd.DataFrame(assessment_rows()), hide_index=True, width="stretch")
    a, b = st.columns(2)
    a.download_button("Download printable report", report_html().encode("utf-8"), "urban_tranquillity_report.html", "text/html", width="stretch")
    b.download_button("Save assessment backup", json.dumps(snapshot(), ensure_ascii=False, indent=2).encode("utf-8"), "urban_tranquillity_backup.json", "application/json", width="stretch")
    a.download_button("Download ratings and evidence CSV", csv_bytes(assessment_rows()), "urban_tranquillity_assessment.csv", "text/csv", width="stretch")
    if selected_actions():
        b.download_button("Download action plan CSV", csv_bytes(selected_actions()), "urban_tranquillity_actions.csv", "text/csv", width="stretch")
    with st.expander("Scoring method, sources and assumptions"):
        st.write("The original seven themes, default weights and 0–4 scale are retained. Applicable subcriteria have equal weight within each theme. Theme weights are normalised. Missing ratings remain unknown; all-NA themes are excluded. Zero-weight themes do not affect the score.")
        st.write("Coverage is weighted. A complete score means all positive-weight applicable items have ratings; it does not certify their evidence. Review urgent concerns and undocumented ratings separately.")
        st.write("Sources: Nexity plaquette-amenagement-tranquilite-oct-V2.pdf (viewer pages in each item); Hackathon_Tranquillite_deck_etudiants.pptx, slides 13–17; Engagement_et_Territoires_Support_etudiants.docx, sections 8 and 12; Paris&Co × Efus, PDF pages 7, 11, 43–44, 50 and 55.")
        st.write("Source files are not redistributed. Rubrics, aggregation, targets and unit prices are hackathon proposals, not official standards. Validate quantities, quotes and outcomes for the actual site.")


with st.sidebar:
    st.markdown("### Urban Tranquillity")
    st.caption("Project decision workspace")
    route = st.radio("Workspace", ROUTES, key="_route")
    with st.expander("Project context", expanded=False):
        project = st.session_state.project
        project["name"] = st.text_input("Project name", max_chars=200, key=widget_key("_project_name", project["name"]))
        project["stage"] = st.selectbox("Project stage", ["Planning", "Construction", "Completed / in operation"], key=widget_key("_stage", project["stage"]))
        project["area"] = st.number_input("Site area (m²)", min_value=0.0, max_value=1e9, step=100.0, key=widget_key("_area", float(project["area"])))
        project["budget"] = st.number_input("Investment budget (€)", min_value=0.0, max_value=1e12, step=1000.0, key=widget_key("_budget", float(project["budget"])))
        project["years"] = st.slider("Operating cost horizon (years)", 1, 30, key=widget_key("_years", int(project["years"])))
    with st.expander("Adjust theme weights"):
        for criterion in CRITERIA:
            st.session_state.weights[criterion["id"]] = st.number_input(criterion["name"], min_value=0.0, max_value=100.0, step=1.0,
                key=widget_key("_weight_" + criterion["id"], float(st.session_state.weights[criterion["id"]])))
        st.caption("Weights are normalised across applicable themes. Zero excludes a theme from scoring, not from the concern register.")
    with st.expander("Load, save and sample"):
        st.file_uploader("Restore an assessment JSON", type=["json"], key="_upload")
        st.button("Restore file · replaces current data", on_click=restore)
        if st.session_state.get("restore_error"):
            st.error(st.session_state.restore_error)
        st.button("Load fictional sample · replaces current data", on_click=load_sample)
        confirmed = st.checkbox("I have saved anything I need before resetting", key="_confirm_reset")
        st.button("Reset assessment and plan", disabled=not confirmed, on_click=reset_assessment)
        st.caption("Changes live in this browser session. Download a restorable backup in Report and save before closing.")

st.markdown('<div class="eyebrow">URBAN DEVELOPMENT · EVERYDAY EXPERIENCE</div>', unsafe_allow_html=True)
st.title("Urban Tranquillity Score")
st.markdown('<p class="intro">Turn everyday urban problems into a documented assessment and a practical improvement plan.</p>', unsafe_allow_html=True)
st.caption(f"{st.session_state.project['name']} · {st.session_state.project['stage']}")
if st.session_state.sample:
    st.warning("Fictional sample loaded. Observations and evidence are demonstration data.")
if st.session_state.pop("restore_success", False):
    st.success("Assessment restored, including evidence, weights and action costs.")
{"Overview": overview, "Assess the project": assess, "Build an action plan": action_plan, "Report and save": report}[route]()
