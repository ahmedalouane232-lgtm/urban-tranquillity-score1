import streamlit as st
import pandas as pd
from io import BytesIO
from docx import Document
from docx.shared import Pt

st.set_page_config(page_title='Urban Tranquillity Score', page_icon='🏙️', layout='wide')

THEMES = {
    'Mobility and Transport': {'weight':25, 'subs':['Pedestrian Safety','Cycling Infrastructure','Traffic Management']},
    'Lighting and Night Safety': {'weight':20, 'subs':['Street Lighting','Dark Areas','Night Accessibility']},
    'Environmental Comfort': {'weight':20, 'subs':['Urban Heat','Noise Pollution','Green Spaces']},
    'Public Space Management': {'weight':15, 'subs':['Cleanliness','Infrastructure Maintenance','Public Space Organization']},
    'Building Safety and Accessibility': {'weight':20, 'subs':['Building Access','Shared Spaces','Universal Accessibility']},
}
SOLUTIONS = [
    {'name':'Safer Pedestrian Crossings', 'theme':'Mobility and Transport', 'sub':'Pedestrian Safety',
     'problem':'Poorly visible crossings and vehicle speed can create conflicts between road users.',
     'action':'Audit pedestrian routes and vehicle speeds. Where technically and legally suitable, install a raised crossing, improve markings and remove visibility obstructions. Verify drainage and accessibility.',
     'unit':'crossing', 'low':6000, 'high':18000, 'impact':'Potentially improves pedestrian safety and crossing legibility.',
     'measure':'Vehicle speeds, crossing visibility, accessibility and user feedback.', 'difficulty':'Medium', 'timeline':'Planning and construction required'},
    {'name':'Energy-Efficient Smart Lighting', 'theme':'Lighting and Night Safety', 'sub':'Dark Areas',
     'problem':'Poorly lit routes can feel unsafe, while outdated lighting may waste electricity and money.',
     'action':'First audit lighting levels and electricity consumption. Replace inefficient fixtures with correctly sized LEDs. Use scheduled dimming during low-traffic periods and optional occupancy sensors where appropriate. Preserve safe visibility, accessibility and legal lighting requirements. Limit glare and light pollution, and maintain the equipment.',
     'unit':'light point', 'low':1500, 'high':5000, 'impact':'Aims to maintain or improve night-time visibility while reducing electricity consumption and operating costs. Actual savings depend on the baseline, dimming strategy and electricity tariff.',
     'measure':'Lighting adequacy, annual kWh consumed, annual electricity spend, maintenance costs, user feedback and simple payback period.', 'difficulty':'Medium', 'timeline':'Survey, electrical work and commissioning required'},
]

st.title('Urban Tranquillity Score')
st.caption('Urban development assessment: 5 themes, 15 sub-themes and 2 targeted improvement solutions')
st.info('Methodology note: Scores, weights, costs and simulated gains are illustrative project assumptions, not official Nexity standards or supplier quotations.')

st.header('1. Assess themes and sub-themes')
st.write('Set each sub-theme score from 0 (not addressed) to 4 (exemplary). Adjust theme weights as needed.')
rows = []
weights = {}
for theme, cfg in THEMES.items():
    with st.expander(theme, expanded=False):
        weights[theme] = st.number_input('Theme weight (%)', min_value=0, max_value=100, value=cfg['weight'], step=5, key=f'weight_{theme}')
        for sub in cfg['subs']:
            score = st.slider(sub, 0, 4, 2, key=f'score_{theme}_{sub}')
            rows.append({'Theme':theme, 'Sub-theme':sub, 'Score':score})

frame = pd.DataFrame(rows)
weight_total = sum(weights.values())
if weight_total == 0:
    st.error('At least one theme weight must be greater than zero.')
    st.stop()
if weight_total != 100:
    st.warning(f'Theme weights total {weight_total}%. They are automatically normalized to 100% for scoring.')

theme_scores = {theme: frame.loc[frame['Theme'] == theme, 'Score'].mean() / 4 * 100 for theme in THEMES}
overall = sum(theme_scores[theme] * weights[theme] for theme in THEMES) / weight_total

st.header('2. Results')
a,b,c = st.columns(3)
a.metric('Overall score', f'{overall:.1f}/100')
b.metric('Themes evaluated', '5')
c.metric('Sub-themes evaluated', '15')
st.progress(min(max(overall/100,0.0),1.0))
chart = pd.DataFrame({'Theme':list(theme_scores), 'Score':list(theme_scores.values())}).set_index('Theme')
st.bar_chart(chart)
weak = frame.sort_values(['Score','Theme']).head(5)
st.subheader('Priority weaknesses')
st.dataframe(weak, use_container_width=True, hide_index=True)

st.header('3. Two targeted solutions')
st.write('Only two improvement solutions are included. They address Pedestrian Safety and Dark Areas. Other low-scoring sub-themes are identified but do not receive an invented recommendation.')
selected = {}
quantities = {}
for idx, sol in enumerate(SOLUTIONS):
    with st.expander(f'Solution {idx+1}: {sol["name"]}', expanded=True):
        st.write(f'**Theme:** {sol["theme"]}  |  **Sub-theme:** {sol["sub"]}')
        st.write('**Problem:** ' + sol['problem'])
        st.write('**Implementation:** ' + sol['action'])
        st.write('**Expected benefit:** ' + sol['impact'])
        st.write('**Monitoring indicators:** ' + sol['measure'])
        st.write('**Feasibility:** ' + sol['difficulty'] + '. ' + sol['timeline'])
        chosen = st.checkbox('Include this solution in the scenario', value=True, key=f'choose_{idx}')
        qty = st.number_input(f'Number of {sol["unit"]}s', min_value=1, max_value=10000, value=2 if idx==0 else 8, key=f'qty_{idx}')
        low, high = sol['low']*qty, sol['high']*qty
        st.write(f'**Illustrative cost range:** €{low:,.0f} to €{high:,.0f} (excluding site-specific constraints)')
        if idx == 1:
            st.markdown('#### Energy and financial savings simulator')
            st.caption('Compare existing lighting with a proposed efficient LED and dimming system. Editable assumptions, not guaranteed results.')
            ec1, ec2 = st.columns(2)
            with ec1:
                old_watts = st.number_input('Existing power per light (W)', min_value=0.0, value=120.0, step=10.0, key='old_watts')
                new_watts = st.number_input('Proposed LED power per light (W)', min_value=0.0, value=55.0, step=5.0, key='new_watts')
                hours = st.number_input('Lighting hours per night', min_value=0.0, max_value=24.0, value=11.0, step=0.5, key='hours')
            with ec2:
                dim_factor = st.slider('Average LED power after dimming (%)', min_value=10, max_value=100, value=75, step=5, key='dim_factor')
                tariff = st.number_input('Electricity tariff (EUR/kWh)', min_value=0.0, value=0.22, step=0.01, format='%.2f', key='tariff')
                extra_maintenance = st.number_input('Annual maintenance savings (EUR, optional)', min_value=0.0, value=0.0, step=50.0, key='maintenance_savings')
            baseline_kwh = qty * old_watts * hours * 365 / 1000
            proposed_kwh = qty * new_watts * (dim_factor / 100) * hours * 365 / 1000
            saved_kwh = baseline_kwh - proposed_kwh
            annual_electric_savings = saved_kwh * tariff
            annual_total_savings = annual_electric_savings + extra_maintenance
            energy_saving_pct = (saved_kwh / baseline_kwh * 100) if baseline_kwh > 0 else 0
            m1, m2, m3 = st.columns(3)
            m1.metric('Annual energy difference', f'{saved_kwh:,.0f} kWh')
            m2.metric('Annual electricity savings', f'EUR {annual_electric_savings:,.0f}')
            m3.metric('Energy reduction', f'{energy_saving_pct:.1f}%')
            st.write(f'**Current annual electricity cost:** EUR {baseline_kwh * tariff:,.0f}')
            st.write(f'**Proposed annual electricity cost:** EUR {proposed_kwh * tariff:,.0f}')
            if annual_total_savings > 0:
                st.write(f'**Simple payback based on full illustrative installation cost:** {low / annual_total_savings:.1f} to {high / annual_total_savings:.1f} years')
                st.caption('Payback uses total installation cost, not incremental upgrade cost. It excludes financing, replacement cycles, future tariff changes and other operating expenses.')
            else:
                st.warning('These assumptions do not generate positive annual savings. Adjust the lighting design or compare alternatives.')
            st.caption('Dimming is only appropriate if required lighting levels and safety are maintained. Check local rules and perform a site-specific lighting study.')
        selected[idx] = chosen
        quantities[idx] = qty

st.header('4. Improvement scenario')
st.caption('Choose a hypothetical score after implementation for each selected solution. Gains are not guaranteed and must be validated after works.')
new_frame = frame.copy()
low_total, high_total = 0,0
for idx, sol in enumerate(SOLUTIONS):
    if selected[idx]:
        mask = (new_frame['Theme']==sol['theme']) & (new_frame['Sub-theme']==sol['sub'])
        old_score = int(new_frame.loc[mask,'Score'].iloc[0])
        target = st.slider(f'Expected score after: {sol["name"]}', min_value=old_score, max_value=4, value=min(4,old_score+1), key=f'target_{idx}')
        new_frame.loc[mask,'Score'] = target
        low_total += sol['low']*quantities[idx]
        high_total += sol['high']*quantities[idx]
new_theme_scores = {theme: new_frame.loc[new_frame['Theme']==theme,'Score'].mean()/4*100 for theme in THEMES}
new_overall = sum(new_theme_scores[t]*weights[t] for t in THEMES)/weight_total
x,y,z = st.columns(3)
x.metric('Current score', f'{overall:.1f}/100')
y.metric('Scenario score', f'{new_overall:.1f}/100', delta=f'{new_overall-overall:+.1f} points')
z.metric('Estimated budget', f'€{low_total:,.0f} - €{high_total:,.0f}')
st.caption('All budgets are illustrative and require site-specific verification. Design studies, permits, taxes and unforeseen works may not be included.')

def build_word_report():
    """Create a complete editable Word summary of the current assessment."""
    doc = Document()
    section = doc.sections[0]
    section.header.paragraphs[0].text = 'URBAN TRANQUILLITY SCORE  |  ASSESSMENT REPORT'
    doc.add_heading('Urban Tranquillity Assessment', 0)
    doc.add_paragraph('Five themes | Fifteen sub-themes | Two targeted solutions')
    doc.add_paragraph('This document summarizes the assessment and improvement scenario generated by the application. All values reflect the currently selected inputs.')
    doc.add_heading('1. Executive summary', level=1)
    doc.add_paragraph(f'Current overall score: {overall:.1f}/100')
    doc.add_paragraph(f'Projected scenario score: {new_overall:.1f}/100 (change: {new_overall-overall:+.1f} points)')
    doc.add_paragraph(f'Illustrative total implementation budget: EUR {low_total:,.0f} to EUR {high_total:,.0f}.')
    doc.add_paragraph('Method: Each sub-theme is scored from 0 (not addressed) to 4 (exemplary). The three sub-theme scores within a theme are averaged and converted to 100. Theme scores are combined using the user-selected weights, normalized to 100%.')
    doc.add_heading('2. Themes and sub-theme assessment', level=1)
    for theme, cfg in THEMES.items():
        doc.add_heading(theme, level=2)
        doc.add_paragraph(f'Weight: {weights[theme]}% (normalized share: {weights[theme]/weight_total*100:.1f}%). Theme score: {theme_scores[theme]:.1f}/100.')
        for sub in cfg['subs']:
            initial = int(frame.loc[(frame['Theme']==theme)&(frame['Sub-theme']==sub),'Score'].iloc[0])
            projected = int(new_frame.loc[(new_frame['Theme']==theme)&(new_frame['Sub-theme']==sub),'Score'].iloc[0])
            doc.add_paragraph(f'{sub}: current {initial}/4; projected {projected}/4', style='List Bullet')
    doc.add_heading('3. Priority weaknesses', level=1)
    for _, item in weak.iterrows():
        doc.add_paragraph(f"{item['Theme']} : {item['Sub-theme']} ({int(item['Score'])}/4)", style='List Bullet')
    doc.add_heading('4. Proposed solutions', level=1)
    for idx, sol in enumerate(SOLUTIONS):
        doc.add_heading(f'Solution {idx+1}: {sol["name"]}', level=2)
        doc.add_paragraph(f'Target: {sol["theme"]} / {sol["sub"]}')
        doc.add_paragraph(f'Problem: {sol["problem"]}')
        doc.add_paragraph(f'Implementation: {sol["action"]}')
        doc.add_paragraph(f'Expected benefit: {sol["impact"]}')
        doc.add_paragraph(f'Monitoring indicators: {sol["measure"]}')
        doc.add_paragraph(f'Feasibility: {sol["difficulty"]}; {sol["timeline"]}.')
        qty = quantities[idx]
        doc.add_paragraph(f'Quantity: {qty} {sol["unit"]}(s). Illustrative budget: EUR {sol["low"]*qty:,.0f} to EUR {sol["high"]*qty:,.0f}.')
        doc.add_paragraph(f'Included in improvement scenario: {"Yes" if selected[idx] else "No"}.')
        if idx == 1:
            doc.add_heading('Energy and financial assessment', level=3)
            doc.add_paragraph(f'Existing power per luminaire: {old_watts:.1f} W. Proposed LED: {new_watts:.1f} W. Average dimming power: {dim_factor}%. Lighting hours per night: {hours:.1f}. Electricity tariff: EUR {tariff:.2f}/kWh.')
            doc.add_paragraph(f'Current consumption: {baseline_kwh:,.0f} kWh/year; proposed: {proposed_kwh:,.0f} kWh/year; difference: {saved_kwh:,.0f} kWh/year ({energy_saving_pct:.1f}%).')
            doc.add_paragraph(f'Current electricity cost: EUR {baseline_kwh*tariff:,.0f}/year; proposed: EUR {proposed_kwh*tariff:,.0f}/year. Electricity savings: EUR {annual_electric_savings:,.0f}/year. Optional maintenance savings: EUR {extra_maintenance:,.0f}/year.')
            if annual_total_savings > 0:
                doc.add_paragraph(f'Illustrative simple payback: {sol["low"]*qty/annual_total_savings:.1f} to {sol["high"]*qty/annual_total_savings:.1f} years (full installation cost basis).')
            else:
                doc.add_paragraph('Under the selected assumptions, there are no positive annual savings.')
    doc.add_heading('5. Results and limitations', level=1)
    doc.add_paragraph(f'Current score: {overall:.1f}/100. Projected score: {new_overall:.1f}/100. Estimated change: {new_overall-overall:+.1f} points.')
    doc.add_paragraph('Scores, weights, unit costs, projected gains and energy assumptions are illustrative, not official Nexity standards, supplier quotes or verified outcomes. Actual costs and benefits require a site survey, technical design and follow-up measurements. Energy-efficient dimming must preserve required visibility and safety.')
    doc.add_paragraph('The two solutions target pedestrian crossings and dark pedestrian areas. Other low-scoring sub-themes are assessed but do not receive additional solution proposals.')
    for style in ['Normal']:
        doc.styles[style].font.size = Pt(10)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()

st.header('5. Export full Word report')
st.write('Download one editable Word document summarizing all 5 themes, 15 sub-themes, both detailed solutions, assessment scores, scenario, costs and energy savings.')
st.download_button('Download complete Word report', data=build_word_report(), file_name='urban_tranquillity_full_report.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
