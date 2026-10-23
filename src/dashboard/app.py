import os
import sys

# Ensure Java 21 is used instead of system default Java 26 (Spark 4.2.0 compatibility)
java21_path = "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
if os.path.exists(java21_path):
    os.environ["JAVA_HOME"] = java21_path
    os.environ["PATH"] = f"{java21_path}/bin:" + os.environ.get("PATH", "")

os.environ["SPARK_LOCAL_IP"] = "127.0.0.1"

java_opts = (
    "--add-opens=java.base/java.lang=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.invoke=ALL-UNNAMED "
    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED "
    "--add-opens=java.base/java.io=ALL-UNNAMED "
    "--add-opens=java.base/java.net=ALL-UNNAMED "
    "--add-opens=java.base/java.nio=ALL-UNNAMED "
    "--add-opens=java.base/java.util=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED "
    "--add-opens=java.base/java.util.concurrent.atomic=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED "
    "--add-opens=java.base/sun.nio.cs=ALL-UNNAMED "
    "--add-opens=java.base/sun.security.action=ALL-UNNAMED "
    "--add-opens=java.base/sun.util.calendar=ALL-UNNAMED "
    "--add-opens=java.security.jgss/sun.security.krb5=ALL-UNNAMED"
)
os.environ["PYSPARK_SUBMIT_ARGS"] = f'--driver-java-options "{java_opts}" pyspark-shell'

import streamlit as st
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Large-Scale Agricultural Market Data & Real-Time Analysis", layout="wide", initial_sidebar_state="expanded")

# Inject Premium Dark Mode Glassmorphism CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at 10% 20%, rgb(20, 20, 30) 0%, rgb(10, 10, 15) 90%); color: #e0e0e0; }
    h1 { background: -webkit-linear-gradient(45deg, #42a5f5, #00e676); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; letter-spacing: -0.5px; }
    h2, h3 { color: #b0bec5; font-weight: 600; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; color: #00e676; }
    div[data-testid="metric-container"] { background: rgba(255, 255, 255, 0.03); border-radius: 12px; padding: 15px; border: 1px solid rgba(255, 255, 255, 0.1); box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); backdrop-filter: blur(10px); transition: transform 0.2s ease-in-out; }
    div[data-testid="metric-container"]:hover { transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0, 230, 118, 0.2); }
    .stTabs [data-baseweb="tab-list"] { gap: 20px; }
    .stTabs [data-baseweb="tab"] { background-color: transparent !important; border-radius: 4px 4px 0px 0px; color: #90a4ae !important; font-weight: 600; padding: 10px 20px; }
    .stTabs [aria-selected="true"] { color: #42a5f5 !important; border-bottom: 2px solid #42a5f5; }
    hr { border-top: 1px solid rgba(255,255,255,0.1); }
</style>
""", unsafe_allow_html=True)

count = st_autorefresh(interval=5000, limit=None, key="data_refresh")

@st.cache_resource
def get_spark():
    spark = SparkSession.builder.appName("StreamlitDashboard") \
        .master("local[2]") \
        .config("spark.driver.host", "127.0.0.1") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "false") \
        .config("spark.driver.extraJavaOptions", java_opts) \
        .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark

@st.cache_data(ttl=60)
def load_analytics(path):
    spark = get_spark()
    try:
        return spark.read.parquet(f"hdfs://namenode:9000/agri-market/analytics/{path}").toPandas()
    except Exception as e:
        import streamlit as st
        st.error(f"Failed to load {path}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=5)
def load_streaming_data():
    spark = get_spark()
    try:
        df = spark.read.parquet("hdfs://namenode:9000/agri/streaming/real_anomaly_predictions")
        return df.toPandas()
    except Exception as e:
        import streamlit as st
        st.error(f"Failed to load streaming data: {str(e)}")
        return pd.DataFrame()

st.title("Large-Scale Agricultural Market Data & Real-Time Analysis")
st.markdown("**Data Source: AGMARKNET daily prices (archive) + official data.gov.in back-fill**")
# Corrected 2026-10-23: every figure shown below comes from docs/VERIFIED_METRICS.md
# (section given in each comment); the original v1 figures are preserved in Git commit 3926155.
st.caption("Figures from docs/VERIFIED_METRICS.md (corrected 2026-10-23). "
           "Earlier v1 anomaly-classifier metrics were withdrawn; see docs/AUDIT_PRIOR_RESULTS.md.")

# docs/VERIFIED_METRICS.md section 2: experiment fc_main_v3, test 2025-01-01 .. 2026-04-20
FORECAST_TEST = pd.DataFrame(
    [
        ("next report", "GBT (absolute loss)", 189.0, 183.5, 0.971, "78.6%", "1.3e-22", "58.5%"),
        ("3 days", "GBT (absolute loss)", 242.6, 231.1, 0.953, "79.4%", "3.6e-47", "68.8%"),
        ("7 days", "Random forest", 308.8, 289.7, 0.938, "80.0%", "4.4e-39", "75.0%"),
        ("14 days", "Random forest", 397.0, 366.4, 0.923, "80.5%", "8.7e-29", "76.4%"),
    ],
    columns=["Horizon", "Selected model", "Persistence MAE (Rs/q)", "Model MAE (Rs/q)",
             "Rel. MAE vs persistence", "80% interval coverage", "Diebold-Mariano p", "Series better"],
)
# docs/VERIFIED_METRICS.md section 2: frozen models, no refitting
FORECAST_FROZEN = pd.DataFrame(
    [
        ("Same test period, complete official data", 0.972, 0.954, 0.943, 0.925, "79.2-80.3%"),
        ("Prospective 2026-04-22 -> 2026-10-22", 0.963, 0.955, 0.958, 0.952, "76.9-80.1%"),
    ],
    columns=["Evaluation (rel. MAE)", "next", "3 d", "7 d", "14 d", "80% coverage"],
)
# docs/VERIFIED_METRICS.md section 3: injected corruptions, run results/anomaly/20261022T175225Z
ANOMALY_INJECTED = pd.DataFrame(
    [
        ("Production rule (trailing robust z)", 0.704, 0.313, 0.846, 0.019),
        ("Previous-report change", 0.671, 0.160, 0.960, 0.051),
        ("Legacy commodity IQR (v1 rule)", 0.352, 0.208, 0.371, 0.014),
    ],
    columns=["Detector", "PR-AUC (any corruption)", "Precision", "Recall", "FPR"],
)

tab1, tab2 = st.tabs(["HISTORICAL MARKET ANALYSIS", "REAL-TIME MARKET ANALYSIS"])

with tab1:
    st.subheader("Data & Architecture Provenance")
    
    col1, col2, col3, col4 = st.columns(4)
    # section 1
    col1.metric("ARCHIVE SILVER ROWS", "75.6M")
    col1.caption("Raw archive: 75,984,017 rows\nSilver v2 (archive + official): 82,114,083 rows")
    
    col2.metric("OFFICIAL BACK-FILL", "7.72M")
    col2.caption("data.gov.in, 2025-10-01 to 2026-10-22, 387 days\nForecast panel: 36 commodities, 11,845 series")
    
    # section 5
    col3.metric("HDFS CLUSTER (Storage)", "1 NN + 3 DN")
    col3.caption("Replication 3, 692 MB silver, HEALTHY\nReadable with 1 DataNode down")
    
    col4.metric("STREAMING (Kafka -> Spark)", "20,000 / 20,000")
    col4.caption("Replay: 21,524 messages, 1,317 duplicates removed, 207 quarantined, 0 missing\n"
                 "Parity 0 mismatches; producer->sink p50 1.69 s")
    
    st.divider()
    st.subheader("Price Forecasting (Model Performance)")
    st.info("Relative MAE = model MAE / persistence (last price) MAE on identical rows; lower is better, "
            "< 1 beats persistence. Train origins 2016-2023, validation 2024, test 2025-01-01 to 2026-04-20 "
            "(archive data), scored once. Persistence is a hard baseline: 17-34% of target changes are exactly zero.")
    
    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Rel. MAE, next report", "0.971")
    mcol2.metric("Rel. MAE, 3 days", "0.953")
    mcol3.metric("Rel. MAE, 7 days", "0.938")
    mcol4.metric("Rel. MAE, 14 days", "0.923")
    st.dataframe(FORECAST_TEST, use_container_width=True, hide_index=True)
    st.markdown("##### Frozen models on new data (no refitting)")
    st.dataframe(FORECAST_FROZEN, use_container_width=True, hide_index=True)
    st.caption("Decision cards, test period, 7 days: WATCH on 98.5% of report-days; HOLD on 0.5% "
               "(hit rate 80.0%); SELL on 1.0% (hit rate 67.8%). Hit rates on published prices, not farm profits.")
    
    st.divider()
    st.subheader("Anomaly Flags (Injected Corruptions Only)")
    st.dataframe(ANOMALY_INJECTED, use_container_width=True, hide_index=True)
    st.warning("There are no labels for real anomalies, so no accuracy figure for real anomalies exists.")
    
    st.divider()
    st.subheader("Price Analysis (Real Data Aggregations)")
    
    df_comm = load_analytics("commodity_statistics")
    df_state = load_analytics("state_statistics")
    df_price = load_analytics("price_statistics")
    
    st.sidebar.header("Historical Filters")
    sel_comm = st.sidebar.multiselect("Filter Commodities", options=df_comm['commodity'].dropna().unique() if not df_comm.empty else [])
    sel_state = st.sidebar.multiselect("Filter States", options=df_state['state'].dropna().unique() if not df_state.empty else [])
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Top States by Record Count")
        if not df_state.empty:
            filt_state = df_state[df_state['state'].isin(sel_state)] if sel_state else df_state
            st.bar_chart(filt_state.set_index('state').sort_values('record_count', ascending=False).head(10))
    with c2:
        st.markdown("##### Top Commodities by Record Count")
        if not df_comm.empty:
            filt_comm = df_comm[df_comm['commodity'].isin(sel_comm)] if sel_comm else df_comm
            st.bar_chart(filt_comm.set_index('commodity').sort_values('record_count', ascending=False).head(10))
            
    st.markdown("##### Commodity Price Statistics")
    if not df_price.empty:
        filt_price = df_price[df_price['commodity'].isin(sel_comm)] if sel_comm else df_price
        st.dataframe(filt_price.head(50), use_container_width=True)


with tab2:
    st.subheader("REAL-DATA STREAM REPLAY (legacy v1 output)")
    st.warning("This tab reads the legacy v1 streaming output (`/agri/streaming/real_anomaly_predictions`). "
               "Its anomaly probabilities come from the withdrawn v1 classifier, so the advisory labels below are "
               "illustrative only and are not evaluated. The current pipeline (PriceEventStream) writes alerts "
               "scored by the trailing robust-z rule; see docs/ARCHITECTURE.md.")
    stream_df = load_streaming_data()
    
    if stream_df.empty:
        st.warning("No real-time data found on HDFS.")
    else:
        time_col = 'timestamp' if 'timestamp' in stream_df.columns else 'arrival_date'
        stream_df[time_col] = pd.to_datetime(stream_df[time_col])
        
        st.sidebar.header("Live Filters")
        l_state = st.sidebar.multiselect("State (Live)", options=stream_df['state'].unique())
        l_comm = st.sidebar.multiselect("Commodity (Live)", options=stream_df['commodity'].unique())
        
        f_df = stream_df.copy()
        if l_state: f_df = f_df[f_df['state'].isin(l_state)]
        if l_comm: f_df = f_df[f_df['commodity'].isin(l_comm)]
        
        total_preds = len(f_df)
        total_anomalies = f_df['anomaly_prediction'].sum()
        pct = (total_anomalies / total_preds * 100) if total_preds > 0 else 0
        latest_ts = f_df[time_col].max() if not f_df.empty else "N/A"
        latest_prob = f_df.sort_values(time_col).iloc[-1]['anomaly_probability'] if not f_df.empty and 'anomaly_probability' in f_df.columns else "N/A"
        
        scol1, scol2, scol3, scol4, scol5 = st.columns(5)
        scol1.metric("Real Events Processed", total_preds)
        scol2.metric("Real Anomalies Detected", int(total_anomalies))
        scol3.metric("Anomaly %", f"{pct:.2f}%")
        scol4.metric("Latest Real Event", str(latest_ts).split(".")[0])
        scol5.metric("Latest Probability", f"{latest_prob:.2f}" if isinstance(latest_prob, float) else latest_prob)
        
        # Farmer Decision Support Advisory Classification
        def classify_advisory(row):
            pred = row.get('anomaly_prediction', 0.0)
            prob = row.get('anomaly_probability', 0.0)
            if pred == 1.0 or prob >= 0.65:
                return "🟢 SELL (Harvest Peak)"
            elif prob >= 0.38:
                return "🟡 HOLD (Panic Reversal)"
            elif prob >= 0.18:
                return "🔵 WATCH (Volatility)"
            else:
                return "🟣 BUY (Procurement)"

        f_df['Advisory'] = f_df.apply(classify_advisory, axis=1)

        sell_cnt = (f_df['Advisory'].str.startswith("🟢")).sum()
        hold_cnt = (f_df['Advisory'].str.startswith("🟡")).sum()
        watch_cnt = (f_df['Advisory'].str.startswith("🔵")).sum()
        buy_cnt = (f_df['Advisory'].str.startswith("🟣")).sum()

        st.markdown("#### 🌾 Farmer Advisories from the legacy v1 stream (illustrative, not evaluated)")
        acol1, acol2, acol3, acol4 = st.columns(4)
        acol1.metric("🟢 SELL Advisories", int(sell_cnt), help="Sell before seasonal post-spike harvest glut collapses prices")
        acol2.metric("🟡 HOLD Advisories", int(hold_cnt), help="Hold inventory during temporary panic drops awaiting mean reversion")
        acol3.metric("🔵 WATCH Advisories", int(watch_cnt), help="Spread volatility detected; monitor neighboring district mandis")
        acol4.metric("🟣 BUY Advisories", int(buy_cnt), help="Stable low price window; optimal for wholesale and food processors")

        st.divider()
        lc1, lc2 = st.columns(2)
        with lc1:
            st.markdown("##### Top Anomalous Commodities")
            anoms = f_df[f_df['anomaly_prediction'] == 1.0]
            if not anoms.empty:
                st.bar_chart(anoms['commodity'].value_counts().head(10))
            else:
                st.info("No anomalies")
        with lc2:
            st.markdown("##### Top Anomalous Markets")
            if not anoms.empty:
                st.bar_chart(anoms['market'].value_counts().head(10))
            else:
                st.info("No anomalies")
                
        st.markdown("##### Recent Farmer Advisories & Real-Time Alert Feed")
        def hl_advisory(val):
            if isinstance(val, str):
                if val.startswith("🟢"): return 'background-color: rgba(0, 230, 118, 0.2); font-weight: bold;'
                if val.startswith("🟡"): return 'background-color: rgba(255, 214, 0, 0.2); font-weight: bold;'
                if val.startswith("🔵"): return 'background-color: rgba(41, 121, 255, 0.2); font-weight: bold;'
                if val.startswith("🟣"): return 'background-color: rgba(170, 0, 255, 0.2); font-weight: bold;'
            return ''

        cols = [c for c in ['Advisory', time_col, 'state', 'district', 'market', 'commodity', 'variety', 'modal_price', 'anomaly_probability', 'anomaly_prediction'] if c in f_df.columns]
        st.dataframe(
            f_df[cols].sort_values(time_col, ascending=False).head(50).style.applymap(hl_advisory, subset=['Advisory']),
            use_container_width=True
        )
