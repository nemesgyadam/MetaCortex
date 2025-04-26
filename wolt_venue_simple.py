"""
Simple script to directly call the Wolt venue listing API without authentication.
"""
import asyncio
import httpx
import json
from typing import Dict, Any, Optional

# Helper function for safe printing on Windows
def safe_print(text):
    """Print text safely on Windows with unicode characters."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fall back to cp1252 (Windows default) encoding
        print(text.encode('cp1252', errors='replace').decode('cp1252'))

async def get_wolt_venues(
    lat: float,
    lon: float,
    language: str = "en",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get a list of Wolt venues near the specified coordinates.
    
    Args:
        lat: Latitude 
        lon: Longitude
        language: Language code
        session_id: Optional session ID for authentication
    
    Returns:
        Response from the Wolt API
    """
    # API endpoint for venue discovery
    base_url = "https://restaurant-api.wolt.com"
    endpoint = "/v1/pages/restaurants"
    params = {
        "lat": lat,
        "lon": lon,
        "filters": "open"  # Only show open restaurants
    }
    
    url = f"{base_url}{endpoint}"
    
    # Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": language,
        "X-Client-Id": "web"
    }
    
    # Add session ID if provided
    if session_id:
        headers["X-Session-Id"] = session_id
    
    print(f"Making request to {url}")
    print(f"Parameters: {params}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Error getting venues: {e}")
        return {"error": str(e)}


async def get_venue_menu(
    venue_slug: str,
    language: str = "en",
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get the menu for a specific venue using its slug.
    
    Args:
        venue_slug: The venue slug (from URL)
        language: Language code 
        session_id: Optional session ID for authentication
    
    Returns:
        Response from the Wolt API
    """
    # API endpoint
    base_url = "https://consumer-api.wolt.com"
    endpoint = f"/consumer-api/consumer-assortment/v1/venues/slug/{venue_slug}/assortment"
    params = {
        "loading_strategy": "full"  # Get full menu with all items
    }
    
    url = f"{base_url}{endpoint}"
    
    # Headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": language,
        "X-Client-Id": "web"
    }
    
    # Add session ID if provided
    if session_id:
        headers["X-Session-Id"] = session_id
    
    print(f"Making request to {url}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Error getting menu: {e}")
        return {"error": str(e)}


async def main():
    # Budapest coordinates
    lat = 47.4775359
    lon = 19.0459652
    
    # Your session ID (optional for these endpoints)
    session_id = "179840a8-0dab-4998-8f37-1c4c83547dae"
    
    # Choose which action to perform
    action = "menu"  # Options: "venues" or "menu"
    
    if action == "venues":
        print(f"Getting venues near Budapest ({lat}, {lon})...")
        result = await get_wolt_venues(lat, lon, session_id=session_id)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            # Process venue results
            sections = result.get("sections", [])
            venue_count = 0
            
            for section in sections:
                items = section.get("items", [])
                for item in items:
                    venue = item.get("venue", {})
                    if not venue:
                        # Try alternative structure for some API responses
                        track = item.get("track", {})
                        if track:
                            venue = track.get("venue", {})
                    
                    venue_count += 1
                    if venue_count <= 5:  # Show first 5 venues
                        name = venue.get("name", "Unknown")
                        delivery_price = venue.get("delivery_price", 0) / 100
                        safe_print(f"\n{venue_count}. {name}")
                        safe_print(f"   Delivery: {delivery_price} {venue.get('currency', 'HUF')}")
                        safe_print(f"   Slug: {venue.get('slug', 'N/A')}")
                        safe_print(f"   ID: {venue.get('id', 'N/A')}")
                        
                        # Show food categories if available
                        categories = venue.get("categories", [])
                        if categories:
                            cat_names = [cat.get("name", "?") for cat in categories[:3]]
                            safe_print(f"   Categories: {', '.join(cat_names)}")
            
            print(f"\nFound {venue_count} venues in total")
            
    elif action == "menu":
        # Get menu for a specific venue (McDonald's in this example)
        venue_slug = "pirog-delikatesz"  # Using the restaurant from earlier example
        print(f"Getting menu for {venue_slug}...")
        
        menu_result = await get_venue_menu(venue_slug, session_id=session_id)
        
        if "error" in menu_result:
            print(f"Error: {menu_result['error']}")
        else:
            # Process menu results
            categories = menu_result.get("categories", [])
            items = menu_result.get("items", [])
            
            print(f"\nFound {len(categories)} categories and {len(items)} items")
            
            # Print first few categories
            for i, category in enumerate(categories[:5]):
                name = category.get("name", "Unknown Category")
                item_count = len(category.get("item_ids", []))
                safe_print(f"\nCategory {i+1}: {name} ({item_count} items)")
            
            # Print first few items
            if items:
                print("\nSample items:")
                for i, item in enumerate(items[:3]):
                    name = item.get("name", "Unknown Item")
                    price = item.get("price", 0) / 100
                    safe_print(f"Item {i+1}: {name} - {price} {menu_result.get('currency', 'HUF')}")
                    safe_print(f"  ID: {item.get('id', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
