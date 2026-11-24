import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
from pathlib import Path
import hashlib
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
     'unit':'raised crossing', 'low':10000, 'high':30000, 'impact':'Potentially improves pedestrian safety and crossing legibility.',
     'measure':'Vehicle speeds, crossing visibility, accessibility and user feedback.', 'difficulty':'Medium', 'timeline':'Planning and construction required'},
    {'name':'Energy-Efficient Smart Lighting', 'theme':'Lighting and Night Safety', 'sub':'Dark Areas',
     'problem':'Poorly lit routes can feel unsafe, while outdated lighting may waste electricity and money.',
     'action':'First audit lighting levels and electricity consumption. Replace inefficient fixtures with correctly sized LEDs. Use scheduled dimming during low-traffic periods and optional occupancy sensors where appropriate. Preserve safe visibility, accessibility and legal lighting requirements. Limit glare and light pollution, and maintain the equipment.',
     'unit':'LED light point', 'low':500, 'high':1000, 'impact':'Aims to maintain or improve night-time visibility while reducing electricity consumption and operating costs. Actual savings depend on the baseline, dimming strategy and electricity tariff.',
     'measure':'Lighting adequacy, annual kWh consumed, annual electricity spend, maintenance costs, user feedback and simple payback period.', 'difficulty':'Medium', 'timeline':'Survey, electrical work and commissioning required'},
]

st.title('Urban Tranquillity Score')
st.caption('Urban development assessment: 5 themes, 15 sub-themes and 2 targeted improvement solutions')

st.header('1. Video Import & AI Analysis')
st.caption('Upload a vehicle survey video and preview it. The video mode uses fictional AI indicators for demonstration only; it does not detect objects or measure sound from the video. Import a CSV for actual pre-extracted indicators.')
RULES = {
    'Pedestrian Safety': ('safe_crossings_pct', 'YOLO adapted', 40),
    'Cycling Infrastructure': ('continuous_cycle_routes_pct', 'SegFormer', 55),
    'Traffic Management': ('conflict_free_segments_pct', 'YOLO + ByteTrack', 65),
    'Street Lighting': ('working_lights_pct', 'YOLO + OpenCV', 65),
    'Dark Areas': ('well_lit_segments_pct', 'OpenCV', 30),
    'Night Accessibility': ('clear_night_routes_pct', 'SegFormer', 45),
    'Urban Heat': ('shade_pct', 'SegFormer (shade proxy only)', 35),
    'Noise Pollution': ('noise_dba', 'Calibrated sensor / YAMNet for source classification', 68),
    'Green Spaces': ('vegetation_pct', 'SegFormer', 18),
    'Cleanliness': ('clean_segments_pct', 'YOLO adapted', 75),
    'Infrastructure Maintenance': ('intact_assets_pct', 'YOLO adapted', 70),
    'Public Space Organization': ('clear_paths_pct', 'SegFormer', 80),
    'Building Access': ('clear_entrances_pct', 'YOLO adapted', 65),
    'Shared Spaces': ('adequate_shared_spaces_pct', 'Complementary inspection', 60),
    'Universal Accessibility': ('accessible_routes_pct', 'Vision + complementary inspection', 55),
}
def indicator_score(sub, value):
    if sub == 'Noise Pollution':
        return 4 if value <= 50 else 3 if value <= 55 else 2 if value <= 65 else 1 if value <= 75 else 0
    if sub == 'Green Spaces':
        return sum(value >= t for t in (5,10,20,30))
    return min(4, int(value // 20))

sample = pd.DataFrame([{v[0]:v[2] for v in RULES.values()}])
mode = st.radio('Data source', ['Video upload (simulated AI)', 'Demo dataset (fictional)', 'Uploaded dataset'], horizontal=True)
video_hash = ''
if mode.startswith('Video'):
    video = st.file_uploader('Import a neighborhood survey video', type=['mp4','mov','avi'], help='MP4 with H.264 encoding is recommended for browser playback.')
    if video is None:
        st.info('Upload a video recorded from a survey vehicle to continue.'); st.stop()
    video_bytes = video.getvalue()
    video_hash = hashlib.sha256(video_bytes).hexdigest()
    st.video(video_bytes, format={'mp4':'video/mp4','mov':'video/quicktime','avi':'video/x-msvideo'}[video.name.rsplit('.',1)[-1].lower()])
    st.caption(f'Uploaded video: {video.name} | {len(video_bytes)/1024**2:.1f} MB')
    st.warning('Simulation only: the indicators below are fictional and are not extracted from this video. A calibrated acoustic sensor is required for actual dB(A) measurements.')
    st.markdown('**Proposed AI pipeline:** Video frames → YOLO / SegFormer / OpenCV → visual indicators → scoring. Audio → YAMNet for sound classification; calibrated sensor data for noise levels.')
    data = sample.copy()
    # Do not imply that indoor or calibrated measurements can be inferred from video.
    data = data.drop(columns=['noise_dba','adequate_shared_spaces_pct','accessible_routes_pct'])
else:
    st.download_button('Download sample collected data (CSV)', sample.to_csv(index=False), 'sample_collected_data.csv', 'text/csv')
    upload = st.file_uploader('Import collected indicators (CSV)', type=['csv']) if mode == 'Uploaded dataset' else None
    if mode == 'Uploaded dataset' and upload is None:
        st.info('Upload a CSV to continue.'); st.stop()
    try:
        data = sample if mode.startswith('Demo') else pd.read_csv(upload)
        if data.empty: raise ValueError('Empty dataset')
    except Exception as exc:
        st.error(f'Cannot read CSV: {exc}'); st.stop()
if not mode.startswith('Video'):
    st.dataframe(data, hide_index=True, use_container_width=True)
fingerprint = hashlib.sha256((mode+video_hash+data.to_csv(index=False)).encode()).hexdigest()
if st.button('Run AI analysis simulation', type='primary'):
    st.session_state['analysis_id'] = fingerprint
    for theme,cfg in THEMES.items():
        for sub in cfg['subs']:
            st.session_state.pop(f'score_{theme}_{sub}',None)
    for i in range(2): st.session_state.pop(f'target_{i}',None)
if st.session_state.get('analysis_id') != fingerprint:
    st.info('Run the analysis to generate scores from the selected dataset.'); st.stop()
analysis_rows=[]
auto={}
for sub,(column,model,_) in RULES.items():
    values=pd.to_numeric(data[column],errors='coerce').dropna() if column in data else pd.Series(dtype=float)
    values=values[values.between(0, 140 if sub=='Noise Pollution' else 100)]
    value=None if values.empty else (10*math.log10(sum(10**(v/10) for v in values)/len(values)) if sub=='Noise Pollution' else float(values.mean()))
    auto[sub]=None if value is None else indicator_score(sub,value)
    analysis_rows.append({'Sub-theme':sub,'Proposed extraction':model,'Indicator':column,'Value':None if value is None else round(value,2),'Automatic score':auto[sub]})
analysis_table=pd.DataFrame(analysis_rows)
st.subheader('Simulated AI indicators' if mode.startswith('Video') or mode.startswith('Demo') else 'Imported indicators and calculated scores')
st.dataframe(analysis_table,hide_index=True,use_container_width=True)
st.caption('Prototype thresholds: positive percentages use 20/40/60/80%; vegetation uses 5/10/20/30%; noise uses 50/55/65/75 dB(A). Noise samples must have equal duration and comparable calibrated measurements. Percentage rows should represent equally weighted survey units. Thresholds are illustrative, not regulatory standards.')
st.metric('Data coverage',f'{sum(v is not None for v in auto.values())}/15')
st.header('2. Assess themes and sub-themes')
st.write('Scores are initialized from the imported indicators. Review or adjust them if needed. Missing indicators remain unassessed unless manually supplied.')
rows=[]
weights={}
for theme,cfg in THEMES.items():
    with st.expander(theme,expanded=False):
        weights[theme]=st.number_input('Theme weight (%)',0,100,cfg['weight'],step=5,key=f'weight_{theme}')
        for sub in cfg['subs']:
            options=[None,0,1,2,3,4]
            score=st.selectbox(sub,options,index=options.index(auto[sub]),format_func=lambda x:'Not assessed' if x is None else f'{x}/4',key=f'score_{theme}_{sub}')
            rows.append({'Theme':theme,'Sub-theme':sub,'Score':score})

frame = pd.DataFrame(rows)
frame['Score'] = pd.to_numeric(frame['Score'], errors='coerce')
weight_total = sum(weights[t] for t in THEMES if frame.loc[frame['Theme']==t,'Score'].notna().any())
if weight_total == 0:
    st.error('At least one theme weight must be greater than zero.')
    st.stop()
if weight_total != 100:
    st.warning(f'Assessed theme weights total {weight_total}%. They are normalized to 100%; missing criteria are excluded.')

theme_scores = {theme: frame.loc[frame['Theme'] == theme, 'Score'].mean() / 4 * 100 for theme in THEMES}
overall = sum(theme_scores[theme] * weights[theme] for theme in THEMES if pd.notna(theme_scores[theme])) / weight_total

st.header('3. Results')
a,b,c = st.columns(3)
a.metric('Overall score', f'{overall:.1f}/100')
b.metric('Themes evaluated', str(sum(pd.notna(v) for v in theme_scores.values())))
c.metric('Sub-themes evaluated', str(frame['Score'].count()))
st.progress(min(max(overall/100,0.0),1.0))
chart = pd.DataFrame({'Theme':list(theme_scores), 'Score':list(theme_scores.values())}).set_index('Theme')
st.bar_chart(chart)
weak = frame.dropna(subset=['Score']).sort_values(['Score','Theme']).head(5)
st.subheader('Priority weaknesses')
st.dataframe(weak, use_container_width=True, hide_index=True)

st.header('4. Two targeted solutions')
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
        st.caption('Published French cost benchmark; scope and local conditions must be checked. Not a contractor quote.')
        unit_low = st.number_input('Lower unit-cost benchmark (EUR)', min_value=0, value=sol['low'], step=100, key=f'low_{idx}')
        unit_high = st.number_input('Upper unit-cost benchmark (EUR)', min_value=0, value=sol['high'], step=100, key=f'high_{idx}')
        if unit_high < unit_low:
            st.error('Upper unit cost must be greater than or equal to lower unit cost.')
            st.stop()
        low, high = unit_low*qty, unit_high*qty
        st.write(f'**Estimated cost for {qty} unit(s):** EUR {low:,.0f} to EUR {high:,.0f}')
        if idx == 0:
            st.markdown('**Reference:** [Plateforme des coûts : traffic calming measures](https://reseau-velo-marche.org/plateforme-des-couts/amenagements/dispositifs-de-moderation-de-trafic/) : EUR 10,000–30,000 per raised crossing/plateau traversant (2025 benchmark).')
        else:
            st.markdown('**References:** [Cerema : public lighting renovation](https://www.cerema.fr/fr/actualites/eclairage-public-poste-cle-reduire-consommations-energie) : around EUR 500 per luminaire for a simple LED renovation; [French IGF report landing page](https://www.igf.finances.gouv.fr/igf/accueil/nos-activites/rapports-de-missions/liste-de-tous-les-rapports-de-mi/linvestissement-des-collectivite.html) : EUR 1,000 upper planning assumption; exact annex figure not independently verified.')
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
            else:
                st.warning('These assumptions do not generate positive annual savings. Adjust the lighting design or compare alternatives.')
        selected[idx] = chosen
        quantities[idx] = qty
        sol.setdefault('editable_costs', {})['low'] = unit_low
        sol['editable_costs']['high'] = unit_high

st.header('5. Improvement scenario')
st.caption('Choose a hypothetical score after implementation for each selected solution. Gains are not guaranteed and must be validated after works.')
new_frame = frame.copy()
low_total, high_total = 0,0
for idx, sol in enumerate(SOLUTIONS):
    if selected[idx]:
        mask = (new_frame['Theme']==sol['theme']) & (new_frame['Sub-theme']==sol['sub'])
        raw_score = new_frame.loc[mask,'Score'].iloc[0]
        if pd.isna(raw_score):
            st.info(f'{sol["name"]}: no baseline score; no projected gain calculated.')
            low_total += sol['editable_costs']['low']*quantities[idx]
            high_total += sol['editable_costs']['high']*quantities[idx]
            continue
        old_score = int(raw_score)
        target = st.selectbox(f'Expected score after: {sol["name"]}', list(range(old_score,5)), index=min(1,4-old_score), key=f'target_{idx}_{old_score}')
        new_frame.loc[mask,'Score'] = target
        low_total += sol['editable_costs']['low']*quantities[idx]
        high_total += sol['editable_costs']['high']*quantities[idx]
new_theme_scores = {theme: new_frame.loc[new_frame['Theme']==theme,'Score'].mean()/4*100 for theme in THEMES}
new_overall = sum(new_theme_scores[t]*weights[t] for t in THEMES if pd.notna(new_theme_scores[t]))/weight_total
x,y,z = st.columns(3)
x.metric('Current score', f'{overall:.1f}/100')
y.metric('Scenario score', f'{new_overall:.1f}/100', delta=f'{new_overall-overall:+.1f} points')
z.metric('Estimated budget', f'€{low_total:,.0f} - €{high_total:,.0f}')

st.subheader('Before vs. after: radar chart')
labels=list(THEMES)
fig=go.Figure()
for name, scores, color, dash in [('Current',theme_scores,'#2563eb','solid'),('After solutions',new_theme_scores,'#16a34a','dash')]:
    vals=[scores[t] if pd.notna(scores[t]) else None for t in labels]
    fig.add_trace(go.Scatterpolar(r=vals+[vals[0]],theta=labels+[labels[0]],name=name,line=dict(color=color,dash=dash),mode='lines+markers',connectgaps=False,fill='toself' if all(v is not None for v in vals) else None,opacity=.75))
fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,100])),height=520,margin=dict(l=100,r=100,t=45,b=50),legend=dict(orientation='h'))
st.plotly_chart(fig,use_container_width=True)

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
    doc.add_paragraph(f'Benchmark-based total implementation budget: EUR {low_total:,.0f} to EUR {high_total:,.0f}.')
    doc.add_paragraph('Method: Each sub-theme is scored from 0 (not addressed) to 4 (exemplary). The three sub-theme scores within a theme are averaged and converted to 100. Theme scores are combined using the user-selected weights, normalized to 100%.')
    doc.add_heading('Data import and simulated AI analysis', level=1)
    doc.add_paragraph(f'Data source: {mode}. Video and demo modes use fictional indicators; CSV mode uses imported indicators. No raw AI inference. Coverage: {sum(v is not None for v in auto.values())}/15. Missing values excluded from scoring; weights normalized over assessed themes.')
    for item in analysis_rows:
        doc.add_paragraph(f"{item['Sub-theme']}: {item['Value']} ({item['Indicator']}); automatic score: {item['Automatic score']}")
    doc.add_heading('2. Themes and sub-theme assessment', level=1)
    for theme, cfg in THEMES.items():
        doc.add_heading(theme, level=2)
        doc.add_paragraph(f'Weight: {weights[theme]}% (normalized share: {weights[theme]/weight_total*100:.1f}%). Theme score: {theme_scores[theme]:.1f}/100.')
        for sub in cfg['subs']:
            initial = frame.loc[(frame['Theme']==theme)&(frame['Sub-theme']==sub),'Score'].iloc[0]
            projected = new_frame.loc[(new_frame['Theme']==theme)&(new_frame['Sub-theme']==sub),'Score'].iloc[0]
            doc.add_paragraph(f"{sub}: current {int(initial) if pd.notna(initial) else 'Not assessed'}; projected {int(projected) if pd.notna(projected) else 'Not assessed'} (scale 0–4)", style='List Bullet')
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
        doc.add_paragraph(f'Quantity: {qty} {sol["unit"]}(s). Benchmark-based budget: EUR {sol["editable_costs"]["low"]*qty:,.0f} to EUR {sol["editable_costs"]["high"]*qty:,.0f}.')
        doc.add_paragraph(f'Included in improvement scenario: {"Yes" if selected[idx] else "No"}.')
        if idx == 1:
            doc.add_heading('Energy and financial assessment', level=3)
            doc.add_paragraph(f'Existing power per luminaire: {old_watts:.1f} W. Proposed LED: {new_watts:.1f} W. Average dimming power: {dim_factor}%. Lighting hours per night: {hours:.1f}. Electricity tariff: EUR {tariff:.2f}/kWh.')
            doc.add_paragraph(f'Current consumption: {baseline_kwh:,.0f} kWh/year; proposed: {proposed_kwh:,.0f} kWh/year; difference: {saved_kwh:,.0f} kWh/year ({energy_saving_pct:.1f}%).')
            doc.add_paragraph(f'Current electricity cost: EUR {baseline_kwh*tariff:,.0f}/year; proposed: EUR {proposed_kwh*tariff:,.0f}/year. Electricity savings: EUR {annual_electric_savings:,.0f}/year. Optional maintenance savings: EUR {extra_maintenance:,.0f}/year.')
            if annual_total_savings > 0:
                doc.add_paragraph(f'Illustrative simple payback: {sol["editable_costs"]["low"]*qty/annual_total_savings:.1f} to {sol["editable_costs"]["high"]*qty/annual_total_savings:.1f} years (full installation cost basis).')
            else:
                doc.add_paragraph('Under the selected assumptions, there are no positive annual savings.')
    doc.add_heading('5. Results and limitations', level=1)
    doc.add_paragraph(f'Current score: {overall:.1f}/100. Projected score: {new_overall:.1f}/100. Estimated change: {new_overall-overall:+.1f} points.')
    doc.add_paragraph('Scores, weights, projected gains and energy assumptions are illustrative. Unit-cost defaults combine published French references and planning assumptions and are not supplier quotations or guaranteed project prices. Smart lighting controls and sensors are not included in the LED unit-price defaults. Actual costs and benefits require a site survey, technical design and follow-up measurements. Energy-efficient dimming must preserve required visibility and safety.')
    doc.add_paragraph('The two solutions target pedestrian crossings and dark pedestrian areas. Other low-scoring sub-themes are assessed but do not receive additional solution proposals.')
    doc.add_heading('6. Cost references and scope', level=1)
    doc.add_paragraph('Raised pedestrian crossing / plateau traversant: EUR 10,000 to 30,000 per unit (2025 benchmark). Source: Plateforme des coûts, https://reseau-velo-marche.org/plateforme-des-couts/amenagements/dispositifs-de-moderation-de-trafic/')
    doc.add_paragraph('Simple LED renovation: approximately EUR 500 per luminaire. Source: Cerema, https://www.cerema.fr/fr/actualites/eclairage-public-poste-cle-reduire-consommations-energie')
    doc.add_paragraph('Upper planning assumption: EUR 1,000 per light point; exact annex figure not independently verified. Related IGF report landing page: https://www.igf.finances.gouv.fr/igf/accueil/nos-activites/rapports-de-missions/liste-de-tous-les-rapports-de-mi/linvestissement-des-collectivite.html')
    doc.add_paragraph('The EUR 500 and EUR 1,000 lighting figures describe different scopes. They do not price smart sensors, remote management, or all site-specific works. Energy savings are calculated from user-editable assumptions and are not verified savings.')
    for style in ['Normal']:
        doc.styles[style].font.size = Pt(10)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()

st.header('6. Export full Word report')
st.write('Download one editable Word document summarizing all 5 themes, 15 sub-themes, both detailed solutions, assessment scores, scenario, costs and energy savings.')
st.download_button('Download complete Word report', data=build_word_report(), file_name='urban_tranquillity_full_report.docx', mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
