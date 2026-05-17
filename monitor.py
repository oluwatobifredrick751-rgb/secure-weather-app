import re
import time
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LOG_FILE = Path("logs") / "weather_app.log"
MAX_LOG_LINES = 1200

st.set_page_config(
    page_title="Monitor • Weather Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("📊 Weather Monitor")
st.markdown("Live diagnostics for request activity, errors, rate limiting, and log trends.")

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Controls")
    refresh_now = st.button("Refresh now")
    auto_refresh = st.checkbox("Auto refresh every 30 seconds", value=False)
    st.markdown("---")
    st.markdown("**Log file**")
    st.code(str(LOG_FILE), language="text")
    st.markdown("---")
    st.caption("Logs are read from the weather dashboard's runtime log file.")

if refresh_now:
    st.experimental_rerun()

if auto_refresh:
    try:
        from streamlit import st_autorefresh

        st_autorefresh(interval=30_000, key="monitor_autorefresh")
    except Exception:
        st.warning("Auto-refresh is not available in this Streamlit version.")

st.caption(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')} UTC")

# ---------------------------------------------------------------------------
# Read and parse logs
# ---------------------------------------------------------------------------
log_pattern = re.compile(r"(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (?P<level>\w+) \| (?P<message>.*)")
rows = []

try:
    log_text = LOG_FILE.read_text(encoding="utf-8")
    log_lines = log_text.strip().splitlines()[-MAX_LOG_LINES:]

    for raw_line in log_lines:
        line = raw_line.strip()
        if not line:
            continue

        match = log_pattern.match(line)
        if match:
            rows.append(match.groupdict())
        else:
            rows.append({
                "timestamp": None,
                "level": "INFO",
                "message": line,
            })

except FileNotFoundError:
    st.warning("⚠️ Log file not found. Generate traffic from the weather dashboard to begin monitoring.")
except Exception as exc:
    st.error(f"Unable to read log file: {exc}")

# ---------------------------------------------------------------------------
# Data formatting
# ---------------------------------------------------------------------------
if rows:
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df.sort_values(by="timestamp", ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)
else:
    df = pd.DataFrame(columns=["timestamp", "level", "message"])

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
request_count = int(df["message"].str.contains("request", case=False, na=False).sum())
error_count = int((df["level"].str.upper() == "ERROR").sum())
rate_limit_count = int(df["message"].str.contains("rate limit", case=False, na=False).sum())
success_count = int(df["message"].str.contains("success|fetched|completed|ok", case=False, na=False).sum())

metric_cols = st.columns(4)
metric_cols[0].metric("Total Requests", request_count)
metric_cols[1].metric("Errors", error_count)
metric_cols[2].metric("Rate Limit Hits", rate_limit_count)
metric_cols[3].metric("Successful Fetches", success_count)

# ---------------------------------------------------------------------------
# Charts and tables
# ---------------------------------------------------------------------------
with st.container():
    st.subheader("Log Level Distribution")
    if not df.empty:
        level_counts = df["level"].value_counts().rename_axis("level").reset_index(name="count")
        st.bar_chart(level_counts.set_index("level"))
    else:
        st.info("No log entries available to chart.")

with st.container():
    st.subheader("Recent Logs")
    if not df.empty:
        display_df = df.loc[:, ["timestamp", "level", "message"]].copy()
        display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str.slice(stop=23)
        st.dataframe(display_df.head(80), use_container_width=True)
    else:
        st.info("No recent log data to display.")

st.markdown("---")
st.caption("Monitor dashboard reads the weather app log file and surfaces live metrics, log level trends, and recent events.")
