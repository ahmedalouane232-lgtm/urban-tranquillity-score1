# Urban Tranquillity Score

English-language Streamlit prototype for evaluating urban development projects. Users can edit ratings and criterion weights, review a normalised score, see recommendations, estimate indicative costs, and export CSV reports.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy to Render

1. Upload `streamlit_app.py`, `requirements.txt`, `render.yaml`, and this `README.md` to the root of a GitHub repository.
2. In Render, select **New > Blueprint**, then connect your repository.
3. Render reads `render.yaml` and builds the Streamlit web service.

The Free plan is subject to Render availability and limitations. Cost figures and scoring weights are illustrative, not official benchmarks.
