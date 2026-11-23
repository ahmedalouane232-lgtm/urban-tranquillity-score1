import pandas as pd
import streamlit as st

st.set_page_config(page_title="Urban Tranquillity Score", page_icon="🏙️", layout="wide")

CRITERIA = [
    {"name": "Visibility and wayfinding", "weight": 15, "action": "Improve signs and remove visual obstructions", "low": 300, "high": 1200, "unit": "fixed project"},
    {"name": "Lighting and night-time safety", "weight": 15, "action": "Audit lighting and improve poorly lit areas", "low": 800, "high": 3000, "unit": "lighting point"},
    {"name": "Mobility and pedestrian routes", "weight": 20, "action": "Improve crossings and pedestrian route continuity", "low": 70, "high": 220, "unit": "linear metre"},
    {"name": "Accessibility and inclusion", "weight": 10, "action": "Remove priority accessibility barriers", "low": 500, "high": 2500, "unit": "intervention"},
    {"name": "Comfort and green spaces", "weight": 15, "action": "Provide shade and improve planted areas", "low": 45, "high": 160, "unit": "square metre"},
    {"name": "Maintenance and management", "weight": 15, "action": "Establish a maintenance and monitoring plan", "low": 400, "high": 1500, "unit": "fixed project"},
    {"name": "Community engagement and monitoring", "weight": 10, "action": "Consult residents and collect feedback", "low": 300, "high": 1300, "unit": "workshop"},
]

st.title("🏙️ Urban Tranquillity Score")
st.caption("Urban development assessment prototype. Scores, weights and costs are illustrative, not official standards.")

with st.sidebar:
    st.header("Project details")
    project = st.text_input("Project name", "Pilot neighbourhood")
    area = st.number_input("Site area (m²)", min_value=100, value=5000, step=100)
    phase = st.selectbox("Project stage", ["Planning", "Construction", "Completed / in operation"])
    st.info("Cost estimates are examples. Confirm unit prices and quantities with local quotations.")
    if st.button("Reset scores and weights"):
        for i, criterion in enumerate(CRITERIA):
            st.session_state[f"rating_{i}"] = 2
            st.session_state[f"weight_{i}"] = criterion["weight"]
        st.rerun()

st.subheader("1. Configure assessment criteria")
st.write("Set a rating from 0 (not addressed) to 4 (excellent). Adjust the importance of each criterion using its weight.")
ratings, weights = {}, {}
for i, criterion in enumerate(CRITERIA):
    with st.container(border=True):
        st.markdown(f"**{criterion['name']}**")
        left, right = st.columns([3, 2])
        ratings[i] = left.slider("Rating (0 to 4)", 0, 4, 2, key=f"rating_{i}")
        weights[i] = right.number_input("Weight", min_value=0, max_value=100, value=criterion["weight"], step=1, key=f"weight_{i}")

weight_total = sum(weights.values())
if weight_total == 0:
    st.error("At least one criterion must have a weight greater than zero.")
    st.stop()

if weight_total != 100:
    st.info(f"Your weights add up to {weight_total}. They are automatically normalised to 100% for scoring.")

normalised = {i: weights[i] / weight_total * 100 for i in weights}
score = sum(ratings[i] / 4 * normalised[i] for i in ratings)

st.subheader("2. Assessment results")
a, b, c = st.columns(3)
a.metric("Overall score", f"{score:.1f} / 100")
b.metric("Site area", f"{area:,} m²")
c.metric("Criteria to improve", sum(value < 3 for value in ratings.values()))
st.progress(min(1.0, score / 100))

chart = pd.DataFrame({"Criterion": [c["name"] for c in CRITERIA], "Rating": [ratings[i] for i in range(len(CRITERIA))]}).set_index("Criterion")
st.bar_chart(chart)

st.subheader("3. Recommendations and quick wins")
recommendations = []
for i, criterion in enumerate(CRITERIA):
    if ratings[i] >= 3:
        continue
    gain = (4 - ratings[i]) / 4 * normalised[i]
    recommendations.append({
        "Criterion": criterion["name"], "Suggested action": criterion["action"],
        "Priority": "High" if ratings[i] <= 1 else "Medium",
        "Maximum potential gain (points)": round(gain, 1),
        "Unit cost low (EUR)": criterion["low"], "Unit cost high (EUR)": criterion["high"],
        "Unit": criterion["unit"], "index": i,
    })

estimate_rows = []
if recommendations:
    rec_df = pd.DataFrame(recommendations).sort_values("Maximum potential gain (points)", ascending=False)
    st.dataframe(rec_df.drop(columns=["index"]), use_container_width=True, hide_index=True)
    st.caption("Potential gains assume a rating of 4. They are not guaranteed results of the suggested actions.")
    st.subheader("4. Indicative cost estimate")
    st.write("Enter the actual quantity for each action. Site area is contextual information, not a universal cost multiplier.")
    for _, item in rec_df.iterrows():
        quantity = st.number_input(
            f"Quantity for {item['Criterion']} ({item['Unit']})", min_value=0.0,
            value=1.0, step=1.0, key=f"quantity_{int(item['index'])}",
        )
        estimate_rows.append({
            "Action": item["Suggested action"], "Quantity": quantity,
            "Minimum cost (EUR)": round(quantity * item["Unit cost low (EUR)"]),
            "Maximum cost (EUR)": round(quantity * item["Unit cost high (EUR)"]),
        })
    estimates = pd.DataFrame(estimate_rows)
    st.dataframe(estimates, use_container_width=True, hide_index=True)
    st.metric("Estimated total range", f"€{estimates['Minimum cost (EUR)'].sum():,.0f} to €{estimates['Maximum cost (EUR)'].sum():,.0f}")
else:
    st.success("Every criterion has a rating of 3 or 4. Continue monitoring and documenting performance.")

st.subheader("5. Export assessment")
report = pd.DataFrame([
    {"Project": project, "Project stage": phase, "Site area (m²)": area,
     "Criterion": criterion["name"], "Weight entered": weights[i],
     "Normalised weight (%)": round(normalised[i], 2), "Rating (0 to 4)": ratings[i],
     "Score contribution": round(ratings[i] / 4 * normalised[i], 2)}
    for i, criterion in enumerate(CRITERIA)
])
st.download_button("Download assessment CSV", data=report.to_csv(index=False).encode("utf-8-sig"),
                   file_name="urban_tranquillity_assessment.csv", mime="text/csv")
if estimate_rows:
    st.download_button("Download cost estimates CSV", data=pd.DataFrame(estimate_rows).to_csv(index=False).encode("utf-8-sig"),
                       file_name="urban_tranquillity_costs.csv", mime="text/csv")
st.caption("Prototype only. Data is not saved to a server. Validate assessment criteria and costs before professional use.")
