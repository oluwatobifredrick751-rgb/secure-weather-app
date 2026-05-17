import streamlit as st
import requests
from loguru import logger
import time
import boto3
import os
from datetime import datetime, timedelta

# ====================== LOGGING ======================
logger.remove()
logger.add("weather_app.log", 
           rotation="10 MB", 
           level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}")

st.set_page_config(
    page_title="Secure Weather App",
    page_icon="🌤️",
    layout="wide"
)

st.title("🌤️ Secure Weather Dashboard")
st.markdown("### Clean Public Weather Sentinel")

# ====================== API KEY ======================
@st.cache_resource(ttl=3600)
def get_api_key():
    # AWS Secrets Manager
    try:
        client = boto3.client('secretsmanager', region_name="us-east-1")
        response = client.get_secret_value(SecretId="openweather-api-key-prod")
        return response['SecretString']
    except:
        pass
    # Environment variable fallback
    key = os.getenv("OPENWEATHER_API_KEY")
    if key:
        return key
    # Your key as last resort
    return "23fdaa3b32f1c696c16fbd964181fb8d"

API_KEY = get_api_key()

# ====================== RATE LIMITING ======================
def check_rate_limit():
    now = time.time()
    if "request_times" not in st.session_state:
        st.session_state.request_times = []
    st.session_state.request_times = [t for t in st.session_state.request_times if now - t < 60]
    if len(st.session_state.request_times) >= 12:
        logger.warning("Rate limit exceeded")
        st.error("⛔ Rate limit reached (12 requests/min). Please wait.")
        return False
    st.session_state.request_times.append(now)
    return True

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("Search & Settings")
    city = st.text_input("City", value="London", key="city_input")
    unit = st.radio("Units", ["Celsius (°C)", "Fahrenheit (°F)"], horizontal=True, key="unit_toggle")
    unit_symbol = "metric" if "Celsius" in unit else "imperial"
    temp_symbol = "°C" if "Celsius" in unit else "°F"

    st.markdown("---")
    st.caption("12 requests per minute maximum")

# ====================== TABS ======================
tab1, tab2 = st.tabs(["🌤️ Current Weather", "📅 5-Day Forecast"])

with tab1:
    if st.button("🔍 Get Current Weather", type="primary", key="current_btn"):
        if check_rate_limit() and city:
            logger.info(f"Current weather request for {city}")
            with st.spinner(f"Fetching current weather for **{city}**..."):
                try:
                    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units={unit_symbol}"
                    resp = requests.get(url, timeout=10)
                    data = resp.json()

                    if resp.status_code == 200:
                        col1, col2, col3, col4 = st.columns(4)
                        col1.metric("Temperature", f"{data['main']['temp']:.1f}{temp_symbol}")
                        col2.metric("Feels Like", f"{data['main']['feels_like']:.1f}{temp_symbol}")
                        col3.metric("Humidity", f"{data['main']['humidity']}%")
                        col4.metric("Wind", f"{data['wind']['speed']} m/s")

                        st.subheader(f"📍 {data['name']}, {data.get('sys', {}).get('country', '')}")
                        icon = data['weather'][0]['icon']
                        st.image(f"https://openweathermap.org/img/wn/{icon}@4x.png", width=200)
                        st.success("✅ Updated successfully")
                    else:
                        st.error(data.get("message", "City not found"))
                except Exception as e:
                    st.error("Failed to fetch weather data")
                    logger.error(f"Error: {e}")

with tab2:
    if st.button("📅 Get 5-Day Forecast", type="primary", key="forecast_btn"):
        if check_rate_limit() and city:
            logger.info(f"5-day forecast request for {city}")
            with st.spinner(f"Fetching 5-day forecast for **{city}**..."):
                try:
                    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city}&appid={API_KEY}&units={unit_symbol}"
                    resp = requests.get(url, timeout=10)
                    data = resp.json()

                    if resp.status_code == 200:
                        st.subheader(f"5-Day Forecast for {data['city']['name']}")
                        daily = {}
                        for item in data['list']:
                            date = item['dt_txt'].split(" ")[0]
                            if date not in daily:
                                daily[date] = item
                            else:
                                # Keep the one with highest temp or first
                                if item['main']['temp_max'] > daily[date]['main']['temp_max']:
                                    daily[date] = item

                        cols = st.columns(5)
                        for idx, (date, item) in enumerate(list(daily.items())[:5]):
                            with cols[idx]:
                                dt = datetime.strptime(date, "%Y-%m-%d")
                                st.markdown(f"**{dt.strftime('%a, %b %d')}**")
                                icon = item['weather'][0]['icon']
                                st.image(f"https://openweathermap.org/img/wn/{icon}@2x.png")
                                st.write(f"**{item['main']['temp_max']:.1f}** / {item['main']['temp_min']:.1f}{temp_symbol}")
                                st.caption(item['weather'][0]['description'].title())
                    else:
                        st.error("Could not fetch forecast")
                except Exception as e:
                    st.error("Forecast request failed")
                    logger.error(f"Forecast error: {e}")

st.caption("Logs are saved to weather_app.log • Built with ❤️ using Streamlit")