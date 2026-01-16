#!/usr/bin/env python3
"""
MCP Client for Weather Server - Advanced Version with Interactive Mode
Demonstrates how to start the weather MCP server as a separate process
and interact with it using different methods (subprocess or uv)
Includes interactive mode to ask user for city and data type (past/future)
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


class WeatherMCPClient:
    """Client for connecting to and using the Weather MCP Server"""
    
    def __init__(self, use_uv: bool = False):
        """
        Initialize the client
        
        Args:
            use_uv: If True, use 'uv run' to start the server, 
                    if False, use 'python' directly
        """
        self.use_uv = use_uv
        self.server_path = Path(__file__).parent / "weather_mcp_server.py"
    
    def get_server_command(self) -> tuple[str, list[str]]:
        """
        Get the command to start the server
        
        Returns:
            Tuple of (executable, args)
        """
        if self.use_uv:
            # Using uv to run the server
            return "uv", ["run", str(self.server_path)]
        else:
            # Using Python directly
            return sys.executable, [str(self.server_path)]
    
    async def test_weather(self, city: str, data_type: str) -> bool:
        """
        Connect to the weather MCP server and fetch weather data
        
        Args:
            city: Name of the city to get weather for
            data_type: Either 'past' for historical data or 'future' for forecast
            
        Returns:
            True if successful, False otherwise
        """
        executable, args = self.get_server_command()
        
        # Determine which tool to call
        tool_name = "get_weather" if data_type.lower() == "past" else "get_forecast"
        data_label = "PAST 7 DAYS" if data_type.lower() == "past" else "NEXT 7 DAYS"
        
        try:
            # Create server parameters
            server_params = StdioServerParameters(
                command=executable,
                args=args
            )
            
            # Connect and run
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize the connection
                    await session.initialize()
                    
                    # List available tools
                    tools = await session.list_tools()
                    print("\n" + "="*60)
                    print("📋 Available Tools:")
                    print("="*60)
                    for tool in tools.tools:
                        print(f"  • {tool.name}: {tool.description}")
                    
                    print("\n" + "="*60)
                    print(f"🌤️  Fetching weather ({data_label}) for: {city}")
                    print("="*60)
                    
                    # Call the appropriate tool
                    result = await session.call_tool(tool_name, {"city": city})
                    
                    # Display the result
                    for content in result.content:
                        print(content.text)
                    
                    print("="*60 + "\n")
                    return True
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def get_user_input() -> tuple[str, str, bool]:
    """
    Interactively ask user for city, data type, and method
    
    Returns:
        Tuple of (city, data_type, use_uv)
    """
    print("\n" + "="*60)
    print("🌍 Weather Data Query Tool")
    print("="*60)
    
    # Get city name
    while True:
        city = input("\n📍 Enter city name (e.g., London, Paris, Tokyo): ").strip()
        if city:
            break
        print("⚠️  Please enter a valid city name")
    
    # Get data type
    while True:
        print("\n📅 What type of data do you need?")
        print("  1) Past weather data (last 7 days)")
        print("  2) Future forecast (next 7 days)")
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            data_type = "past"
            break
        elif choice == "2":
            data_type = "future"
            break
        else:
            print("⚠️  Please enter 1 or 2")
    
    # Get execution method
    print("\n🔧 How should the server be started?")
    print("  1) Using Python (python)")
    print("  2) Using UV (uv run)")
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        
        if choice == "1":
            use_uv = False
            method = "python"
            break
        elif choice == "2":
            use_uv = True
            method = "uv run"
            break
        else:
            print("⚠️  Please enter 1 or 2")
    
    print(f"\n✓ Selected: {city} | {data_type.upper()} | {method}\n")
    return city, data_type, use_uv


async def main():
    """
    Main test function - support both interactive and command-line modes
    """
    # Check if running in interactive or command-line mode
    if len(sys.argv) > 1:
        # Command-line mode
        use_uv = "--uv" in sys.argv
        cities = [arg for arg in sys.argv[1:] if arg != "--uv"]
        
        if not cities:
            # No cities provided, use defaults
            test_data = [
                ("London", "past"),
                ("Paris", "future"),
                ("Tokyo", "past")
            ]
        else:
            # Mix of past and future for provided cities
            test_data = [(city, "past" if i % 2 == 0 else "future") for i, city in enumerate(cities)]
        
        # Show which method we're using
        method = "uv run" if use_uv else "python"
        print(f"\n🔧 Using '{method}' to start the MCP server\n")
        
        # Create client and test
        client = WeatherMCPClient(use_uv=use_uv)
        for city, data_type in test_data:
            await client.test_weather(city, data_type)
    else:
        # Interactive mode
        city, data_type, use_uv = get_user_input()
        
        # Create client and test
        client = WeatherMCPClient(use_uv=use_uv)
        success = await client.test_weather(city, data_type)
        
        if not success:
            print(f"Failed to get weather data for {city}")
        
        # Ask if user wants to query another city
        while True:
            again = input("\n🔄 Would you like to query another city? (yes/no): ").strip().lower()
            if again in ["yes", "y"]:
                city, data_type, use_uv = get_user_input()
                client = WeatherMCPClient(use_uv=use_uv)
                await client.test_weather(city, data_type)
            elif again in ["no", "n"]:
                print("\n👋 Thank you for using Weather Query Tool!\n")
                break
            else:
                print("⚠️  Please enter 'yes' or 'no'")


if __name__ == "__main__":
    asyncio.run(main())
