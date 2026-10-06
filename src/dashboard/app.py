import streamlit as st
import pandas as pd
from pyspark.sql import SparkSession
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Agri Anomaly Dashboard", layout="wide")

# Refresh every 5 seconds (5000 milliseconds)
count = st_autorefresh(interval=5000, limit=None, key="data_refresh")

@st.cache_resource
def get_spark():
    spark = SparkSession.builder \
        .appName("StreamlitDashboard") \
        .getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    return spark

@st.cache_data(ttl=5)
def load_data():
    spark = get_spark()
    try:
        df = spark.read.parquet("hdfs://namenode:9000/agri/streaming/anomaly_predictions")
        return df.toPandas()
    except Exception as e:
        return pd.DataFrame()

st.title("Real-Time Agri Market Anomaly Dashboard")

df = load_data()

if df.empty:
    st.warning("No data found or HDFS is unavailable.")
else:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    st.sidebar.header("Filters")
    selected_state = st.sidebar.multiselect("State", options=df['state'].unique())
    selected_district = st.sidebar.multiselect("District", options=df['district'].unique())
    selected_commodity = st.sidebar.multiselect("Commodity", options=df['commodity'].unique())
    selected_market = st.sidebar.multiselect("Market", options=df['market'].unique())
    
    filtered_df = df.copy()
    if selected_state:
        filtered_df = filtered_df[filtered_df['state'].isin(selected_state)]
    if selected_district:
        filtered_df = filtered_df[filtered_df['district'].isin(selected_district)]
    if selected_commodity:
        filtered_df = filtered_df[filtered_df['commodity'].isin(selected_commodity)]
    if selected_market:
        filtered_df = filtered_df[filtered_df['market'].isin(selected_market)]

    st.subheader("Key Metrics")
    total_preds = len(filtered_df)
    total_anomalies = filtered_df['anomaly_prediction'].sum()
    anomaly_pct = (total_anomalies / total_preds * 100) if total_preds > 0 else 0
    latest_ts = filtered_df['timestamp'].max() if not filtered_df.empty else "N/A"
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Predictions", total_preds)
    col2.metric("Total Anomalies", int(total_anomalies))
    col3.metric("Anomaly %", f"{anomaly_pct:.2f}%")
    col4.metric("Latest Prediction", str(latest_ts).split(".")[0])
    
    st.divider()

    col_charts1, col_charts2 = st.columns(2)
    
    with col_charts1:
        st.subheader("Prediction Distribution")
        dist = filtered_df['anomaly_prediction'].value_counts().rename(index={0.0: "Normal", 1.0: "Anomaly"})
        st.bar_chart(dist)
    
    with col_charts2:
        st.subheader("Recent Anomaly Probabilities")
        chart_df = filtered_df.sort_values('timestamp').tail(50).set_index('timestamp')
        if not chart_df.empty:
            st.line_chart(data=chart_df['anomaly_probability'])
            
    col_charts3, col_charts4 = st.columns(2)
    
    with col_charts3:
        st.subheader("Top Anomalous Commodities")
        anomalies_only = filtered_df[filtered_df['anomaly_prediction'] == 1.0]
        if not anomalies_only.empty:
            comm_counts = anomalies_only['commodity'].value_counts().head(10)
            st.bar_chart(comm_counts)
        else:
            st.info("No anomalies to display.")
            
    with col_charts4:
        st.subheader("Top Anomalous Markets")
        if not anomalies_only.empty:
            mkt_counts = anomalies_only['market'].value_counts().head(10)
            st.bar_chart(mkt_counts)
        else:
            st.info("No anomalies to display.")
            
    st.divider()
    
    st.subheader("Recent Alerts")
    alerts_df = filtered_df.sort_values('timestamp', ascending=False)
    
    def highlight_anomalies(val):
        color = '#ffcccc' if val == 1.0 else ''
        return f'background-color: {color}'
    
    disp_cols = ['timestamp', 'state', 'district', 'market', 'commodity', 'variety', 'modal_price', 'anomaly_probability', 'anomaly_prediction']
    st.dataframe(alerts_df[disp_cols].head(50).style.applymap(highlight_anomalies, subset=['anomaly_prediction']))
