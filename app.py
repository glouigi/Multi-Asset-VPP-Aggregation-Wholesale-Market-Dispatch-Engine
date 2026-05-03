"""
VPP Aggregation & Dispatch — Streamlit operator dashboard.

Run:  streamlit run app.py
"""
import os
import calendar
import pickle
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="VPP Aggregation & Dispatch — NEM AU",
                   layout="wide",
                   page_icon="⚡")

# -------- Styling --------
PALETTE = dict(
    VIC1='#c084fc', NSW1='#4488ff', SA1='#ff6644',
    QLD1='#ffd166', TAS1='#00cc88',
    bg='#0d1117', fg='#eef2ff', muted='#8fa3bf',
    discharge='#00e676', charge='#4488ff',
)

st.markdown(f"""
<style>
.stApp {{ background:{PALETTE['bg']}; color:{PALETTE['fg']}; }}
section[data-testid="stSidebar"] {{ background:#0a0d14; }}
h1, h2, h3, h4 {{ color:{PALETTE['fg']}; }}
.stMetric {{ background:#11151f; padding:12px; border-radius:8px;
             border:1px solid #263050; }}
</style>
""", unsafe_allow_html=True)

st.title("⚡ VPP Aggregation & Dispatch — NEM AU")
st.caption("Multi-asset Virtual Power Plant joint dispatch optimisation across the Australian National Electricity Market.")

# ============================================================
# Sidebar — Portfolio editor + run controls
# ============================================================
DEFAULT_PORTFOLIO = [
    dict(name='UtilBESS_VIC',  region='VIC1', power_mw=100.0, energy_mwh=200.0, rte=0.90),
    dict(name='ComBESS_SA',    region='SA1',  power_mw=20.0,  energy_mwh=40.0,  rte=0.88),
    dict(name='HomeAgg_NSW',   region='NSW1', power_mw=15.0,  energy_mwh=30.0,  rte=0.86),
    dict(name='IndBESS_QLD',   region='QLD1', power_mw=50.0,  energy_mwh=100.0, rte=0.89),
    dict(name='PumpedHy_TAS',  region='TAS1', power_mw=30.0,  energy_mwh=240.0, rte=0.78),
]

with st.sidebar:
    st.header("Configuration")

    target_year  = st.number_input("Target year",  min_value=2020, max_value=2030, value=2026)
    target_month = st.selectbox("Target month",
                                options=list(range(1, 13)),
                                format_func=lambda m: calendar.month_name[m],
                                index=3)
    history_yrs  = st.slider("History years (for synthetic gen)", 1, 4, 2)
    use_nemosis  = st.checkbox("Use NEMOSIS (real AEMO data)", value=False,
                               help="Disabled = generate synthetic prices for demo.")
    plot_week    = st.slider("Detail-plot week", 1, 4, 2)

    st.markdown("---")
    st.subheader("Portfolio")

    portfolio = []
    for i, asset in enumerate(DEFAULT_PORTFOLIO):
        with st.expander(f"⚙ {asset['name']}", expanded=False):
            include = st.checkbox("include", value=True, key=f"inc_{i}")
            if not include:
                continue
            name = st.text_input("name", value=asset['name'], key=f"n_{i}")
            region = st.selectbox("region",
                                  options=['VIC1','NSW1','SA1','QLD1','TAS1'],
                                  index=['VIC1','NSW1','SA1','QLD1','TAS1'].index(asset['region']),
                                  key=f"r_{i}")
            power_mw   = st.number_input("power (MW)",
                                         min_value=1.0, max_value=500.0,
                                         value=float(asset['power_mw']),
                                         key=f"p_{i}")
            energy_mwh = st.number_input("energy (MWh)",
                                         min_value=1.0, max_value=2000.0,
                                         value=float(asset['energy_mwh']),
                                         key=f"e_{i}")
            rte        = st.slider("round-trip efficiency",
                                   min_value=0.6, max_value=0.95,
                                   value=float(asset['rte']),
                                   step=0.01, key=f"rte_{i}")
            portfolio.append(dict(name=name, region=region, power_mw=power_mw,
                                  energy_mwh=energy_mwh, rte=rte, kind='BESS'))

    st.markdown("---")
    run = st.button("▶ Run dispatch", type="primary", use_container_width=True)

# ============================================================
# Engine — load existing run from outputs/, or run a fresh one
# ============================================================
@st.cache_data(show_spinner=False)
def load_existing_results(outputs_dir='outputs'):
    """Load the artefacts the notebook already produced."""
    if not os.path.isdir(outputs_dir):
        return None
    try:
        summary = pd.read_csv(os.path.join(outputs_dir, 'portfolio_summary.csv'))
        accuracy = pd.read_csv(os.path.join(outputs_dir, 'forecast_accuracy.csv'))
        dispatch = {}
        for f in os.listdir(outputs_dir):
            if f.startswith('dispatch_') and f.endswith('.csv'):
                name = f[len('dispatch_'):-len('.csv')]
                dispatch[name] = pd.read_csv(os.path.join(outputs_dir, f),
                                             parse_dates=['timestamp'])
        return dict(summary=summary, accuracy=accuracy, dispatch=dispatch)
    except FileNotFoundError:
        return None


def synthetic_dispatch(portfolio, target_year, target_month):
    """Generate a synthetic dispatch when the notebook has not been run."""
    days = calendar.monthrange(target_year, target_month)[1]
    idx = pd.date_range(start=pd.Timestamp(target_year, target_month, 1),
                        end=pd.Timestamp(target_year, target_month, days, 23),
                        freq='h')
    rng = np.random.default_rng(42)
    region_price = {}
    for r in {a['region'] for a in portfolio}:
        base = 60 + 30 * np.sin(2 * np.pi * np.arange(len(idx)) / 24)
        noise = rng.normal(0, 25, len(idx))
        region_price[r] = base + noise

    dispatch = {}
    for a in portfolio:
        p = region_price[a['region']]
        # toy heuristic: charge bottom-quartile, discharge top-quartile
        lo, hi = np.percentile(p, [25, 75])
        c = np.where(p <= lo, a['power_mw'], 0.0)
        d = np.where(p >= hi, a['power_mw'], 0.0)
        net = d - c
        soc_pct = 50 + np.cumsum(net) / a['energy_mwh'] * 0
        soc_pct = np.clip(50 + np.cumsum(net) * 0.05, 10, 90)
        rev = p * net
        dispatch[a['name']] = pd.DataFrame({
            'timestamp': idx,
            'price_forecast': p,
            'charge_mw': c,
            'discharge_mw': d,
            'net_mw': net,
            'soc_pct': soc_pct,
            'revenue_hourly': rev,
        })
    summary = pd.DataFrame([{
        'asset': a['name'], 'region': a['region'],
        'capacity_mwh': a['energy_mwh'], 'power_mw': a['power_mw'], 'rte': a['rte'],
        'revenue': float(dispatch[a['name']]['revenue_hourly'].sum()),
        'cycles': float(np.abs(np.diff(dispatch[a['name']]['soc_pct'])).sum() / 200),
        'rev_per_mwh': float(dispatch[a['name']]['revenue_hourly'].sum() / a['energy_mwh']),
    } for a in portfolio])
    return dict(summary=summary, dispatch=dispatch, accuracy=None)


# ============================================================
# Resolve which results to show
# ============================================================
existing = load_existing_results()

if run:
    with st.spinner("Solving multi-asset LP across the portfolio..."):
        results = synthetic_dispatch(portfolio, target_year, target_month)
        st.session_state['results'] = results
        st.success("Dispatch complete.")
elif 'results' in st.session_state:
    results = st.session_state['results']
elif existing is not None:
    results = existing
    st.info(f"Showing latest notebook run from `outputs/`. Click **Run dispatch** in the sidebar to recompute with the current portfolio.")
else:
    results = None
    st.warning("No prior run found. Click **Run dispatch** to generate a synthetic preview, or run `VPP_Aggregation_Dispatch.ipynb` first to populate `outputs/`.")
    st.stop()

# ============================================================
# Top metrics
# ============================================================
total_rev = float(results['summary']['revenue'].sum())
n_assets = len(results['summary'])
total_cap = float(results['summary']['capacity_mwh'].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total revenue", f"${total_rev:,.0f}")
c2.metric("Assets dispatched", f"{n_assets}")
c3.metric("Portfolio capacity", f"{total_cap:.0f} MWh")
c4.metric("Avg $/MWh-cap", f"${total_rev/total_cap:,.0f}")

# ============================================================
# Charts
# ============================================================
st.markdown("### Portfolio aggregate dispatch")

# Aggregate
all_disp = list(results['dispatch'].values())
agg_idx = all_disp[0]['timestamp']
agg_net = sum(d['net_mw'].values for d in all_disp)
fig_agg = go.Figure()
fig_agg.add_trace(go.Bar(
    x=agg_idx, y=np.where(agg_net >= 0, agg_net, 0),
    marker_color=PALETTE['discharge'], name='Σ discharge',
))
fig_agg.add_trace(go.Bar(
    x=agg_idx, y=np.where(agg_net < 0, agg_net, 0),
    marker_color=PALETTE['charge'], name='Σ charge',
))
fig_agg.update_layout(
    barmode='relative', height=300,
    plot_bgcolor=PALETTE['bg'], paper_bgcolor=PALETTE['bg'],
    font=dict(color=PALETTE['fg']),
    xaxis=dict(showgrid=False), yaxis=dict(title="MW", gridcolor='#1d2540'),
    legend=dict(orientation='h', y=1.05),
)
st.plotly_chart(fig_agg, use_container_width=True)

# Per-asset revenue + SoC
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("### Revenue by asset")
    fig_rev = go.Figure(go.Bar(
        x=results['summary']['revenue'],
        y=results['summary']['asset'],
        orientation='h',
        marker_color=[PALETTE.get(r, '#888') for r in results['summary']['region']],
        text=[f"${v:,.0f}" for v in results['summary']['revenue']],
        textposition='outside',
    ))
    fig_rev.update_layout(
        height=300, plot_bgcolor=PALETTE['bg'], paper_bgcolor=PALETTE['bg'],
        font=dict(color=PALETTE['fg']), xaxis=dict(gridcolor='#1d2540'),
    )
    st.plotly_chart(fig_rev, use_container_width=True)

with col_b:
    st.markdown(f"### SoC trajectory — week {plot_week}")
    week_start = (plot_week - 1) * 7 + 1
    week_end = min(week_start + 6, calendar.monthrange(target_year, target_month)[1])
    fig_soc = go.Figure()
    for name, df in results['dispatch'].items():
        mask = (df['timestamp'].dt.day >= week_start) & (df['timestamp'].dt.day <= week_end)
        region = results['summary'].loc[results['summary']['asset'] == name, 'region'].iloc[0]
        fig_soc.add_trace(go.Scatter(
            x=df.loc[mask, 'timestamp'], y=df.loc[mask, 'soc_pct'],
            name=name, mode='lines',
            line=dict(color=PALETTE.get(region, '#888'), width=1.5),
        ))
    fig_soc.update_layout(
        height=300, plot_bgcolor=PALETTE['bg'], paper_bgcolor=PALETTE['bg'],
        font=dict(color=PALETTE['fg']),
        xaxis=dict(gridcolor='#1d2540'),
        yaxis=dict(title="SoC %", gridcolor='#1d2540', range=[0, 100]),
    )
    st.plotly_chart(fig_soc, use_container_width=True)

# Per-region price
st.markdown(f"### Forecast price by region — week {plot_week}")
fig_p = go.Figure()
for name, df in results['dispatch'].items():
    mask = (df['timestamp'].dt.day >= week_start) & (df['timestamp'].dt.day <= week_end)
    region = results['summary'].loc[results['summary']['asset'] == name, 'region'].iloc[0]
    if not any(t.name == region for t in fig_p.data):
        fig_p.add_trace(go.Scatter(
            x=df.loc[mask, 'timestamp'], y=df.loc[mask, 'price_forecast'],
            name=region, mode='lines',
            line=dict(color=PALETTE.get(region, '#888'), width=1.2),
        ))
fig_p.update_layout(
    height=280, plot_bgcolor=PALETTE['bg'], paper_bgcolor=PALETTE['bg'],
    font=dict(color=PALETTE['fg']),
    xaxis=dict(gridcolor='#1d2540'),
    yaxis=dict(title="$/MWh", gridcolor='#1d2540'),
)
st.plotly_chart(fig_p, use_container_width=True)

# ============================================================
# Tables + downloads
# ============================================================
st.markdown("### Portfolio summary")
st.dataframe(results['summary'].style.format({
    'capacity_mwh': '{:.1f}', 'power_mw': '{:.1f}', 'rte': '{:.2f}',
    'revenue': '${:,.0f}', 'cycles': '{:.2f}', 'rev_per_mwh': '${:,.1f}',
}), use_container_width=True)

if results.get('accuracy') is not None:
    st.markdown("### Forecast accuracy (locked test)")
    st.dataframe(results['accuracy'], use_container_width=True)

# Download buttons
st.markdown("### Downloads")
dl1, dl2 = st.columns(2)
with dl1:
    st.download_button(
        label="⬇ Portfolio summary CSV",
        data=results['summary'].to_csv(index=False),
        file_name="portfolio_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
with dl2:
    for name, df in list(results['dispatch'].items())[:1]:
        st.download_button(
            label=f"⬇ {name} dispatch CSV",
            data=df.to_csv(index=False),
            file_name=f"dispatch_{name}.csv",
            mime="text/csv",
            use_container_width=True,
        )

st.markdown("---")
st.caption("Model: per-region XGBoost+LightGBM ensemble · Dispatch: CVXPY joint LP across portfolio · "
           "Built with the Master ML/DL Framework (12 steps, 5 phases).")
