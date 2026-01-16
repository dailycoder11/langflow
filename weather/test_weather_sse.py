#!/usr/bin/env python3
"""
MCP Client for FastMCP SSE Server with proper initialization
"""

import httpx
import json
import asyncio


class MCPSSEClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8010"):
        self.base_url = base_url
        self.message_id = 0
        self.session_url = None
        self.initialized = False
    
    def _next_id(self):
        """Generate next message ID"""
        self.message_id += 1
        return self.message_id
    
    async def send_request(self, method: str, params: dict = None):
        """
        Send request via SSE with proper MCP protocol
        """
        url = f"{self.base_url}/sse"
        
        # Build request - include params as empty dict for MCP protocol
        request_payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params if params is not None else {}
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as sse_client:
                # Open SSE connection
                async with sse_client.stream(
                    "GET",
                    url,
                    headers={
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                    },
                ) as sse_stream:
                    if sse_stream.status_code != 200:
                        print(f"SSE connection failed: {sse_stream.status_code}")
                        return None
                    
                    print(f"Connected to SSE stream")
                    
                    # Read until we get the endpoint
                    endpoint_url = None
                    event_type = None
                    
                    async for line in sse_stream.aiter_lines():
                        if line.startswith("event: "):
                            event_type = line[7:].strip()
                        
                        elif line.startswith("data: "):
                            data = line[6:].strip()
                            
                            # Got the endpoint
                            if event_type == "endpoint":
                                endpoint_url = f"{self.base_url}{data}"
                                print(f"Got endpoint: {endpoint_url}")
                                
                                # Initialize if not already done
                                if not self.initialized and method != "initialize":
                                    print("Initializing session first...")
                                    init_payload = {
                                        "jsonrpc": "2.0",
                                        "id": self._next_id(),
                                        "method": "initialize",
                                        "params": {
                                            "protocolVersion": "2024-11-05",
                                            "capabilities": {},
                                            "clientInfo": {
                                                "name": "weather-client",
                                                "version": "1.0.0"
                                            }
                                        }
                                    }
                                    
                                    async with httpx.AsyncClient(timeout=30.0) as init_client:
                                        init_response = await init_client.post(
                                            endpoint_url,
                                            json=init_payload,
                                            headers={"Content-Type": "application/json"}
                                        )
                                        print(f"Initialize posted: {init_response.status_code}")
                                    
                                    # Wait for initialization response
                                    event_type = None
                                    continue
                                
                                # Now POST the actual message
                                async with httpx.AsyncClient(timeout=30.0) as post_client:
                                    print(f"Sending request: {json.dumps(request_payload)}")
                                    post_response = await post_client.post(
                                        endpoint_url,
                                        json=request_payload,
                                        headers={"Content-Type": "application/json"}
                                    )
                                    print(f"Message posted: {post_response.status_code}")
                                
                                # Continue reading for response
                                event_type = None
                                continue
                            
                            # Try to parse as JSON response
                            if data:
                                try:
                                    parsed = json.loads(data)
                                    
                                    # Check if this is initialization response
                                    if not self.initialized and "result" in parsed:
                                        result = parsed.get("result", {})
                                        if "capabilities" in result:
                                            self.initialized = True
                                            print("Session initialized!")
                                            
                                            # Now send the actual request
                                            async with httpx.AsyncClient(timeout=30.0) as post_client:
                                                print(f"Sending actual request: {json.dumps(request_payload)}")
                                                post_response = await post_client.post(
                                                    endpoint_url,
                                                    json=request_payload,
                                                    headers={"Content-Type": "application/json"}
                                                )
                                                print(f"Actual request posted: {post_response.status_code}")
                                            continue
                                    
                                    # Check if this is our response
                                    if "result" in parsed or "error" in parsed:
                                        print(f"Got response!")
                                        return parsed
                                        
                                except json.JSONDecodeError:
                                    pass
                    
                    return None
                    
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def list_tools(self):
        """List all available tools"""
        return await self.send_request("tools/list", {})
    
    async def call_tool(self, tool_name: str, arguments: dict):
        """Call a specific tool"""
        return await self.send_request(
            "tools/call",
            {"name": tool_name, "arguments": arguments}
        )


async def main():
    print("=" * 60)
    print("MCP SSE Client - Listing Available Tools")
    print("=" * 60)
    
    client = MCPSSEClient()
    
    print("\n1. Retrieving list of tools...")
    tools_response = await client.list_tools()
    
    if tools_response:
        print("\n" + "=" * 60)
        print("SUCCESS! Tools Retrieved")
        print("=" * 60)
        print(json.dumps(tools_response, indent=2))
        
        # Parse and display tools
        if "result" in tools_response:
            result = tools_response["result"]
            
            tools = None
            if isinstance(result, dict) and "tools" in result:
                tools = result["tools"]
            elif isinstance(result, list):
                tools = result
            
            if tools:
                print(f"\n\nFound {len(tools)} tool(s):")
                print("-" * 60)
                
                for tool in tools:
                    print(f"\nTool Name: {tool.get('name')}")
                    print(f"Description: {tool.get('description')}")
                    
                    if "inputSchema" in tool:
                        schema = tool["inputSchema"]
                        print(f"Input Schema:")
                        print(f"  Type: {schema.get('type')}")
                        
                        if "properties" in schema:
                            print(f"  Parameters:")
                            for param, details in schema["properties"].items():
                                param_type = details.get("type", "unknown")
                                param_desc = details.get("description", "No description")
                                print(f"    - {param} ({param_type}): {param_desc}")
                        
                        if "required" in schema:
                            print(f"  Required: {', '.join(schema['required'])}")
                    
                    print("-" * 60)
                
                # Try calling a tool
                print("\n\n2. Example: Calling get_weather for London...")
                weather_response = await client.call_tool("get_weather", {"city": "London"})
                
                if weather_response:
                    print("\nWeather Response:")
                    print(json.dumps(weather_response, indent=2))
    else:
        print("\n" + "=" * 60)
        print("Failed to retrieve tools")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())