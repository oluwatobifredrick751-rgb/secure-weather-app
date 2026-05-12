import streamlit as st
import pandas as pd
import re
import time

st.set_page_config(page_title="Monitor • Secure Weather App", page_icon="📊", layout="wide")

st.title("📊 Weather Sentinel Monitor")
st.markdown("### Real-time Logs & Activity Dashboard")

if st.button("🔄 Refresh Logs"):
    st.rerun()

st.caption(f"Last refreshed: {time.strftime('%Y-%m-%d %H:%M:%S')}")

LOG_FILE = "weather_app.log"

# Load logs
try:
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.readlines()[-1500:]
except FileNotFoundError:
    st.warning("No log file found yet. Make some weather requests first.")
    logs = []

# Parse logs
parsed_logs = []
for line in logs:
    line = line.strip()
    if not line:
        continue
    match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (\w+) \| (.*)', line)
    if match:
        parsed_logs.append({
            "timestamp": match.group(1),
            "level": match.group(2),
            "message": match.group(3)
        })

df = pd.DataFrame(parsed_logs)

# Metrics
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Requests", len([m for m in df.get('message', []) if "Weather Request" in str(m)]))
col2.metric("Errors", len(df[df['level'] == 'ERROR']) if not df.empty else 0)
col3.metric("Rate Limit Hits", len([m for m in df.get('message', []) if "Rate limit" in str(m)]))
col4.metric("Total Logs", len(df))

st.subheader("Recent Logs")
if not df.empty:
    st.dataframe(
        df.tail(100)[['timestamp', 'level', 'message']],
        use_container_width=True,
        hide_index=True
    )
    
    # Chart
    if len(df) > 5:
        st.bar_chart(df['level'].value_counts())
else:
    st.info("No logs yet. Go to the main page and fetch weather data.")

st.success("✅ Monitor Dashboard Ready")
