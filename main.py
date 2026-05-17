import os
import re
import time
import datetime
from pathlib import Path

import boto3
import requests
import streamlit as st
from loguru import logger

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "weather_app.log"

logger.remove()
logger.add(
    str(LOG_FILE),
    rotation="10 MB",
    retention="14 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}",
)

# ---------------------------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌦️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@st.cache_resource(ttl=3600)
def get_secrets_manager_client():
    return boto3.client("secretsmanager")


@st.cache_resource(ttl=3600)
def get_api_key() -> str:
    try:
        client = get_secrets_manager_client()
        secret_name = os.getenv("OPENWEATHER_SECRET_NAME", "openweather-api-key-prod")
        response = client.get_secret_value(SecretId=secret_name)
        logger.info("Loaded API key from AWS Secrets Manager", secret_name=secret_name)
        return response["SecretString"]
    except Exception as exc:
        logger.warning("Secrets Manager lookup failed", error=str(exc))

    env_key = os.getenv("OPENWEATHER_API_KEY")
    if env_key:
        logger.info("Loaded API key from environment variable")
        return env_key

    fallback_key = os.getenv("OPENWEATHER_API_KEY_FALLBACK", "")
    if fallback_key:
        logger.info("Loaded API key from fallback environment variable")
        return fallback_key

    raise ValueError("OpenWeather API key is not configured. Set OPENWEATHER_API_KEY or configure Secrets Manager.")


def sanitize_city(city: str) -> str:
    cleaned = city.strip()
    cleaned = re.sub(r"[^a-zA-ZÀ-ÿ0-9 \-']", "", cleaned)
    return cleaned


def check_rate_limit() -> bool:
    now = time.time()
    if "request_timestamps" not in st.session_state:
        st.session_state.request_timestamps = []

    st.session_state.request_timestamps = [ts for ts in st.session_state.request_timestamps if now - ts < 60]
    if len(st.session_state.request_timestamps) >= 12:
        logger.warning("Rate limit reached", request_count=len(st.session_state.request_timestamps))
        st.error("⛔ Rate limit reached. Try again in a moment.")
        return False

    st.session_state.request_timestamps.append(now)
    return True


def format_temperature(value: float, units: str) -> str:
    suffix = "°C" if units == "metric" else "°F"
    return f"{value:.1f}{suffix}"


def wind_label(units: str) -> str:
    return "m/s" if units == "metric" else "mph"


def get_wind_direction(degrees: float) -> str:
    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]


def fetch_openweather(endpoint: str, city: str, units: str = "metric") -> dict:
    api_key = get_api_key()
    url = f"https://api.openweathermap.org/data/2.5/{endpoint}"
    params = {"q": city, "appid": api_key, "units": units}

    logger.info("Fetching OpenWeather data", endpoint=endpoint, city=city, units=units)
    response = requests.get(url, params=params, timeout=12)
    payload = response.json()

    if response.status_code != 200:
        message = payload.get("message", "Unable to fetch weather data").capitalize()
        logger.error("OpenWeather API returned error", status=response.status_code, message=message)
        raise ValueError(message)

    return payload


def parse_forecast_by_day(forecast_json: dict) -> list[dict]:
    timezone_offset = forecast_json.get("city", {}).get("timezone", 0)
    daily_groups: dict[datetime.date, dict] = {}

    for entry in forecast_json.get("list", []):
        timestamp = entry.get("dt", 0)
        local_time = datetime.datetime.utcfromtimestamp(timestamp + timezone_offset)
        local_date = local_time.date()
        weather = entry["weather"][0]

        bucket = daily_groups.setdefault(local_date, {
            "items": [],
            "temps": [],
            "humidities": [],
            "winds": [],
        })

        bucket["items"].append({
            "time": local_time,
            "icon": weather["icon"],
            "description": weather["description"].title(),
            "temp": entry["main"]["temp"],
            "humidity": entry["main"]["humidity"],
            "wind_speed": entry["wind"]["speed"],
            "wind_deg": entry["wind"].get("deg", 0),
        })
        bucket["temps"].append(entry["main"]["temp"])
        bucket["humidities"].append(entry["main"]["humidity"])
        bucket["winds"].append(entry["wind"]["speed"])

    forecast_days = []
    for day, values in sorted(daily_groups.items()):
        representative = min(
            values["items"],
            key=lambda item: abs(item["time"].hour - 12),
        )
        forecast_days.append({
            "date": day,
            "icon": representative["icon"],
            "description": representative["description"],
            "min_temp": min(values["temps"]),
            "max_temp": max(values["temps"]),
            "humidity": sum(values["humidities"]) / len(values["humidities"]),
            "wind_speed": sum(values["winds"]) / len(values["winds"]),
            "wind_direction": get_wind_direction(representative["wind_deg"]),
        })

    return forecast_days[:5]


def render_page_styles() -> None:
    st.markdown(
        "<style>"
        "body { background: linear-gradient(180deg, #eef2ff 0%, #f8fafc 100%); }"
        ".stApp { color: #111827; }"
        ".card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 20px; padding: 18px; box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08); }"
        ".card-title { font-size: 1rem; font-weight: 700; margin-bottom: 10px; }"
        ".metric-text { color: #4b5563; font-size: 0.95rem; margin: 2px 0; }"
        "</style>",
        unsafe_allow_html=True,
    )


def render_current_weather(current_weather: dict, units: str) -> None:
    weather = current_weather["weather"][0]
    visibility_km = current_weather.get("visibility", 0) / 1000
    unit_label = wind_label(units)

    st.subheader(f"Current weather in {current_weather['name']}, {current_weather['sys'].get('country', '')}")
    with st.container():
        cols = st.columns([2, 1], gap="large")
        with cols[0]:
            st.markdown(f"### {weather['description'].title()}")
            st.markdown(f"**Temperature:** {format_temperature(current_weather['main']['temp'], units)}")
            st.markdown(f"**Feels like:** {format_temperature(current_weather['main']['feels_like'], units)}")
            st.markdown(f"**Humidity:** {current_weather['main']['humidity']}%")
            st.markdown(f"**Pressure:** {current_weather['main']['pressure']} hPa")
            st.markdown(f"**Visibility:** {visibility_km:.1f} km")
            st.markdown(f"**Wind:** {current_weather['wind']['speed']:.1f} {unit_label} ({get_wind_direction(current_weather['wind'].get('deg', 0))})")
        with cols[1]:
            st.image(f"https://openweathermap.org/img/wn/{weather['icon']}@4x.png", width=220)


def render_forecast_cards(forecast_days: list[dict], units: str) -> None:
    if not forecast_days:
        st.warning("No forecast data available. Search for a city to show the 5-day outlook.")
        return

    cards = st.columns(len(forecast_days), gap="large")
    for forecast, card in zip(forecast_days, cards):
        with card:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='card-title'>{forecast['date'].strftime('%A, %b %d')}</div>", unsafe_allow_html=True)
            st.image(f"https://openweathermap.org/img/wn/{forecast['icon']}@2x.png", width=90)
            st.markdown(f"**{forecast['description']}**")
            st.markdown(f"<div class='metric-text'>Min: {format_temperature(forecast['min_temp'], units)}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-text'>Max: {format_temperature(forecast['max_temp'], units)}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-text'>Humidity: {forecast['humidity']:.0f}%</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-text'>Wind: {forecast['wind_speed']:.1f} {wind_label(units)} {forecast['wind_direction']}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


def initialize_session() -> None:
    defaults = {
        "last_city": "London",
        "last_units": "metric",
        "weather_data": None,
        "forecast_data": None,
        "request_timestamps": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def build_dashboard() -> None:
    render_page_styles()
    st.title("🌦️ Weather Dashboard")
    st.markdown("A clean public weather dashboard with 5-day forecast grouping, OpenWeatherMap integration, and built-in rate limiting.")

    with st.sidebar:
        st.header("Search & settings")
        city_input = st.text_input("City", value=st.session_state.get("last_city", "London"))
        units = st.radio("Units", ["Celsius", "Fahrenheit"], horizontal=True)
        unit_code = "metric" if units == "Celsius" else "imperial"
        search_button = st.button("Search")
        st.markdown("---")
        st.markdown("**Usage**")
        st.markdown("- 12 requests per minute maximum")
        st.markdown("- Forecast uses `/data/2.5/forecast`")
        st.markdown("- API key from AWS Secrets Manager or `OPENWEATHER_API_KEY`")

    if search_button:
        city = sanitize_city(city_input)
        if not city:
            st.error("Please enter a valid city name.")
            logger.warning("Invalid city search", raw_input=city_input)
        elif not check_rate_limit():
            logger.warning("Rate-limited search attempt", city=city)
        else:
            try:
                with st.spinner("Loading weather data..."):
                    forecast = fetch_openweather("forecast", city, unit_code)
                    current = fetch_openweather("weather", city, unit_code)
                    st.session_state.weather_data = current
                    st.session_state.forecast_data = forecast
                    st.session_state.last_city = city
                    st.session_state.last_units = unit_code
                    logger.info("Weather refresh successful", city=city, units=unit_code)
            except ValueError as exc:
                st.error(str(exc))
            except requests.RequestException as exc:
                st.error("Unable to reach OpenWeatherMap. Please try again later.")
                logger.error("HTTP request failed", error=str(exc), city=city)
            except Exception as exc:
                st.error("An unexpected error occurred while fetching weather data.")
                logger.exception("Unexpected error during weather fetch")

    weather_data = st.session_state.get("weather_data")
    forecast_data = st.session_state.get("forecast_data")
    active_units = st.session_state.get("last_units", unit_code)

    tabs = st.tabs(["Current Weather", "5-Day Forecast"])

    with tabs[0]:
        if weather_data:
            render_current_weather(weather_data, active_units)
        else:
            st.info("Search for a city in the sidebar to display the current weather.")

    with tabs[1]:
        if forecast_data:
            daily_forecast = parse_forecast_by_day(forecast_data)
            render_forecast_cards(daily_forecast, active_units)
        else:
            st.info("Search for a city in the sidebar to display the 5-day forecast.")

    st.markdown("---")
    st.caption(f"Logs stored to `{LOG_FILE}`")


def main() -> None:
    initialize_session()
    build_dashboard()


if __name__ == "__main__":
    main()
