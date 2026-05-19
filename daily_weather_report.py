import boto3
import requests
from datetime import datetime
from loguru import logger

logger.add("daily_report.log", rotation="5 MB")

cities = ["Lagos", "Ibadan", "London", "Toronto"]

def get_api_key():
    try:
        client = boto3.client('secretsmanager', region_name="us-east-1")
        response = client.get_secret_value(SecretId="openweather-api-key-prod")
        return response['SecretString']
    except:
        return "23fdaa3b32f1c696c16fbd964181fb8d"

def get_weather(city):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={get_api_key()}&units=metric"
        data = requests.get(url, timeout=10).json()
        
        if data.get("cod") != 200:
            return f"❌ {city}: {data.get('message')}"
            
        return f"""
🌍 **{data['name']}, {data.get('sys',{}).get('country')}**
🌡️ Temp: {data['main']['temp']:.1f}°C (Feels like {data['main']['feels_like']:.1f}°C)
💧 Humidity: {data['main']['humidity']}%
🌬️ Wind: {data['wind']['speed']} m/s
☁️ {data['weather'][0]['description'].title()}
"""
    except Exception as e:
        return f"❌ Error fetching {city}: {e}"

# Generate Report
report = f"🌤️ **Daily Weather Report - {datetime.now().strftime('%A, %d %B %Y')}**\n\n"

for city in cities:
    report += get_weather(city) + "\n"

report += f"\n---\nSent at {datetime.now().strftime('%H:%M')} UTC"

print(report)

# ====================== SEND NOTIFICATIONS ======================

# 1. EMAIL via AWS SES
def send_email(report):
    try:
        ses = boto3.client('ses', region_name='us-east-1')
        ses.send_email(
            Source='oluwatobifredrick751@gmail.com',
            Destination={'ToAddresses': ['oluwatobifredrick751@gmail.com']},
            Message={
                'Subject': {'Data': f'Daily Weather Report - {datetime.now().strftime("%d %B %Y")}'},
                'Body': {'Text': {'Data': report}}
            }
        )
        logger.info("✅ Email sent successfully")
    except Exception as e:
        logger.error(f"Email failed: {e}")

# 2. TELEGRAM
def send_telegram(report):
    try:
        TELEGRAM_BOT_TOKEN = "8996298652:AAFcFtW1q8PbYE8TRRhrTWRkvuLa2_WPB_s"
        TELEGRAM_CHAT_ID = "7162398118"   # We will get this next
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": report,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
        logger.info("✅ Telegram message sent")
    except Exception as e:
        logger.error(f"Telegram failed: {e}")

# Send both
send_email(report)
send_telegram(report)

logger.info("Daily weather report completed")
