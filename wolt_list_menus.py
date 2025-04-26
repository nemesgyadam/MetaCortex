"""
Python script to fetch restaurant data from Wolt's discovery APIs.
These endpoints are more likely to work without authentication.
"""
import httpx
import asyncio
import json
import sys
import codecs
import unicodedata
from typing import Dict, Any, Optional, List

# Set up proper encoding for Windows terminal
sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'backslashreplace')
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'backslashreplace')


def safe_print(text):
    """
    Print text safely, handling any encoding issues with Windows terminal.
    """
    try:
        print(text)
    except UnicodeEncodeError:
        # Fall back to ASCII with replacement characters
        print(text.encode('ascii', 'replace').decode('ascii'))


async def get_restaurants_by_location(
    lat: float,
    lon: float,
    city: str = "budapest", 
    language: str = "en",
) -> Dict[str, Any]:
    """
    Get restaurants near a location using Wolt's discovery API.
    
    Args:
        lat: Latitude
        lon: Longitude
        city: City name (lowercase)
        language: Language code (ISO-639-1)
        
    Returns:
        API response as dictionary
    """
    # This is the public-facing restaurant API
    base_url = "https://restaurant-api.wolt.com"
    
    # Use the restaurants endpoint (based on our previous success)
    endpoint = "/v1/pages/restaurants"
    
    # Query parameters
    params = {
        "lat": lat,
        "lon": lon,
        "city": city,
        "language": language,
        "filters": "open"  # Only show open restaurants
    }
    
    # Basic headers that mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": language
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}


async def get_restaurant_menu(
    restaurant_slug: str,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Get restaurant menu using the consumer-facing API.
    
    Args:
        restaurant_slug: Restaurant slug from URL
        language: Language code (ISO-639-1)
        
    Returns:
        API response as dictionary
    """
    # This is the consumer-facing API
    base_url = "https://consumer-api.wolt.com"
    
    # Use the assortment endpoint (this was previously successful)
    endpoint = f"/consumer-api/consumer-assortment/v1/venues/slug/{restaurant_slug}/assortment"
    
    # Query parameters
    params = {
        "language": language
    }
    
    # Basic headers that mimic a browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": language
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}


def print_restaurant_list(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Print restaurant information from the API response.
    
    Args:
        data: API response data
        
    Returns:
        List of restaurant data
    """
    if "error" in data:
        print(f"Error: {data['error']}")
        return []
    
    # Extract sections which usually contain restaurant items
    sections = data.get("sections", [])
    
    restaurants = []
    for section in sections:
        section_title = section.get("title", "Unnamed section")
        section_items = section.get("items", [])
        
        # Skip sections with no items
        if not section_items:
            continue
        
        print(f"\nSection: {section_title} ({len(section_items)} venues)")
        
        # Extract restaurant info from items
        for i, item in enumerate(section_items[:10]):  # Limit to 10 per section
            venue = item.get("venue", {})
            if not venue:
                continue
                
            # Add to our list of restaurants
            restaurants.append(venue)
            
            # Extract restaurant info
            name = venue.get("name", "Unknown Restaurant")
            slug = venue.get("slug", "")
            short_description = venue.get("short_description", "")
            rating = venue.get("rating", {})
            rating_value = rating.get("rating", 0)
            rating_count = rating.get("count", 0)
            
            safe_print(f"\nVenue {i+1}: {name}")
            safe_print(f"  Slug: {slug}")
            if short_description:
                safe_print(f"  Description: {short_description}")
            if rating_value:
                safe_print(f"  Rating: {rating_value} ({rating_count} reviews)")
        
        if len(section_items) > 10:
            safe_print(f"\n... and {len(section_items) - 10} more venues in this section")
    
    safe_print(f"\nTotal venues found: {len(restaurants)}")
    return restaurants


def print_menu_summary(menu_data: Dict[str, Any]) -> None:
    """
    Print a summary of menu data from the API response.
    
    Args:
        menu_data: Menu data from API response
    """
    if "error" in menu_data:
        print(f"Error: {menu_data['error']}")
        return
    
    # Extract basic info
    assortment_id = menu_data.get("assortment_id", "Unknown")
    loading_strategy = menu_data.get("loading_strategy", "Unknown")
    primary_language = menu_data.get("primary_language", "Unknown")
    selected_language = menu_data.get("selected_language", "Unknown")
    
    safe_print(f"Assortment ID: {assortment_id}")
    safe_print(f"Loading Strategy: {loading_strategy}")
    safe_print(f"Primary Language: {primary_language}")
    safe_print(f"Selected Language: {selected_language}")
    
    # Display categories
    categories = menu_data.get("categories", [])
    safe_print(f"\nFound {len(categories)} menu categories")
    
    for i, category in enumerate(categories[:15]):  # Limit to 15 categories
        name = category.get("name", "Unknown Category")
        description = category.get("description", "")
        item_ids = category.get("item_ids", [])
        
        safe_print(f"\nCategory {i+1}: {name}")
        if description:
            safe_print(f"  Description: {description}")
        safe_print(f"  Items: {len(item_ids)} item IDs")
    
    if len(categories) > 15:
        safe_print(f"\n... and {len(categories) - 15} more categories")
    
    # Try to find items
    items = menu_data.get("items", [])
    safe_print(f"\nFound {len(items)} items in the items array")
    
    if len(items) > 0:
        safe_print("\nExample items:")
        for i, item in enumerate(items[:5]):  # Show first 5 items
            name = item.get("name", "Unknown Item")
            description = item.get("description", "")
            #print(item)
            
            safe_print(f"\nItem {i+1}: {name}")
            if description:
                safe_print(f"  Description: {description}")
        
        if len(items) > 5:
            safe_print(f"\n... and {len(items) - 5} more items")
    
    # Explain if items are missing
    if loading_strategy == "partial" and len(items) == 0:
        safe_print("\nNote: This menu uses a 'partial' loading strategy, which means")
        safe_print("items are loaded on-demand when a category is selected.")
        safe_print("To get actual menu items, additional API requests with proper")
        safe_print("authentication may be required for each category.")


async def main():
    """
    Main function to demonstrate the discovery API and menu retrieval.
    """
    # Budapest coordinates
    budapest_lat = 47.497912
    budapest_lon = 19.040235
    
    print("Step 1: Discovering restaurants in Budapest...")
    
    # Get restaurants in Budapest
    restaurants = await get_restaurants_by_location(
        lat=budapest_lat,
        lon=budapest_lon,
        city="budapest",
        language="en"
    )
    
    # Save the response for inspection
    with open("budapest_restaurants.json", "w", encoding="utf-8") as f:
        json.dump(restaurants, f, indent=2, ensure_ascii=False)
        print("Restaurant data saved to budapest_restaurants.json")
    
    # Print restaurant info
    restaurant_list = print_restaurant_list(restaurants)
    
    # If we found restaurants, fetch the menu for the first one
    if restaurant_list:
        # Get the first restaurant's slug
        restaurant = restaurant_list[0]
        restaurant_name = restaurant.get("name", "Unknown")
        restaurant_slug = restaurant.get("slug", "")
        
        if restaurant_slug:
            print(f"\n\nStep 2: Fetching menu for {restaurant_name} (slug: {restaurant_slug})...")
            
            # Get the restaurant menu
            menu = await get_restaurant_menu(
                restaurant_slug=restaurant_slug,
                language="en"
            )
            
            # Save the response for inspection
            with open(f"{restaurant_slug}_menu.json", "w", encoding="utf-8") as f:
                json.dump(menu, f, indent=2, ensure_ascii=False)
                print(f"Menu data saved to {restaurant_slug}_menu.json")
            
            # Print menu summary
            print_menu_summary(menu)
        else:
            print("\nNo valid restaurant slug found to fetch menu")
    else:
        print("\nNo restaurants found to fetch menu")


if __name__ == "__main__":
    asyncio.run(main())
