import os
import re
import time
import datetime
import requests
import boto3
import streamlit as st
from loguru import logger
from collections import Counter

# ====================== LOGGING ======================
logger.remove()
logger.add(
    "weather_app.log",
    rotation="10 MB",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
)

st.set_page_config(
    page_title="Secure Weather App",
    page_icon="🌤️",
    layout="wide",
)

st.markdown(
    "<style>"
    "body { background: #f3f4f6; }"
    ".stApp { color: #111827; }"
    ".card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 18px; padding: 20px; box-shadow: 0 18px 48px rgba(15, 23, 42, 0.08); }"
    ".card-title { font-size: 1.1rem; font-weight: 700; color: #111827; margin-bottom: 10px; }"
    ".card-text { color: #6b7280; margin-bottom: 12px; }"
    ".streamlit-expanderHeader { font-weight: 600; }"
    "</style>",
    unsafe_allow_html=True,
)

# ======== Security helpers ========
@st.cache_resource(ttl=3600)
def get_api_key():
    try:
        client = boto3.client("secretsmanager", region_name="us-east-1")
        response = client.get_secret_value(SecretId="openweather-api-key-prod")
        return response["SecretString"]
    except Exception as exc:
        logger.warning(f"Secrets Manager lookup failed: {exc}")

    env_key = os.getenv("OPENWEATHER_API_KEY")
    if env_key:
        return env_key

    fallback_key = os.getenv("OPENWEATHER_API_KEY_FALLBACK", "")
    return fallback_key


def get_app_password() -> str:
    return os.getenv("APP_PASSWORD", "SecureWeather2026!")


def sanitize_city(city: str) -> str:
    cleaned = city.strip()
    cleaned = re.sub(r"[^a-zA-ZÀ-ÿ0-9 \-']", "", cleaned)
    return cleaned


def check_rate_limit() -> bool:
    now = time.time()
    if "request_times" not in st.session_state:
        st.session_state.request_times = []

    st.session_state.request_times = [ts for ts in st.session_state.request_times if now - ts < 60]
    if len(st.session_state.request_times) >= 12:
        logger.warning("Rate limit exceeded")
        st.error("⛔ Rate limit reached. Please wait 60 seconds.")
        return False

    st.session_state.request_times.append(now)
    return True


def authenticate(password: str) -> bool:
    success = password == get_app_password()
    if success:
        st.session_state.authenticated = True
        logger.info("User authenticated successfully")
    else:
        st.session_state.authenticated = False
        logger.warning("Invalid login attempt")
    return success


def initialize_session():
    defaults = {
        "authenticated": False,
        "request_times": [],
        "weather_data": None,
        "forecast_data": None,
        "last_city": "",
        "last_units": "metric",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def format_temperature(value: float, units: str) -> str:
    symbol = "°C" if units == "metric" else "°F"
    return f"{value:.1f}{symbol}"


def parse_daily_forecast(forecast_json: dict) -> list[dict]:
    groups: dict[datetime.date, dict] = {}
    timezone_offset = forecast_json.get("city", {}).get("timezone", 0)

    for entry in forecast_json.get("list", []):
        ts = entry.get("dt", 0)
        local_time = datetime.datetime.utcfromtimestamp(ts + timezone_offset)
        day = local_time.date()
        weather = entry["weather"][0]

        bucket = groups.setdefault(day, {
            "temps": [],
            "humidity": [],
            "icons": [],
            "descriptions": [],
        })
        bucket["temps"].append(entry["main"]["temp"])
        bucket["humidity"].append(entry["main"]["humidity"])
        bucket["icons"].append(weather["icon"])
        bucket["descriptions"].append(weather["description"])

    daily = []
    for day, values in groups.items():
        icon = Counter(values["icons"]).most_common(1)[0][0]
        description = Counter(values["descriptions"]).most_common(1)[0][0]
        daily.append(
            {
                "date": day,
                "icon": icon,
                "min_temp": min(values["temps"]),
                "max_temp": max(values["temps"]),
                "description": description.title(),
                "humidity": sum(values["humidity"]) / len(values["humidity"]),
            }
        )

    daily.sort(key=lambda item: item["date"])
    return daily[:5]


def fetch_openweather(endpoint: str, city: str, units: str = "metric") -> dict:
    api_key = get_api_key()
    if not api_key:
        logger.error("OpenWeather API key is missing")
        raise ValueError("API key is not configured. Set it in AWS Secrets Manager or OPENWEATHER_API_KEY.")

    url = f"https://api.openweathermap.org/data/2.5/{endpoint}"
    params = {"q": city, "appid": api_key, "units": units}
    logger.info(f"Fetching {endpoint} for city={city} units={units}")

    response = requests.get(url, params=params, timeout=12)
    payload = response.json()
    if response.status_code != 200:
        message = payload.get("message", "Unable to fetch weather data")
        logger.error(f"OpenWeather error {response.status_code}: {message}")
        raise ValueError(message)

    return payload


def render_current_weather(data: dict, units: str) -> None:
    wind_label = "m/s" if units == "metric" else "mph"
    weather = data["weather"][0]

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    cols = st.columns([1, 1, 1, 1])
    cols[0].metric("Temperature", format_temperature(data["main"]["temp"], units))
    cols[1].metric("Feels Like", format_temperature(data["main"]["feels_like"], units))
    cols[2].metric("Humidity", f"{data['main']['humidity']}%")
    cols[3].metric("Wind", f"{data['wind']['speed']:.1f} {wind_label}")

    st.markdown(f"### 📍 {data['name']}, {data.get('sys', {}).get('country', '')}")
    st.image(f"https://openweathermap.org/img/wn/{weather['icon']}@4x.png", width=180)
    st.markdown(f"**{weather['description'].title()}**")
    st.markdown("**Pressure:** " f"{data['main']['pressure']} hPa  ")
    st.markdown("**Visibility:** " f"{data.get('visibility', 0) / 1000:.1f} km")
    st.markdown("</div>", unsafe_allow_html=True)


def render_forecast_cards(forecast_days: list[dict], units: str) -> None:
    if not forecast_days:
        st.warning("No forecast data is available.")
        return

    for chunk_start in range(0, len(forecast_days), 3):
        row = forecast_days[chunk_start : chunk_start + 3]
        cols = st.columns(len(row), gap="large")
        for forecast, col in zip(row, cols):
            with col:
                col.markdown("<div class='card'>", unsafe_allow_html=True)
                col.markdown(f"<div class='card-title'>{forecast['date'].strftime('%A, %b %d')}</div>", unsafe_allow_html=True)
                col.image(f"https://openweathermap.org/img/wn/{forecast['icon']}@2x.png", width=120)
                col.markdown(f"<div class='card-text'>{forecast['description']}</div>", unsafe_allow_html=True)
                col.metric("Min", format_temperature(forecast['min_temp'], units))
                col.metric("Max", format_temperature(forecast['max_temp'], units))
                col.markdown(f"**Humidity:** {forecast['humidity']:.0f}%")
                col.markdown("</div>", unsafe_allow_html=True)


def render_login_panel() -> None:
    st.sidebar.markdown("## 🔐 Secure Login")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Sign in"):
        if authenticate(password):
            st.sidebar.success("Authenticated")
            st.experimental_rerun()
        else:
            st.sidebar.error("Invalid password")


initialize_session()

if not st.session_state.authenticated:
    st.title("Secure Weather App")
    st.markdown("### Authenticate to access current weather and forecast data.")
    render_login_panel()
    st.stop()

st.sidebar.success("Authenticated")
st.sidebar.markdown("---")
st.sidebar.markdown("Enter a city and choose your preferred temperature units.")

city_raw = st.text_input("City", "Lagos")
units = st.radio("Units", ["Celsius", "Fahrenheit"], horizontal=True)
unit_code = "metric" if units == "Celsius" else "imperial"
search = st.button("🔍 Get Weather")

if search:
    city = sanitize_city(city_raw)
    if not city:
        st.error("Please enter a valid city name.")
    elif not check_rate_limit():
        pass
    else:
        try:
            with st.spinner("Fetching weather data..."):
                st.session_state.weather_data = fetch_openweather("weather", city, unit_code)
                st.session_state.forecast_data = fetch_openweather("forecast", city, unit_code)
                st.session_state.last_city = city
                st.session_state.last_units = unit_code
                logger.info(f"Weather query success for city={city}")
        except ValueError as exc:
            st.error(str(exc).capitalize())
        except Exception as exc:
            st.error("Failed to fetch weather data. Please try again.")
            logger.error(f"Unexpected error for city={city}: {exc}")

if st.session_state.weather_data and st.session_state.forecast_data:
    weather_data = st.session_state.weather_data
    forecast_data = st.session_state.forecast_data
elif st.session_state.last_city:
    try:
        weather_data = fetch_openweather("weather", st.session_state.last_city, st.session_state.last_units)
        forecast_data = fetch_openweather("forecast", st.session_state.last_city, st.session_state.last_units)
    except Exception:
        weather_data = None
        forecast_data = None
else:
    weather_data = None
    forecast_data = None

st.markdown("# 🌤️ Secure Weather Dashboard")
st.markdown("Modern weather insights with secure access and responsive forecasting.")
st.divider()

tabs = st.tabs(["Current Weather", "5-Day Forecast"])

with tabs[0]:
    if weather_data:
        render_current_weather(weather_data, st.session_state.last_units)
    else:
        st.info("Search for a city above to display the current weather.")

with tabs[1]:
    if forecast_data:
        forecast_days = parse_daily_forecast(forecast_data)
        render_forecast_cards(forecast_days, st.session_state.last_units)
    else:
        st.info("Search for a city above to display the 5-day forecast.")

st.caption("Monitor available at /monitor • Logs stored locally and ready for CloudWatch ingestion.")
