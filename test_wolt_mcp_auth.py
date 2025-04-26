"""
Test script for Wolt MCP endpoints with authentication
"""
import asyncio
import sys
import logging
import os
from typing import Optional

# Set up the path to include meta_cortex for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = SCRIPT_DIR  # Already at project root
sys.path.append(ROOT_DIR)

from meta_cortex.client_manager import ClientManager

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("test_wolt_mcp")

# Authentication values from direct_wolt_basket.py
AUTH_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjY4MDMzZDU2MDAwMDAwMDAwMDAwMDAwMCIsInR5cCI6IngudXNlcitqd3QifQ.eyJhdWQiOlsid29sdC1jb20iLCJkYWFzLXB1YmxpYy1hcGkiLCJnaWZ0LWNhcmQtc2hvcCIsImNvdXJpZXJjbGllbnQiLCJwYXltZW50cy10aXBzLXNlcnZpY2UiLCJyZXR1cm5zLWFwaSIsIndscy1jdXN0b21lci1zZXJ2aWNlIiwic3Vic2NyaXB0aW9uLXNlcnZpY2UiLCJvcmRlci10cmFja2luZyIsImxveWFsdHktcHJvZ3JhbS1hcGkiLCJjb25zdW1lci1hc3NvcnRtZW50IiwicGF5bWVudC1zZXJ2aWNlIiwicmVzdGF1cmFudC1hcGkiLCJvcmRlci14cCIsInZlbnVlLWNvbnRlbnQtYXBpIiwiaW50ZWdyYXRpb24tY29uZmlnLXNlcnZpY2UiLCJhY3Rpdml0eS1odWIiLCJlLXdhbGxldC1zZXJ2aWNlIiwid29sdGF1dGgiLCJhZC1pbnNpZ2h0cyIsImNvcnBvcmF0ZS1wb3J0YWwtYXBpIiwiZGlmZnVzaW9uIiwidG9wdXAtc2VydmljZSIsImxveWFsdHktZ2F0ZXdheSIsImNvbnZlcnNlLXdpZGdldC1jb25zdW1lciIsInN1cHBvcnQtZnVubmVsIiwibWVhbC1iZW5lZml0cy1zZXJ2aWNlIl0sImlzcyI6IndvbHRhdXRoIiwianRpIjoiYzFjZTFhMzIyMjdkMTFmMDk5N2QzNjc3Y2FhZWY0YzYiLCJ1c2VyIjp7ImlkIjoiNWU4YjI4YWFkY2UyY2RiODY0MmIzNTNkIiwibmFtZSI6eyJmaXJzdF9uYW1lIjoiTmVtZXMiLCJsYXN0X25hbWUiOiJcdTAwYzFkXHUwMGUxbSJ9LCJlbWFpbCI6Im5lbWVzZ3lhZGFtQGdtYWlsLmNvbSIsInJvbGVzIjpbInVzZXIiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX251bWJlcl92ZXJpZmllZCI6dHJ1ZSwiY291bnRyeSI6IkhVTiIsImxhbmd1YWdlIjoiaHUiLCJwcm9maWxlX3BpY3R1cmUiOnsidXJsIjoiaHR0cHM6Ly9jcmVkaXRvcm5vdG1lZGlhLnMzLmFtYXpvbmF3cy5jb20vZTFhYzQ3YmNmM2Q4ZTc0Y2JmMGI0NjAxZjA4MjFmODZmOWRlYzMyYjNmOTQxZWJmNzFkMWQ4Y2QwZGYxNDQ5YzNlNDdlODJlZDA4MDRlMTc0NmRlNjZhNjBkYmRmODUxYjQwNDliMDRhNWZmZGNkOGExN2MzMWQ3NTg3ODUzMGEifSwicGVybWlzc2lvbnMiOltdLCJwaG9uZV9udW1iZXIiOiIrMzYzMDYwMjY4MTgiLCJ0ZW5hbnQiOiJ3b2x0In0sImlhdCI6MTc0NTY1ODM5NiwiZXhwIjoxNzQ1NjYwMTk2LCJhbXIiOltdfQ.7Olph0-f2Kl_9AoOropZU2lAFh_p6MXZcsDS90hFbxQwg2VhUw9v6K9kIxO4aU85QFbW9tbbNPOfguTlojnMNQ"
SESSION_ID = "179840a8-0dab-4998-8f37-1c4c83547dae"

# Test parameters
VENUE_SLUG = "pizza-me-palma"  # Example venue 
VENUE_ID = "617bd8b17317edf628e3dd26"  # From direct_wolt_basket.py

async def run_tests():
    """Run a series of tests for Wolt MCP endpoints"""
    log.info("Starting Wolt MCP authentication tests")
    
    # Initialize ClientManager
    cm = ClientManager()
    await cm.initialize()
    
    # 1. Test listing venues
    log.info("\n=== Testing venue list API ===")
    try:
        response = await cm.call_tool("wolt", "wolt_venue_list", {
            "location_code": "budapest", 
            "open_now": True,
            "auth_token": AUTH_TOKEN,
            "session_id": SESSION_ID
        })
        if "error" in response:
            log.error(f"Venue list error: {response['error']}")
        else:
            log.info(f"Venue list success! Found {len(response.get('sections', []))} sections")
    except Exception as e:
        log.error(f"Venue list exception: {e}")
    
    # 2. Test venue menu
    log.info("\n=== Testing venue menu API ===")
    try:
        response = await cm.call_tool("wolt", "wolt_venue_menu", {
            "slug": VENUE_SLUG,
            "auth_token": AUTH_TOKEN,
            "session_id": SESSION_ID
        })
        if "error" in response:
            log.error(f"Venue menu error: {response['error']}")
        else:
            log.info(f"Venue menu success! Found {len(response.get('items', []))} menu items")
            # Extract an item ID for basket test
            items = response.get("items", [])
            item_id = items[0]["id"] if items else None
            if item_id:
                log.info(f"Found menu item ID: {item_id}")
                return item_id
    except Exception as e:
        log.error(f"Venue menu exception: {e}")
    
    return None

async def test_basket(item_id: Optional[str] = None):
    """Test basket creation with the extracted item ID"""
    if not item_id:
        log.warning("No item ID provided, using default from direct_wolt_basket.py")
        item_id = "0edff4489301896552b7fb23"  # Default from direct_wolt_basket.py
    
    log.info("\n=== Testing basket creation ===")
    
    # Initialize ClientManager
    cm = ClientManager()
    await cm.initialize()
    
    try:
        # Create a basket with the item
        response = await cm.call_tool("wolt", "wolt_create_basket", {
            "venue_id": VENUE_ID,
            "items": [
                {
                    "id": item_id,
                    "quantity": 1,
                    "price": 95000  # Price in smallest currency unit
                }
            ],
            "currency": "HUF",
            "auth_token": AUTH_TOKEN,
            "session_id": SESSION_ID
        })
        
        if "error" in response:
            log.error(f"Basket creation error: {response['error']}")
        else:
            basket_id = response.get("id")
            log.info(f"Basket created successfully! Basket ID: {basket_id}")
            
            # Test getting the basket
            if basket_id:
                log.info("\n=== Testing get basket ===")
                basket_response = await cm.call_tool("wolt", "wolt_get_basket", {
                    "basket_id": basket_id,
                    "auth_token": AUTH_TOKEN,
                    "session_id": SESSION_ID
                })
                
                if "error" in basket_response:
                    log.error(f"Get basket error: {basket_response['error']}")
                else:
                    log.info(f"Get basket success! Items: {len(basket_response.get('items', []))}")
                    
                # Test basket count
                log.info("\n=== Testing basket count ===")
                count_response = await cm.call_tool("wolt", "wolt_basket_count", {
                    "auth_token": AUTH_TOKEN,
                    "session_id": SESSION_ID
                })
                
                if "error" in count_response:
                    log.error(f"Basket count error: {count_response['error']}")
                else:
                    log.info(f"Basket count success! Count: {count_response.get('count', 0)}")
    except Exception as e:
        log.error(f"Basket test exception: {e}")

async def test_past_orders():
    """Test fetching past orders"""
    log.info("\n=== Testing past orders API ===")
    
    # Initialize ClientManager
    cm = ClientManager()
    await cm.initialize()
    
    try:
        response = await cm.call_tool("wolt", "wolt_past_orders", {
            "auth_token": AUTH_TOKEN,
            "session_id": SESSION_ID
        })
        
        if "error" in response:
            log.error(f"Past orders error: {response['error']}")
        else:
            orders = response.get("data", {}).get("orders", [])
            log.info(f"Past orders success! Found {len(orders)} past orders")
    except Exception as e:
        log.error(f"Past orders exception: {e}")

async def main():
    """Main test function"""
    try:
        # Run venue tests and get an item ID
        item_id = await run_tests()
        
        # Test basket functionality
        await test_basket(item_id)
        
        # Test past orders
        await test_past_orders()
        
        log.info("All tests completed!")
    except Exception as e:
        log.error(f"Test failed with exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
