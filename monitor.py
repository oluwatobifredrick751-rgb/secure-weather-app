import streamlit as st
import pandas as pd
import re
import time
from datetime import datetime

st.set_page_config(page_title="Monitor • Secure Weather App", page_icon="📊", layout="wide")

st.title("📊 Weather Sentinel Monitor")
st.markdown("### Real-time Logs & System Activity")

# Auto refresh
if st.button("🔄 Refresh Now"):
    st.rerun()

st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")

LOG_FILE = "weather_app.log"

# Load logs
try:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.readlines()[-1000:]  # Last 1000 lines
except FileNotFoundError:
    st.error("Log file not found. Make some requests first.")
    logs = []

# Parse logs
parsed = []
for line in logs:
    line = line.strip()
    if not line:
        continue
    # Match our log format
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (\w+) \| (.*)', line)
    if match:
        parsed.append({
            "timestamp": match.group(1),
            "level": match.group(2),
            "message": match.group(3)
        })

df = pd.DataFrame(parsed)

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Requests", len([m for m in df.get('message', []) if "Weather Request" in str(m)]))
col2.metric("Errors", len(df[df['level'] == 'ERROR']) if not df.empty else 0)
col3.metric("Rate Limits", len([m for m in df.get('message', []) if "Rate limit" in str(m)]))
col4.metric("Total Logs", len(df))

st.subheader("Recent Activity")
if not df.empty:
    st.dataframe(
        df.tail(100)[['timestamp', 'level', 'message']],
        use_container_width=True,
        hide_index=True
    )
    
    # Level distribution
    if len(df) > 5:
        st.bar_chart(df['level'].value_counts())
else:
    st.info("No logs yet. Go to the main dashboard and fetch weather data.")

st.success("✅ Monitor is Ready - CloudWatch integration coming in Phase 3")
