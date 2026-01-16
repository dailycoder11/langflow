# Weather MCP Server

A Model Context Protocol (MCP) server that provides weather data for the last 7 days using the free [Open-Meteo API](https://open-meteo.com/en/docs).

## Files

- **`weather_mcp_server.py`** - The MCP server implementation
- **`test_weather_mcp.py`** - Simple client that connects and tests the server
- **`test_weather_mcp_advanced.py`** - Advanced client supporting both Python and `uv` execution
- **`mcp_config.json`** - MCP configuration for use with Claude or other clients

## Installation

```bash
# Install dependencies
pip install mcp httpx
```

## Usage

### Method 1: Simple Python Client

```bash
# Test with a single city
python test_weather_mcp.py "London"

# Test with multiple cities
python test_weather_mcp.py "London" "Paris" "Tokyo"
```

### Method 2: Advanced Client (Python or UV)

```bash
# Using Python directly
python test_weather_mcp_advanced.py "London"

# Using uv to run the server
python test_weather_mcp_advanced.py --uv "London"

# Test with multiple cities
python test_weather_mcp_advanced.py --uv "London" "Paris" "Tokyo" "New York"
```

### Method 3: Advanced Client with Interactive Mode

The advanced client now supports an **interactive mode** where you're asked:
1. Which city you want weather for
2. Whether you need past (last 7 days) or future (next 7 days) data
3. Which execution method to use (Python or UV)

Simply run without arguments for interactive mode:

```bash
python test_weather_mcp_advanced.py
```

You'll be prompted with options:
```
📍 Enter city name (e.g., London, Paris, Tokyo): London

📅 What type of data do you need?
  1) Past weather data (last 7 days)
  2) Future forecast (next 7 days)
Enter your choice (1 or 2): 2

🔧 How should the server be started?
  1) Using Python (python)
  2) Using UV (uv run)
Enter your choice (1 or 2): 2
```

## Available Tools

### `get_weather`

Get **historical** weather data for the last 7 days for a specific city.

**Parameters:**
- `city` (string, required): Name of the city to get weather for (e.g., 'London', 'New York', 'Tokyo')

**Returns:**
- City name and country
- Coordinates (latitude, longitude)
- Timezone
- Last 7 days of weather data including:
  - Date
  - Max/Min temperature (°C)
  - Precipitation (mm)
  - Max wind speed (km/h)

### `get_forecast`

Get **weather forecast** for the next 7 days for a specific city.

**Parameters:**
- `city` (string, required): Name of the city to get forecast for (e.g., 'London', 'New York', 'Tokyo')

**Returns:**
- City name and country
- Coordinates (latitude, longitude)
- Timezone
- Next 7 days of forecast data including:
  - Date
  - Max/Min temperature (°C)
  - Precipitation (mm)
  - Max wind speed (km/h)

## Example Output

```
Weather Data for London (United Kingdom)
Location: 51.50853, -0.12574
Timezone: Europe/London

Last 7 Days:
===============================================================
Date: 2025-12-16
  Max Temperature: 11.4°C
  Min Temperature: 6.0°C
  Precipitation: 4.5mm
  Max Wind Speed: 12.7km/h
...
```

## How It Works

1. **Geocoding**: Converts city name to coordinates using Open-Meteo Geocoding API
2. **Weather Data**: Fetches historical weather data for the last 7 days using Open-Meteo Archive API
3. **MCP Protocol**: Exposes weather functionality via the Model Context Protocol for integration with AI applications

## Starting the Server as a Subprocess

The advanced client shows how to start the server as a separate process:

```python
from mcp.client.stdio import stdio_client, StdioServerParameters

# Using Python
server_params = StdioServerParameters(
    command="python",
    args=["weather_mcp_server.py"]
)

# Or using uv
server_params = StdioServerParameters(
    command="uv",
    args=["run", "weather_mcp_server.py"]
)

# Connect to the server
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("get_weather", {"city": "London"})
```

## API Data Sources

- **Geocoding**: https://geocoding-api.open-meteo.com/v1/search
- **Historical Weather**: https://archive-api.open-meteo.com/v1/archive

Both APIs are free and don't require authentication.

## Configuration for Claude

To use this with Claude (via MCP configuration), add to your Claude configuration file:

```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": ["run", "weather_mcp_server.py"],
      "cwd": "/path/to/weather"
    }
  }
}
```
