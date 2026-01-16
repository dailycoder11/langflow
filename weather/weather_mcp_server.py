#!/usr/bin/env python3
"""
Weather MCP Server
Provides weather data for the last 7 days using Open-Meteo API
Implements the Model Context Protocol (MCP) specification
"""

import asyncio
from datetime import datetime, timedelta

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


# Initialize MCP Server
server = Server("weather-mcp")


def get_coordinates(city: str) -> dict:
    """
    Get latitude and longitude for a city using Open-Meteo Geocoding API
    """
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }
        
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        if data.get("results"):
            result = data["results"][0]
            return {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "name": result["name"],
                "country": result.get("country", ""),
                "timezone": result.get("timezone", "UTC")
            }
        else:
            return {"error": f"City '{city}' not found"}
    except Exception as e:
        return {"error": f"Failed to get coordinates: {str(e)}"}


def get_weather_data(latitude: float, longitude: float, timezone: str = "auto") -> dict:
    """
    Get weather data for the last 7 days using Open-Meteo API
    """
    try:
        # Calculate date range for last 7 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=6)
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
            "timezone": timezone,
            "temperature_unit": "celsius"
        }
        
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # Format the response
        weather_records = []
        if "daily" in data:
            daily = data["daily"]
            for i in range(len(daily["time"])):
                weather_records.append({
                    "date": daily["time"][i],
                    "max_temp_c": daily["temperature_2m_max"][i],
                    "min_temp_c": daily["temperature_2m_min"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "max_wind_speed_kmh": daily["windspeed_10m_max"][i]
                })
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": data.get("timezone", "UTC"),
            "records": weather_records
        }
    except Exception as e:
        return {"error": f"Failed to get weather data: {str(e)}"}


def get_forecast_data(latitude: float, longitude: float, timezone: str = "auto") -> dict:
    """
    Get weather forecast for the next 7 days using Open-Meteo API
    """
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
            "timezone": timezone,
            "temperature_unit": "celsius",
            "forecast_days": 7
        }
        
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        data = response.json()
        
        # Format the response
        forecast_records = []
        if "daily" in data:
            daily = data["daily"]
            for i in range(len(daily["time"])):
                forecast_records.append({
                    "date": daily["time"][i],
                    "max_temp_c": daily["temperature_2m_max"][i],
                    "min_temp_c": daily["temperature_2m_min"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "max_wind_speed_kmh": daily["windspeed_10m_max"][i]
                })
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": data.get("timezone", "UTC"),
            "records": forecast_records
        }
    except Exception as e:
        return {"error": f"Failed to get forecast data: {str(e)}"}


def get_weather_for_city(city: str) -> dict:
    """
    Get weather for a city (combined geocoding + weather data)
    """
    # Get coordinates
    coords = get_coordinates(city)
    
    if "error" in coords:
        return coords
    
    # Get weather data
    weather = get_weather_data(
        coords["latitude"],
        coords["longitude"],
        coords.get("timezone", "auto")
    )
    
    # Add city info to weather response
    weather["city"] = coords["name"]
    weather["country"] = coords["country"]
    
    return weather


# MCP Tool Definition
@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List available tools exposed by this MCP server
    """
    return [
        Tool(
            name="get_weather",
            description="Get historical weather data for the last 7 days for a specific city. Returns temperature (min/max), precipitation, and wind speed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get weather for (e.g., 'London', 'New York', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        ),
        Tool(
            name="get_forecast",
            description="Get weather forecast for the next 7 days for a specific city. Returns temperature (min/max), precipitation, and wind speed.",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "Name of the city to get forecast for (e.g., 'London', 'New York', 'Tokyo')"
                    }
                },
                "required": ["city"]
            }
        )
    ]


# MCP Tool Handler
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Handle tool calls from MCP clients
    """
    if name == "get_weather":
        city = arguments.get("city", "").strip()
        
        if not city:
            return [TextContent(type="text", text="Error: City name is required")]
        
        result = get_weather_for_city(city)
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        # Format the result nicely
        output = f"""Weather Data (PAST 7 DAYS) for {result.get('city', 'Unknown')} ({result.get('country', 'Unknown')})
Location: {result.get('latitude')}, {result.get('longitude')}
Timezone: {result.get('timezone')}

Last 7 Days:
{'='*70}"""
        for record in result.get("records", []):
            output += f"""
Date: {record['date']}
  Max Temperature: {record['max_temp_c']}°C
  Min Temperature: {record['min_temp_c']}°C
  Precipitation: {record['precipitation_mm']}mm
  Max Wind Speed: {record['max_wind_speed_kmh']}km/h"""
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_forecast":
        city = arguments.get("city", "").strip()
        
        if not city:
            return [TextContent(type="text", text="Error: City name is required")]
        
        # Get coordinates first
        coords = get_coordinates(city)
        
        if "error" in coords:
            return [TextContent(type="text", text=f"Error: {coords['error']}")]
        
        # Get forecast data
        result = get_forecast_data(
            coords["latitude"],
            coords["longitude"],
            coords.get("timezone", "auto")
        )
        
        if "error" in result:
            return [TextContent(type="text", text=f"Error: {result['error']}")]
        
        # Format the result nicely
        output = f"""Weather Forecast (NEXT 7 DAYS) for {coords.get('name', 'Unknown')} ({coords.get('country', 'Unknown')})
Location: {result.get('latitude')}, {result.get('longitude')}
Timezone: {result.get('timezone')}

Next 7 Days:
{'='*70}"""
        for record in result.get("records", []):
            output += f"""
Date: {record['date']}
  Max Temperature: {record['max_temp_c']}°C
  Min Temperature: {record['min_temp_c']}°C
  Precipitation: {record['precipitation_mm']}mm
  Max Wind Speed: {record['max_wind_speed_kmh']}km/h"""
        
        return [TextContent(type="text", text=output)]
    
    return [TextContent(type="text", text=f"Error: Unknown tool '{name}'")]


async def main():
    """
    Run the MCP server with stdio communication
    """
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
