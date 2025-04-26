"""
Specialized Python script to fetch products from Wolt API using various endpoint strategies.
"""
import httpx
import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple


async def fetch_products_by_id(
    venue_id: str,
    language: str = "en",
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Try to fetch products directly using the venue ID instead of slug.
    
    Args:
        venue_id: Venue ID (not the slug)
        language: Language code (ISO-639-1)
        auth_token: Wolt auth token (optional)
        
    Returns:
        API response as a dictionary
    """
    # Base URL for Wolt API
    base_url = "https://restaurant-api.wolt.com"
    
    # Endpoint for venue products
    endpoint = f"/v3/venues/{venue_id}/menu"
    
    # Query parameters
    params = {
        "lang": language
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Platform": "Web"
    }
    
    # Add auth token if provided
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
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


async def fetch_venue_details(
    venue_slug: str,
    language: str = "en",
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch venue details to extract venue ID and other useful information.
    
    Args:
        venue_slug: Venue slug from URL
        language: Language code (ISO-639-1)
        auth_token: Wolt auth token (optional)
        
    Returns:
        API response with venue details
    """
    # Base URL for Wolt API
    base_url = "https://restaurant-api.wolt.com"
    
    # Endpoint for venue details
    endpoint = f"/v1/pages/venues/{venue_slug}"
    
    # Query parameters
    params = {
        "lang": language
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Platform": "Web"
    }
    
    # Add auth token if provided
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
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


async def fetch_popular_items(
    venue_slug: str,
    language: str = "en",
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Try to fetch popular items which might be available without authentication.
    
    Args:
        venue_slug: Venue slug from URL
        language: Language code (ISO-639-1)
        auth_token: Wolt auth token (optional)
        
    Returns:
        API response with popular items if available
    """
    # Base URL for Wolt API
    base_url = "https://restaurant-api.wolt.com"
    
    # Endpoint for popular items
    endpoint = f"/v1/pages/venue/{venue_slug}"
    
    # Query parameters
    params = {
        "lang": language
    }
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Platform": "Web"
    }
    
    # Add auth token if provided
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
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


def extract_venue_id(venue_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract venue ID from venue data response.
    
    Args:
        venue_data: Venue data from API response
        
    Returns:
        Venue ID if found, None otherwise
    """
    # Try to find venue ID in different locations in the response
    if "venue" in venue_data:
        venue = venue_data.get("venue", {})
        return venue.get("id")
    
    # Try other possible locations
    if "id" in venue_data:
        return venue_data.get("id")
    
    # If we have sections, look for venue info
    if "sections" in venue_data:
        for section in venue_data.get("sections", []):
            if "venue" in section:
                return section.get("venue", {}).get("id")
    
    return None


def extract_items_from_response(response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract items from various response structures.
    
    Args:
        response_data: API response data
        
    Returns:
        List of extracted items
    """
    items = []
    
    # Check for direct items array
    if "items" in response_data:
        items.extend(response_data.get("items", []))
    
    # Check for items in sections
    if "sections" in response_data:
        for section in response_data.get("sections", []):
            section_items = section.get("items", [])
            items.extend(section_items)
    
    # Check for popular items section
    if "popular_items" in response_data:
        items.extend(response_data.get("popular_items", []))
    
    # Check for menu items in categories
    if "menu" in response_data:
        menu = response_data.get("menu", {})
        categories = menu.get("categories", [])
        for category in categories:
            category_items = category.get("items", [])
            items.extend(category_items)
    
    return items


def print_items(items: List[Dict[str, Any]]) -> None:
    """
    Print item details in a structured format.
    
    Args:
        items: List of item data dictionaries
    """
    if not items:
        print("No items found")
        return
    
    print(f"\nFound {len(items)} items:")
    
    for i, item in enumerate(items[:20]):  # Limit to 20 items for display
        # Extract item data, handle various structures
        item_data = item
        if "item" in item:
            item_data = item.get("item", {})
        elif "product" in item:
            item_data = item.get("product", {})
        
        # Extract name
        name = item_data.get("name", "Unknown Item")
        
        # Extract description
        description = item_data.get("description", "")
        
        # Extract price - handle different price structures
        price = 0
        currency = "EUR"
        price_info = None
        
        if "price" in item_data:
            price_info = item_data.get("price")
        elif "base_price" in item_data:
            price_info = item_data.get("base_price")
        elif "baseprice" in item_data:
            price_info = item_data.get("baseprice")
        
        if price_info:
            if isinstance(price_info, dict):
                price = price_info.get("amount", 0) / 100 if "amount" in price_info else price_info.get("value", 0) / 100
                currency = price_info.get("currency", "EUR")
            elif isinstance(price_info, (int, float)):
                price = price_info / 100
        
        # Print item info
        print(f"\nItem {i+1}: {name}")
        if description:
            print(f"  Description: {description}")
        if price > 0:
            print(f"  Price: {price} {currency}")
    
    if len(items) > 20:
        print(f"\n... and {len(items) - 20} more items")


async def main():
    """
    Main function to demonstrate API calls.
    """
    # You can try these example venues
    venue_slugs = [
        "pirog-delikatesz",  # Previous example
        "burger-king-arena-plaza",  # Popular chain, more likely to have public data
        "pizza-hut-mammut",  # Another popular chain
    ]
    
    # Select venue to test
    venue_slug = venue_slugs[1]  # Change index to test different venues
    
    print(f"Fetching product information for venue: {venue_slug}\n")
    
    # First fetch venue details to get the venue ID
    print("Step 1: Fetching venue details...")
    venue_details = await fetch_venue_details(venue_slug)
    
    if "error" in venue_details:
        print(f"Error fetching venue details: {venue_details['error']}")
    else:
        # Save venue details
        with open(f"{venue_slug}_details.json", "w", encoding="utf-8") as f:
            json.dump(venue_details, f, indent=2, ensure_ascii=False)
            print(f"Venue details saved to {venue_slug}_details.json")
        
        # Extract venue ID
        venue_id = extract_venue_id(venue_details)
        if venue_id:
            print(f"Found venue ID: {venue_id}")
            
            # Try to fetch products using venue ID
            print("\nStep 2: Fetching products by venue ID...")
            products = await fetch_products_by_id(venue_id)
            
            if "error" in products:
                print(f"Error fetching products: {products['error']}")
            else:
                # Save products
                with open(f"{venue_slug}_products.json", "w", encoding="utf-8") as f:
                    json.dump(products, f, indent=2, ensure_ascii=False)
                    print(f"Products saved to {venue_slug}_products.json")
                
                # Extract and print items
                items = extract_items_from_response(products)
                print_items(items)
        else:
            print("Could not find venue ID in the response")
    
    # Try popular items approach regardless of venue ID success
    print("\nStep 3: Fetching popular items...")
    popular_items_data = await fetch_popular_items(venue_slug)
    
    if "error" in popular_items_data:
        print(f"Error fetching popular items: {popular_items_data['error']}")
    else:
        # Save popular items data
        with open(f"{venue_slug}_popular.json", "w", encoding="utf-8") as f:
            json.dump(popular_items_data, f, indent=2, ensure_ascii=False)
            print(f"Popular items data saved to {venue_slug}_popular.json")
        
        # Extract and print items
        items = extract_items_from_response(popular_items_data)
        print_items(items)
        
        # Check if we have venue recommendations
        if "venue_recommendations" in popular_items_data:
            print("\nFound venue recommendations in the response")


if __name__ == "__main__":
    asyncio.run(main())
