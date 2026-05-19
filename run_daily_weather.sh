#!/bin/bash
cd /home/ec2-user/secure-weather-app
python3 daily_weather_report.py >> daily_report.log 2>&1
