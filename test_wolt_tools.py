"""
Test script for Wolt MCP tools
Lists all available tools and tries to access them
"""
import asyncio
import json
import os
import sys
from typing import Dict, Any, List

# Add the meta_cortex directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'meta_cortex'))
from client_manager import ClientManager


async def test_wolt_tools():
    """
    Test the Wolt MCP tools by listing all available tools and trying to access them.
    """
    # Initialize the client manager with verbose output
    manager = ClientManager(verbose=True)
    
    try:
        # Start the manager (load config, create and connect clients)
        await manager.start()
        
        # Get all available server names
        server_names = manager.get_server_names()
        print(f"Available servers: {server_names}")
        
        # Check if Wolt server is available
        if "wolt" not in server_names:
            print("Wolt server is not available in the configuration")
            return
        
        # Get all tools from the Wolt server
        client = manager.connected_clients.get("wolt")
        if not client:
            print("Wolt client is not connected")
            return
            
        # Get all tools from the Wolt server
        wolt_tools = client.get_tools() if hasattr(client, 'get_tools') else {}
        
        if not wolt_tools:
            print("No tools available from Wolt server")
            return
            
        print("\n" + "="*50)
        print("AVAILABLE WOLT TOOLS:")
        print("="*50)
        
        # Print all available tools with their descriptions
        for tool_name, (_, description) in wolt_tools.items():
            print(f"Tool: {tool_name}")
            print(f"Description: {description}")
            print("-"*50)
        
        # Test each tool with appropriate parameters
        print("\n" + "="*50)
        print("TESTING WOLT TOOLS:")
        print("="*50)
        
        # Common authentication parameters
        auth_token = None  # Leave as None for public endpoints, replace with real token for auth-required endpoints
        language = "en"
        
        # List of tools to test with real values from network traffic
        tools_to_test = [
            ("list_italian_restaurants", {
                "lat": 47.4775359,  # Budapest coordinates from traffic data
                "lon": 19.0459652,
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_venue_list", {
                "location_code": "budapest",  # Using Budapest location from traffic
                "lat": 47.4775359, 
                "lon": 19.0459652,
                "open_now": True,
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_venue_profile", {
                "slug": "pirog-delikatesz",  # Pirog Delikatesz slug from browser URL
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_venue_menu", {
                "slug": "pirog-delikatesz",  # Pirog Delikatesz slug from browser URL
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_menu_items", {
                "slug": "pirog-delikatesz",  # Pirog Delikatesz slug from browser URL
                "item_ids": ["6182726817ad8c76127a70e0"],  # Example item ID 
                "auth_token": auth_token,
                "language": language
            }),
            # The following endpoints require authentication
            ("wolt_create_basket", {
                "venue_id": "617bd8b17317edf628e3dd26",  # Pirog Delikatesz venue ID
                "items": [{
                    "id": "6182726817ad8c76127a70e0",  # Item ID from traffic data
                    "quantity": 1
                }],
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_get_basket", {
                "basket_id": "680bdf60f639c8b68f085ef0",  # Example basket ID
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_basket_count", {
                "auth_token": auth_token,
                "language": language
            }),
            # Never run checkout during development/testing!
            ("wolt_checkout", {
                "purchase_plan": {
                    "basket_id": "680bdf60f639c8b68f085ef0",
                    "dev_mode": True  # Safety flag to prevent actual orders
                },
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_past_orders", {
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_geocode_address", {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",  # Example Google Place ID
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_order_tracking", {
                "order_id": "680bdf60f639c8b68f085ef0",  # Example order ID
                "auth_token": auth_token,
                "language": language
            }),
            ("wolt_bulk_delete_baskets", {
                "ids": ["680bdf60f639c8b68f085ef0"],  # Example basket ID
                "auth_token": auth_token,
                "language": language
            })
        ]
        
        # Test each tool
        for tool_name, params in tools_to_test:
            print(f"\nTesting tool: {tool_name}")
            print(f"Parameters: {json.dumps(params, indent=2)}")
            
            try:
                result = await manager.call_tool("wolt", tool_name, params)
                print(f"Response status: {'Success' if 'error' not in result else 'Error'}")
                print(f"Result: {json.dumps(result, indent=2)[:500]}..." if len(json.dumps(result)) > 500 else f"Result: {json.dumps(result, indent=2)}")
            except Exception as e:
                print(f"Error calling tool {tool_name}: {str(e)}")
            
            print("-"*50)
            
    except Exception as e:
        print(f"Error in test_wolt_tools: {str(e)}")
    finally:
        # Clean up resources
        try:
            await asyncio.shield(manager.close_all_clients())
            print("Successfully closed all clients")
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")


if __name__ == "__main__":
    asyncio.run(test_wolt_tools())
