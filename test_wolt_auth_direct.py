"""
Direct test for Wolt MCP endpoints with authentication
This script directly tests the wolt.py module's authentication without using ClientManager
"""
import asyncio
import sys
import logging
import json
import os
from typing import Dict, Any, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from wolt.wolt import (
    get_auth_headers,
    wolt_venue_list,
    wolt_venue_menu,
    wolt_venue_profile,
    wolt_create_basket,
    wolt_get_basket,
    wolt_basket_count,
    wolt_past_orders
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("test_wolt_auth")

# Authentication values from direct_wolt_basket.py
AUTH_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjY4MDMzZDU2MDAwMDAwMDAwMDAwMDAwMCIsInR5cCI6IngudXNlcitqd3QifQ.eyJhdWQiOlsid29sdC1jb20iLCJkYWFzLXB1YmxpYy1hcGkiLCJnaWZ0LWNhcmQtc2hvcCIsImNvdXJpZXJjbGllbnQiLCJwYXltZW50cy10aXBzLXNlcnZpY2UiLCJyZXR1cm5zLWFwaSIsIndscy1jdXN0b21lci1zZXJ2aWNlIiwic3Vic2NyaXB0aW9uLXNlcnZpY2UiLCJvcmRlci10cmFja2luZyIsImxveWFsdHktcHJvZ3JhbS1hcGkiLCJjb25zdW1lci1hc3NvcnRtZW50IiwicGF5bWVudC1zZXJ2aWNlIiwicmVzdGF1cmFudC1hcGkiLCJvcmRlci14cCIsInZlbnVlLWNvbnRlbnQtYXBpIiwiaW50ZWdyYXRpb24tY29uZmlnLXNlcnZpY2UiLCJhY3Rpdml0eS1odWIiLCJlLXdhbGxldC1zZXJ2aWNlIiwid29sdGF1dGgiLCJhZC1pbnNpZ2h0cyIsImNvcnBvcmF0ZS1wb3J0YWwtYXBpIiwiZGlmZnVzaW9uIiwidG9wdXAtc2VydmljZSIsImxveWFsdHktZ2F0ZXdheSIsImNvbnZlcnNlLXdpZGdldC1jb25zdW1lciIsInN1cHBvcnQtZnVubmVsIiwibWVhbC1iZW5lZml0cy1zZXJ2aWNlIl0sImlzcyI6IndvbHRhdXRoIiwianRpIjoiYzFjZTFhMzIyMjdkMTFmMDk5N2QzNjc3Y2FhZWY0YzYiLCJ1c2VyIjp7ImlkIjoiNWU4YjI4YWFkY2UyY2RiODY0MmIzNTNkIiwibmFtZSI6eyJmaXJzdF9uYW1lIjoiTmVtZXMiLCJsYXN0X25hbWUiOiJcdTAwYzFkXHUwMGUxbSJ9LCJlbWFpbCI6Im5lbWVzZ3lhZGFtQGdtYWlsLmNvbSIsInJvbGVzIjpbInVzZXIiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX251bWJlcl92ZXJpZmllZCI6dHJ1ZSwiY291bnRyeSI6IkhVTiIsImxhbmd1YWdlIjoiaHUiLCJwcm9maWxlX3BpY3R1cmUiOnsidXJsIjoiaHR0cHM6Ly9jcmVkaXRvcm5vdG1lZGlhLnMzLmFtYXpvbmF3cy5jb20vZTFhYzQ3YmNmM2Q4ZTc0Y2JmMGI0NjAxZjA4MjFmODZmOWRlYzMyYjNmOTQxZWJmNzFkMWQ4Y2QwZGYxNDQ5YzNlNDdlODJlZDA4MDRlMTc0NmRlNjZhNjBkYmRmODUxYjQwNDliMDRhNWZmZGNkOGExN2MzMWQ3NTg3ODUzMGEifSwicGVybWlzc2lvbnMiOltdLCJwaG9uZV9udW1iZXIiOiIrMzYzMDYwMjY4MTgiLCJ0ZW5hbnQiOiJ3b2x0In0sImlhdCI6MTc0NTY1ODM5NiwiZXhwIjoxNzQ1NjYwMTk2LCJhbXIiOltdfQ.7Olph0-f2Kl_9AoOropZU2lAFh_p6MXZcsDS90hFbxQwg2VhUw9v6K9kIxO4aU85QFbW9tbbNPOfguTlojnMNQ"
SESSION_ID = "179840a8-0dab-4998-8f37-1c4c83547dae"

# Test parameters - using exactly the same values that worked in direct_wolt_basket.py
VENUE_ID = "617bd8b17317edf628e3dd26"  # From direct_wolt_basket.py
DEFAULT_ITEM_ID = "0edff4489301896552b7fb23"  # Default item ID from direct_wolt_basket.py
ITEM_PRICE = 95000  # Price in smallest currency unit from direct_wolt_basket.py


async def test_venue_list() -> bool:
    """Test venue listing in Budapest"""
    log.info("\n=== Testing venue list API ===")
    try:
        response = await wolt_venue_list(
            location_code="budapest", 
            open_now=True,
            auth_token=AUTH_TOKEN,
            session_id=SESSION_ID
        )
        
        if "error" in response:
            log.error(f"Venue list error: {response['error']}")
            return False
        else:
            sections = response.get("sections", [])
            log.info(f"Venue list success! Found {len(sections)} sections")
            return True
    except Exception as e:
        log.error(f"Venue list exception: {e}")
        return False


async def test_venue_menu(venue_slug: str) -> tuple[bool, Optional[str]]:
    """Test venue menu for a specific restaurant"""
    log.info("\n=== Testing venue menu API ===")
    item_id = None
    
    if not venue_slug:
        log.warning("No venue slug provided, cannot test venue menu")
        return False, None
    
    try:
        response = await wolt_venue_menu(
            slug=venue_slug,
            auth_token=AUTH_TOKEN,
            session_id=SESSION_ID
        )
        
        if "error" in response:
            log.error(f"Venue menu error: {response['error']}")
            return False, None
        else:
            items = response.get("items", [])
            log.info(f"Venue menu success! Found {len(items)} menu items")
            
            # Get the first item ID for basket tests
            if items:
                item_id = items[0]["id"]
                log.info(f"Found menu item ID: {item_id}")
            
            return True, item_id
    except Exception as e:
        log.error(f"Venue menu exception: {e}")
        return False, None


async def test_venue_list_with_id() -> tuple[bool, str]:
    """Test venue listing with a specific venue ID to get the proper slug"""
    log.info("\n=== Testing venue list with venue ID to get slug ===")
    try:
        # First get a list of venues
        response = await wolt_venue_list(
            location_code="budapest", 
            auth_token=AUTH_TOKEN,
            session_id=SESSION_ID
        )
        
        if "error" in response:
            log.error(f"Venue list error: {response['error']}")
            return False, ""
        
        # Try to find venue based on venue ID
        venue_slug = ""
        if "sections" in response:
            for section in response.get("sections", []):
                for item in section.get("items", []):
                    if "venue" in item and item["venue"].get("id") == VENUE_ID:
                        venue_slug = item["venue"].get("slug", "")
                        venue_name = item["venue"].get("name", "unknown")
                        log.info(f"Found venue: {venue_name} with slug: {venue_slug}")
                        return True, venue_slug
        
        log.warning(f"Could not find venue with ID {VENUE_ID} in the venue list response")
        return False, ""
    except Exception as e:
        log.error(f"Venue list with ID exception: {e}")
        return False, ""


async def test_basket(item_id: Optional[str] = None) -> bool:
    """Test basket creation and retrieval"""
    if not item_id:
        log.warning("No item ID provided, using default from direct_wolt_basket.py")
        item_id = DEFAULT_ITEM_ID
    
    log.info("\n=== Testing basket creation ===")
    
    try:
        # Create a basket with the item - exactly matching the format from direct_wolt_basket.py
        response = await wolt_create_basket(
            venue_id=VENUE_ID,
            items=[
                {
                    "id": item_id,
                    "quantity": 1,
                    "price": ITEM_PRICE  # Include price exactly as in direct_wolt_basket.py
                }
            ],
            currency="HUF",
            auth_token=AUTH_TOKEN,
            session_id=SESSION_ID
        )
        
        if "error" in response:
            log.error(f"Basket creation error: {response['error']}")
            return False
        else:
            basket_id = response.get("id")
            log.info(f"Basket created successfully! Basket ID: {basket_id}")
            
            # Test getting the basket
            if basket_id:
                log.info("\n=== Testing get basket ===")
                basket_response = await wolt_get_basket(
                    basket_id=basket_id,
                    auth_token=AUTH_TOKEN,
                    session_id=SESSION_ID
                )
                
                if "error" in basket_response:
                    log.error(f"Get basket error: {basket_response['error']}")
                    return False
                else:
                    log.info(f"Get basket success! Items: {len(basket_response.get('items', []))}")
                    
                # Test basket count
                log.info("\n=== Testing basket count ===")
                count_response = await wolt_basket_count(
                    auth_token=AUTH_TOKEN,
                    session_id=SESSION_ID
                )
                
                if "error" in count_response:
                    log.error(f"Basket count error: {count_response['error']}")
                    return False
                else:
                    log.info(f"Basket count success! Count: {count_response.get('count', 0)}")
                    return True
    except Exception as e:
        log.error(f"Basket test exception: {e}")
        return False
    
    return False


async def test_past_orders() -> bool:
    """Test fetching past orders"""
    log.info("\n=== Testing past orders API ===")
    
    try:
        response = await wolt_past_orders(
            auth_token=AUTH_TOKEN,
            session_id=SESSION_ID
        )
        
        if "error" in response:
            log.error(f"Past orders error: {response['error']}")
            return False
        else:
            orders = response.get("data", {}).get("orders", [])
            log.info(f"Past orders success! Found {len(orders)} past orders")
            return True
    except Exception as e:
        log.error(f"Past orders exception: {e}")
        return False


async def main():
    """Main test function"""
    success_count = 0
    total_tests = 4  # Total number of tests we're running
    
    try:
        # Test venue listing
        if await test_venue_list():
            success_count += 1
        
        # Get venue slug from the venue list
        venue_list_success, venue_slug = await test_venue_list_with_id()
        if venue_list_success:
            # Test venue menu and get an item ID
            success, item_id = await test_venue_menu(venue_slug)
            if success:
                success_count += 1
            
            # Test basket functionality
            if await test_basket(item_id):
                success_count += 1
        else:
            # Fall back to testing with default item ID if venue isn't found
            log.info("Testing basket with default item ID")
            if await test_basket(None):
                success_count += 1
        
        # Test past orders
        if await test_past_orders():
            success_count += 1
            
        # Report results
        log.info("\n=== Testing complete ===")
        log.info(f"Passed {success_count}/{total_tests} tests")
        
        if success_count == total_tests:
            log.info("✅ All tests passed! Authentication is working properly.")
        else:
            log.warning(f"⚠️ {total_tests - success_count} tests failed. Check the logs for details.")
        
    except Exception as e:
        log.error(f"Test suite failed with exception: {e}")


if __name__ == "__main__":
    asyncio.run(main())
