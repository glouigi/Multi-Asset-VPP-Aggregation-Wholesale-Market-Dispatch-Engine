# Deployment guide

Three paths from local laptop to public URL.

## Option 1 — Local / LAN

```bash
# pip route
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) run the notebook once to populate outputs/
jupyter lab VPP_Aggregation_Dispatch.ipynb   # run all cells

# 2) start the dashboard
streamlit run app.py
# -> http://localhost:8501
```

To expose on the LAN (so phones / colleagues can hit it):

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
# -> http://<your-LAN-ip>:8501
```

## Option 2 — Streamlit Community Cloud (free)

1. Push this repo to a public GitHub repository.
2. Go to https://share.streamlit.io/ → **New app** → connect the repo.
3. Set:
   - **Branch:** `main`
   - **Main file path:** `app.py`
   - **Python version:** `3.11`
4. Streamlit Cloud reads `requirements.txt` automatically.
5. Click **Deploy**. ~3 minutes later you get `https://<repo>.streamlit.app`.

> The app reads `outputs/` if present (committed run results) or generates a synthetic preview. For a real-data deploy, run the notebook locally first, commit the resulting CSVs in `outputs/`, then push.

## Option 3 — Docker (Cloud Run, Fly, or any container host)

```bash
# Build
docker build -t vpp-engine .

# Run locally
docker run -p 8501:8501 vpp-engine
# -> http://localhost:8501
```

### Deploy to Google Cloud Run

```bash
PROJECT_ID=<your-gcp-project>
gcloud builds submit --tag gcr.io/$PROJECT_ID/vpp-engine
gcloud run deploy vpp-engine \
  --image gcr.io/$PROJECT_ID/vpp-engine \
  --port 8501 \
  --memory 2Gi \
  --region australia-southeast1 \
  --allow-unauthenticated
```

### Deploy to Fly.io

```bash
fly launch --copy-config --name vpp-engine
fly deploy
```

## CI/CD

The repo ships with `.github/workflows/ci.yml` which:

1. Triggers on every push and PR to `main`
2. Installs deps, sets `USE_NEMOSIS=False` (CI is offline w.r.t. AEMO)
3. Executes the notebook end-to-end with a 25-min timeout
4. Uploads the resulting `outputs/` and executed notebook as build artefacts

Failing the smoke test blocks merges — protecting `main` from regressions.
