import streamlit as st
import requests
from loguru import logger
import time
import boto3
import re

# ====================== LOGGING ======================
logger.remove()
logger.add("weather_app.log", 
           rotation="10 MB", 
           level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}")

st.set_page_config(page_title="Secure Weather App", page_icon="🌤️", layout="wide")

st.title("🌤️ Secure Weather Dashboard")
st.markdown("### Real-time Public Weather Sentinel")

# Get API Key
@st.cache_resource(ttl=3600)
def get_api_key():
    try:
        client = boto3.client('secretsmanager', region_name="us-east-1")
        response = client.get_secret_value(SecretId="openweather-api-key-prod")
        return response['SecretString']
    except Exception as e:
        logger.error(f"Secrets Manager Error: {e}")
        return None

API_KEY = get_api_key()

# Rate Limiting
def check_rate_limit():
    now = time.time()
    if "request_times" not in st.session_state:
        st.session_state.request_times = []
    st.session_state.request_times = [t for t in st.session_state.request_times if now - t < 60]
    if len(st.session_state.request_times) >= 12:
        logger.warning("Rate limit exceeded")
        st.error("⛔ Too many requests. Please wait a minute.")
        return False
    st.session_state.request_times.append(now)
    return True

city = st.text_input("Enter City Name", "Lagos").strip()

if st.button("🔍 Get Weather", type="primary") and city:
    if check_rate_limit():
        logger.info(f"Weather Request | City: {city}")
        with st.spinner(f"Fetching weather for **{city}**..."):
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                
                if resp.status_code == 200:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Temperature", f"{data['main']['temp']:.1f}°C")
                    col2.metric("Feels Like", f"{data['main']['feels_like']:.1f}°C")
                    col3.metric("Humidity", f"{data['main']['humidity']}%")
                    col4.metric("Wind", f"{data['wind']['speed']} m/s")
                    
                    st.subheader(f"📍 {data['name']}, {data.get('sys',{}).get('country','')}")
                    icon = data['weather'][0]['icon']
                    st.image(f"https://openweathermap.org/img/wn/{icon}@4x.png")
                    st.success("✅ Data retrieved successfully")
                else:
                    st.error(data.get("message", "City not found"))
            except Exception as e:
                st.error("Failed to fetch weather data")
                logger.error(f"Error for {city}: {e}")

st.caption("Monitor Dashboard → /monitor | Logs sent to CloudWatch")
