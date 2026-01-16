#!/usr/bin/env python3
"""
Weather MCP Server (SSE)
Exposes:
- get_weather   (past 7 days)
- get_forecast  (next 7 days)
"""

from datetime import datetime, timedelta
import httpx
import uvicorn

from mcp.server.fastmcp import FastMCP


# --------------------------------------------------
# CREATE MCP SERVER
# --------------------------------------------------
mcp = FastMCP("weather-mcp")


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def get_coordinates(city: str) -> dict:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city, "count": 1, "language": "en", "format": "json"}

    r = httpx.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if not data.get("results"):
        return {"error": f"City '{city}' not found"}

    res = data["results"][0]
    return {
        "latitude": res["latitude"],
        "longitude": res["longitude"],
        "name": res["name"],
        "country": res.get("country", ""),
        "timezone": res.get("timezone", "UTC"),
    }


def get_past_weather(lat: float, lon: float, timezone: str) -> dict:
    end = datetime.now().date()
    start = end - timedelta(days=6)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "windspeed_10m_max"
        ),
        "timezone": timezone,
        "temperature_unit": "celsius",
    }

    r = httpx.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    records = []
    daily = data.get("daily", {})
    for i, date in enumerate(daily.get("time", [])):
        records.append({
            "date": date,
            "max_temp_c": daily["temperature_2m_max"][i],
            "min_temp_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "max_wind_speed_kmh": daily["windspeed_10m_max"][i],
        })

    return {
        "timezone": data.get("timezone", "UTC"),
        "records": records,
    }


def get_future_forecast(lat: float, lon: float, timezone: str) -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": (
            "temperature_2m_max,"
            "temperature_2m_min,"
            "precipitation_sum,"
            "windspeed_10m_max"
        ),
        "forecast_days": 7,
        "timezone": timezone,
        "temperature_unit": "celsius",
    }

    r = httpx.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    records = []
    daily = data.get("daily", {})
    for i, date in enumerate(daily.get("time", [])):
        records.append({
            "date": date,
            "max_temp_c": daily["temperature_2m_max"][i],
            "min_temp_c": daily["temperature_2m_min"][i],
            "precipitation_mm": daily["precipitation_sum"][i],
            "max_wind_speed_kmh": daily["windspeed_10m_max"][i],
        })

    return {
        "timezone": data.get("timezone", "UTC"),
        "records": records,
    }


# --------------------------------------------------
# MCP TOOLS
# --------------------------------------------------
@mcp.tool()
def get_weather(city: str) -> dict:
    """
    Get historical weather data for the past 7 days for a city.
    """
    if not city.strip():
        return {"error": "City name is required"}

    coords = get_coordinates(city)
    if "error" in coords:
        return coords

    weather = get_past_weather(
        coords["latitude"],
        coords["longitude"],
        coords["timezone"],
    )

    return {
        "city": coords["name"],
        "country": coords["country"],
        **weather,
    }


@mcp.tool()
def get_forecast(city: str) -> dict:
    """
    Get weather forecast for the next 7 days for a city.
    """
    if not city.strip():
        return {"error": "City name is required"}

    coords = get_coordinates(city)
    if "error" in coords:
        return coords

    forecast = get_future_forecast(
        coords["latitude"],
        coords["longitude"],
        coords["timezone"],
    )

    return {
        "city": coords["name"],
        "country": coords["country"],
        **forecast,
    }


# --------------------------------------------------
# ENTRYPOINT
# --------------------------------------------------
if __name__ == "__main__":
    print("Starting Weather MCP Server on http://127.0.0.1:8010/sse")
    uvicorn.run(
        mcp.sse_app,     # <-- correct for YOUR MCP version
        host="127.0.0.1",
        port=8010,
        log_level="info",
    )