import streamlit as st
import requests
from loguru import logger
import time
import boto3
import re

logger.remove()
logger.add("weather_app.log", rotation="10 MB", level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}")

st.set_page_config(page_title="Secure Weather App", page_icon="🌤️", layout="wide")

st.title("🌤️ Secure Weather Dashboard")
st.markdown("### Public Weather Sentinel")

@st.cache_resource(ttl=3600)
def get_api_key():
    try:
        client = boto3.client('secretsmanager', region_name="us-east-1")
        response = client.get_secret_value(SecretId="openweather-api-key-prod")
        return response['SecretString']
    except:
        # Fallback to your key
        return "23fdaa3b32f1c696c16fbd964181fb8d"

API_KEY = get_api_key()

def check_rate_limit():
    now = time.time()
    if "requests" not in st.session_state:
        st.session_state.requests = []
    st.session_state.requests = [t for t in st.session_state.requests if now - t < 60]
    if len(st.session_state.requests) >= 12:
        st.error("Rate limit reached. Try again later.")
        return False
    st.session_state.requests.append(now)
    return True

city = st.text_input("Enter City Name", "Lagos").strip()

if st.button("🔍 Get Weather", type="primary") and city:
    if check_rate_limit():
        logger.info(f"Weather Request | City: {city}")
        with st.spinner(f"Fetching for **{city}**..."):
            try:
                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
                data = requests.get(url, timeout=10).json()
                
                if data.get("cod") != 200:
                    st.error(data.get("message", "City not found"))
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Temperature", f"{data['main']['temp']:.1f}°C")
                    col2.metric("Feels Like", f"{data['main']['feels_like']:.1f}°C")
                    col3.metric("Humidity", f"{data['main']['humidity']}%")
                    col4.metric("Wind", f"{data['wind']['speed']} m/s")
                    
                    st.subheader(f"📍 {data['name']}, {data.get('sys',{}).get('country','')}")
                    icon = data['weather'][0]['icon']
                    st.image(f"https://openweathermap.org/img/wn/{icon}@4x.png", width=200)
            except Exception as e:
                st.error("Failed to fetch weather")
                logger.error(f"Error: {e}")

st.caption("Monitor at /monitor")
