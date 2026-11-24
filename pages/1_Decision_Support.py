import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math
from pathlib import Path
import hashlib
from io import BytesIO
from docx import Document
from docx.shared import Pt

st.set_page_config(page_title='Decision Support', page_icon='🏙️', layout='wide')

THEMES = {
    'Mobility and Transport': {'weight':25, 'subs':['Pedestrian Safety','Cycling Infrastructure','Traffic Management']},
    'Lighting and Night Safety': {'weight':20, 'subs':['Street Lighting','Dark Areas','Night Accessibility']},
    'Environmental Comfort': {'weight':20, 'subs':['Urban Heat','Noise Pollution','Green Spaces']},
    'Public Space Management': {'weight':15, 'subs':['Cleanliness','Infrastructure Maintenance','Public Space Organization']},
    'Building Safety and Accessibility': {'weight':20, 'subs':['Building Access','Shared Spaces','Universal Accessibility']},
}
st.title('Decision Support')
st.caption('Video import, simulated AI analysis and automatic scoring')

st.header('1. Video Import')
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
st.header('2. AI Analysis')
if st.button('Run AI analysis simulation', type='primary'):
    st.session_state['decision_analysis_id'] = fingerprint
if st.session_state.get('decision_analysis_id') != fingerprint:
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

st.header('3. Automatic Scoring')
results=[]
for theme,cfg in THEMES.items():
    scores=[auto[sub] for sub in cfg['subs'] if auto[sub] is not None]
    results.append({'Theme':theme,'Weight (%)':cfg['weight'],'Score / 100':sum(scores)/len(scores)*25 if scores else None,'Coverage':f'{len(scores)}/3'})
valid=[r for r in results if r['Score / 100'] is not None]
if valid:
    overall=sum(r['Score / 100']*r['Weight (%)'] for r in valid)/sum(r['Weight (%)'] for r in valid)
    st.metric('Automatic Urban Tranquillity Score',f'{overall:.1f}/100')
    st.dataframe(pd.DataFrame(results),hide_index=True,use_container_width=True)
    st.caption('Missing indicators are excluded. This partial score is illustrative in simulation mode. Main page manual scores are independent.')
else:
    st.warning('No valid indicators available.')
