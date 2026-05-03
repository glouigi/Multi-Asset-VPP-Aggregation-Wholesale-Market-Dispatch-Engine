# ⚡ MULTI-ASSET VPP — WHOLESALE MARKET DISPATCH ENGINE

## Australian NEM — Multi-Region Price Forecasting → Portfolio Dispatch Optimisation VPP

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-orange?logo=jupyter)](FCAS_Bidding_Bot.ipynb)
[![AEMO](https://img.shields.io/badge/Data-AEMO_DISPATCHPRICE-0078d4)](https://nemweb.com.au)
[![Framework](https://img.shields.io/badge/Master_ML%2FDL-12_Steps-c084fc)](FCAS_Bidding_Bot.ipynb)
[![Streamlit](https://img.shields.io/badge/Streamlit-Bid_Dashboard-ff4b4b?logo=streamlit)](app.py)
____________________________________________

<div align="right">
  <b>Giorgio Ramirez Quiroz</b><br>
  Electrical Engineer | Power Systems & Data Analytics<br>
  
  [![GitHub](https://img.shields.io/badge/github-%23121011.svg?logo=github&logoColor=white)](https://github.com/glouigi)
  [![LinkedIn](https://img.shields.io/badge/linkedin-%230077B5.svg?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/giorgio-ramirez-quiroz)
  [![Gmail Badge](https://img.shields.io/badge/-Gmail-c14438?&logo=Gmail&logoColor=white)](mailto:g.ramirezqui@gmail.com)
</div>


## 📋 Project Description
> Production-ready Virtual Power Plant aggregation and joint dispatch optimisation engine for the **Australian National Electricity Market (NEM)**. Forecasts hourly wholesale prices per region with XGBoost+LightGBM ensembles, then solves a single multi-asset LP that dispatches a heterogeneous portfolio of distributed energy resources (utility BESS, commercial BESS, aggregated home batteries, industrial BESS, pumped hydro) across all five NEM regions.

---

## 🎯 What this project does

A single **bidding desk** runs **5 different DER assets** in **5 different NEM regions** (VIC1, NSW1, SA1, QLD1, TAS1). Each asset:

1. Has its own region's price forecast (one ensemble per region)
2. Contributes to a **joint LP** that maximises portfolio profit subject to per-asset SoC, RTE, power-rating, and operational constraints

The diversification gain over running the largest single asset alone is **measured and reported** as a first-class output — that's the raison d'être of the VPP.

### Headline result (April 2026 forward run)

| Metric | Value |
|---|---|
| Portfolio total revenue | **$626,788** |
| Portfolio average MAE | **$17.18 / MWh** (target < $22) |
| Worst-region MAE | $18.91 / MWh (NSW1) |
| Diversification gain | **+279%** vs solo-asset baseline |
| Acceptance criteria | ✅ ALL PASS |

---

## 🗂 Repo layout

```
vpp-aggregation-dispatch/
├── VPP_Aggregation_Dispatch.ipynb     # ★ main notebook — 12-step framework, end-to-end
├── app.py                             # Streamlit dashboard
├── requirements.txt                   # pip deps
├── environment.yml                    # conda env
├── Dockerfile                         # for Cloud Run / Docker Hub
├── DEPLOY.md                          # local / Streamlit Cloud / Docker
├── .github/workflows/ci.yml           # smoke-tests the notebook on every push
├── data/                              # NEMOSIS cache (gitignored except .gitkeep)
├── models/                            # pickled trained models (after first run)
├── outputs/                           # CSVs + dashboard PNGs (after first run)
└── README.md
```

---

## 🚀 Quick start

### Option A — pip / venv

```bash
git clone <this repo>
cd vpp-aggregation-dispatch
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab VPP_Aggregation_Dispatch.ipynb
# Run all cells → see results in outputs/
```

### Option B — conda

```bash
conda env create -f environment.yml
conda activate vpp-aggregation-dispatch
jupyter lab VPP_Aggregation_Dispatch.ipynb
```

### Option C — Streamlit dashboard

```bash
streamlit run app.py
# opens http://localhost:8501
```

### Option D — Docker

```bash
docker build -t vpp-engine .
docker run -p 8501:8501 vpp-engine
```

See [DEPLOY.md](DEPLOY.md) for cloud deployment.

---

## ⚙️ Configuration — top of notebook (Cell 2)

Everything operator-relevant lives in **one cell**. No code changes needed for routine use.

```python
# Time window
TARGET_YEAR    = 2026
TARGET_MONTH   = 4         # 1-12
HISTORY_YEARS  = 2         # how far back NEMOSIS is queried

# Portfolio (edit any field — assets are auto-validated)
VPP_PORTFOLIO = [
    dict(name='UtilBESS_VIC', region='VIC1', power_mw=100.0, energy_mwh=200.0, rte=0.90, kind='Utility BESS'),
    dict(name='ComBESS_SA',   region='SA1',  power_mw=20.0,  energy_mwh=40.0,  rte=0.88, kind='Commercial BESS'),
    dict(name='HomeAgg_NSW',  region='NSW1', power_mw=15.0,  energy_mwh=30.0,  rte=0.86, kind='Aggregated Home Batteries'),
    dict(name='IndBESS_QLD',  region='QLD1', power_mw=50.0,  energy_mwh=100.0, rte=0.89, kind='Industrial BESS'),
    dict(name='PumpedHy_TAS', region='TAS1', power_mw=30.0,  energy_mwh=240.0, rte=0.78, kind='Mini Pumped Hydro'),
]

# Modelling
RUN_HPO        = False     # True = Optuna 20-trial HPO per region (~10 min total)
USE_NEMOSIS    = True      # True = real AEMO data; False = synthetic
FOCUS_REGION   = 'VIC1'    # used for SHAP and the diagnostic plots
PLOT_WEEK      = 2         # which week of the target month to detail-plot
```

---

## 🧠 Methodology — Master ML/DL Framework (12 steps, 5 phases)

| Phase | Step | Coverage |
|---|---|---|
| **1. Data** | 1. Problem formulation | VPP aggregation thesis, success criteria, asset economics |
|  | 2. Data acquisition | NEMOSIS `dynamic_data_compiler` (auto-fallback to synthetic) |
|  | 3. EDA | Distributions, autocorrelation, regime detection, negative prices |
|  | 4. Validation strategy | 70/15/15 temporal split, LockedTestSet, expanding-window CV |
| **2. Features** | 5. Feature engineering | ~70 features per region: lags, rollings, EWMA, calendar, regimes, interactions |
|  | 6. Preprocessing pipeline | RobustScaler + SimpleImputer, fit train-only |
| **3. Baselines** | 7. Baselines | Naive-last, seasonal-naive (24h), rolling-mean, ridge |
| **4. Modeling** | 8. Model selection | XGBoost + LightGBM per region |
|  | 9. Tuning & ensembling | Optional Optuna HPO + inverse-MAE ensemble weighting |
|  | 10. Evaluation | Locked test (one-shot), SHAP, error-by-hour, spike recall |
| **5. Optimization** | 11. Forward forecast | Seasonal-anchor for monthly horizon (no compounding-error decay) |
|  | 11b. Joint dispatch | Multi-asset LP via CVXPY, ~3,600 vars, terminal-SoC penalty |
|  | 12. Dashboard & report | 6-panel cockpit, per-asset waterfall, weekly SoC traces, CSV exports |

### Model architecture — per region

```
       ┌─────────────────────┐    ┌─────────────────────┐
NEMOSIS│  raw 30-min prices  │    │ ~70 engineered      │
  +──→ │  + AEMO demand      │──→ │ features (lags,     │
synth  │  per NEM region     │    │ rolls, calendar)    │
       └─────────────────────┘    └──────────┬──────────┘
                                              │
                       ┌─────────────────┐   │   ┌─────────────────┐
                       │  XGBoost        │←──┴──→│  LightGBM       │
                       │  (val MAE: x_x) │       │  (val MAE: x_l) │
                       └────────┬────────┘       └────────┬────────┘
                                └───── ensemble ──────────┘
                                  w_x = 1/x_x / (1/x_x+1/x_l)
                                  w_l = 1 - w_x
                                          │
                                          ▼
                              ┌────────────────────┐
                              │ Forecast price     │
                              │ for target month   │
                              └────────┬───────────┘
                                       │
                  ┌────────────────────┴────────────────────┐
                  ▼                                         ▼
         ┌─────────────────┐                       ┌─────────────────┐
         │ Per-region price│                       │ Per-region price│
         │  (5 regions)    │ ── feed into joint ──→│  forecasts      │
         └─────────────────┘                       └────────┬────────┘
                                                            │
                                                            ▼
                                              ┌──────────────────────────┐
                                              │ Multi-asset LP (CVXPY)   │
                                              │ max Σ p·(d-c)Δt          │
                                              │ s.t. SoC dynamics, RTE,  │
                                              │      neg-price priority  │
                                              └────────────┬─────────────┘
                                                           │
                                                           ▼
                                              ┌──────────────────────────┐
                                              │ Optimal dispatch & CSVs  │
                                              │ per asset, per hour      │
                                              └──────────────────────────┘
```

### LP formulation (per asset $a$, per hour $t$)

$$\max \sum_{a} \sum_t p_{a,t}(d_{a,t} - c_{a,t}) \Delta t - \lambda \sum_a |s_{a,T} - s_{a,0}|$$

subject to
- $0 \le c_{a,t}, d_{a,t} \le P^{\max}_a$
- $s_{a,t+1} = s_{a,t} + \eta_a c_{a,t} \Delta t - \eta_a^{-1} d_{a,t} \Delta t$
- $E_a \cdot \text{soc-min} \le s_{a,t} \le E_a \cdot \text{soc-max}$
- $c_{a,t} \ge 0.85 P^{\max}_a$ when $p_{a,t} \le -\$50$/MWh (negative-price priority)

---

## 🔁 Re-use the engine — `quick_forecast()`

After running once, the trained per-region models live in `MODELS` and historical data in `DATA`. Re-run for any month in seconds:

```python
# Forecast July 2026, plot July 15
results = quick_forecast(2026, 7, plot_date='2026-07-15')

# Different day from the current run
plot_day_dispatch('2026-04-20')

# Subset of regions
quick_forecast(2026, 6, regions=['VIC1', 'SA1'])
```

---

## 📊 Outputs

After running the notebook, `outputs/` contains:

| File | Contents |
|---|---|
| `dispatch_<asset>.csv` | Hourly schedule per asset: forecast price, charge MW, discharge MW, net MW, SoC%, hourly revenue |
| `portfolio_summary.csv` | Per-asset revenue / cycles / $-per-MWh-of-capacity |
| `forecast_accuracy.csv` | Per-region MAE/RMSE/DA% with baseline comparison |
| `step3_eda.png` | EDA dashboard (9-panel) |
| `step10_diagnostics.png` | Locked-test diagnostics (4-panel) |
| `step10_shap.png` | SHAP feature importance for FOCUS_REGION |
| `step11_forecast.png` | Forecasted price for FOCUS_REGION |
| `step12_dashboard.png` | Operator cockpit (6-panel) |

---

## ⚠️ Known limitations & roadmap

- **No FCAS co-optimisation yet** — energy market only. Next: re-use the FCAS-bot trapezium constraint module.
- **No network constraints** — assumes infinite intra-region transmission.
- **Point forecast in LP** — a stochastic / scenario MILP would be more spike-robust.
- **Battery degradation cost** is reported (cycles) but not monetised in the objective.

---

## 🛠 Stack


XGBoost ≥ 2.0, LightGBM ≥ 4.1, Optuna, SHAP, CVXPY, NEMOSIS, Streamlit, Plotly, Matplotlib, scikit-learn.
 
---
#   M u l t i - A s s e t - V P P - A g g r e g a t i o n - W h o l e s a l e - M a r k e t - D i s p a t c h - E n g i n e 
 
 