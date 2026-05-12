import streamlit as st
import requests
from loguru import logger
import time
import boto3

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
        return None

API_KEY = get_api_key()

city = st.text_input("Enter City", "Lagos").strip()

if st.button("🔍 Get Weather", type="primary") and city:
    with st.spinner("Fetching weather data..."):
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
            data = requests.get(url, timeout=10).json()
            
            if data.get("cod") != 200:
                st.error(data.get("message", "City not found"))
            else:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Temperature", f"{data['main']['temp']}°C")
                col2.metric("Feels Like", f"{data['main']['feels_like']}°C")
                col3.metric("Humidity", f"{data['main']['humidity']}%")
                col4.metric("Wind Speed", f"{data['wind']['speed']} m/s")
                
                st.success(f"📍 {data['name']}, {data.get('sys',{}).get('country')}")
                icon = data['weather'][0]['icon']
                st.image(f"https://openweathermap.org/img/wn/{icon}@4x.png", width=150)
                
                logger.info(f"Weather fetched successfully for {city}")
        except Exception as e:
            st.error("Failed to fetch weather data")
            logger.error(f"Error fetching weather for {city}: {e}")

st.caption("Monitor Dashboard available at /monitor")
