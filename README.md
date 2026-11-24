# Urban Tranquillity Score

English Streamlit assessment for 5 themes, 15 sub-themes and 2 detailed solutions.

- Editable theme weights and sub-theme scores
- Current and projected score out of 100
- Two solutions: safer pedestrian crossings and energy-efficient smart lighting
- Editable cost, electricity and energy-saving assumptions
- **One Word (.docx) export** summarizing all scores, solutions, costs and savings
- Project information sidebar and CSV export removed

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Render

Upload all four files to the root of a GitHub repository and deploy using `render.yaml`.

Cost defaults are grounded in published French benchmarks (links in the app and exported Word report); they are not site-specific quotations. LED figures cover different renovation scopes and exclude smart sensors/remote management. Scores and energy savings are illustrative simulations.

## Video demonstration
Select Video upload (simulated AI), upload an MP4 (recommended), MOV or AVI, preview it and click Run AI analysis simulation. Video mode uses explicitly fictional indicators, not video inference. Browser playback depends on codec. CSV mode remains available for real pre-extracted indicators. No calibrated sound levels are inferred from video audio.
