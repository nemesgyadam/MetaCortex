import json
import sys
import logging
from typing import List, Dict, Any, Optional
import datetime
import os

import httpx
from mcp.server.fastmcp import FastMCP




# --- Logging Setup ---
# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Generate timestamped filename
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"wolt_mcp_server_{timestamp}.log")

# Configure logging handlers
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Root logger setup (optional, but good practice)
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO) # Set root level

# Clear existing handlers (important if script is re-run in same process)
if root_logger.hasHandlers():
    root_logger.handlers.clear()

# Console Handler (stderr)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(log_formatter)
root_logger.addHandler(console_handler)

# File Handler
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setFormatter(log_formatter)
root_logger.addHandler(file_handler)

# Get the specific logger for this module
log = logging.getLogger(__name__)
# --- End Logging Setup ---

# Helper function to parse detailed venue list data
def _parse_venue_list_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Parses the raw venue list API response to extract key venue information,
    including ID, name, rating, and preview menu items.
    """
    extracted_info = []
    log.info("Parsing venue list data...")
    sections = data.get('sections', [])
    if not sections:
        log.warning("No 'sections' found in the venue list data.")
        return []

    for section in sections:
        items = section.get('items', [])
        # Heuristic: Check if the first item's template suggests it's a venue list section
        if items and items[0].get('template', '').startswith('venue-'):
            log.info(f"Processing venue section '{section.get('name', 'N/A')}' with {len(items)} items.")
            for item in items:
                # Check if the item itself contains venue data directly or nested
                venue_data = item.get('venue')
                if not venue_data:
                    # Sometimes venue data might be elsewhere in the item, adjust if needed
                    log.debug(f"Skipping item without direct 'venue' key. Template: {item.get('template')}")
                    continue

                # Extract venue details safely
                venue_id = venue_data.get('id')
                venue_name = venue_data.get('name')
                venue_rating_score = venue_data.get('rating', {}).get('score') # Safely get rating score

                # Extract preview menu items
                preview_items_info = []
                for menu_item in venue_data.get('venue_preview_items', []):
                     preview_items_info.append({
                         'id': menu_item.get('id'),
                         'name': menu_item.get('name'),
                         'price': menu_item.get('baseprice') # Changed from 'price' to 'baseprice' based on observation
                     })

                if venue_id and venue_name: # Only add if we have core info
                    extracted_info.append({
                        'id': venue_id,
                        'name': venue_name,
                        'rating_score': venue_rating_score,
                        'preview_menu_items': preview_items_info
                    })
                else:
                    log.warning(f"Skipped venue due to missing ID or Name: {venue_data.get('id', 'N/A')}")

    log.info(f"Extracted information for {len(extracted_info)} venues.")
    return extracted_info


# Initialize FastMCP server
mcp = FastMCP("wolt")

# Constants
WOLT_API_BASE = "https://consumer-api.wolt.com"
WOLT_RESTAURANT_API_BASE = "https://restaurant-api.wolt.com"


def _parse_restaurant_data(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parses the restaurant data from the Wolt API response."""
    restaurants = []
    if "sections" in data:
        for section in data.get("sections", []):
            for item in section.get("items", []):
                if "venue" in item:
                    venue = item["venue"]
                    # Only consider online restaurants
                    if venue.get("online", False):
                        restaurant_info = {
                            "name": venue.get("name", "N/A"),
                            "address": venue.get("address", "N/A"),
                            "rating_score": venue.get("rating", {}).get("score", "N/A"),
                            "rating_volume": venue.get("rating", {}).get("volume", "N/A"),
                            "price_range": venue.get("price_range", "N/A"),
                            "online": True,  # Already filtered for online
                            "slug": venue.get("slug", "N/A")
                        }
                        restaurants.append(restaurant_info)
    return restaurants


def _format_restaurant_output(restaurants: List[Dict[str, Any]]) -> str:
    """Formats the list of restaurants into a string."""
    if not restaurants:
        return "No online Italian restaurants found nearby."

    log.info(f"Found {len(restaurants)} online Italian restaurants.")
    output_lines = ["Nearby Italian Restaurants (Top 10):"]
    for i, r in enumerate(restaurants[:10]):  # Limit to top 10
        price_str = '$' * r['price_range'] if isinstance(r['price_range'], int) else 'N/A'
        output_lines.append(
            f"  {i + 1}. {r['name']} (Rating: {r['rating_score']}/{r['rating_volume']}, Price: {price_str}, Address: {r['address']}, Slug: {r['slug']})"
        )
    return "\n".join(output_lines)


def get_auth_headers(language: str = "en", auth_token: Optional[str] = None, session_id: Optional[str] = None, client_id: str = "web") -> Dict[str, str]:
    """
    Generate common authentication headers used in Wolt API requests.
    
    Args:
        language: Language code for localization
        auth_token: Optional authentication token (Bearer token)
        session_id: Optional session ID for authentication
        client_id: Client ID (default: web)
        
    Returns:
        Dictionary of headers required for API authentication
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Accept-Language": language,
        "X-Client-Id": client_id
    }
    
    # Add authentication headers if provided
    if session_id:
        headers["X-Session-Id"] = session_id
        
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        
    return headers


@mcp.tool()
async def list_nearby_restaurants(lat: float, lon: float, category: Optional[str] = None, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> str:
    """Fetches a list of restaurants near the given latitude and longitude using the Wolt API.

    Args:
        lat: Latitude coordinate.
        lon: Longitude coordinate.
        category: Optional. Restaurant category (e.g., 'italian', 'sushi').
        auth_token: Optional. Wolt authentication token.
        session_id: Optional. Wolt session ID for authentication.
        language: Language code for localization (default: 'en').

    Returns:
        A string containing a formatted list of nearby restaurants or an error message.
    """
    log.info(f"Fetching restaurants near lat={lat}, lon={lon}" + (f" with category={category}" if category else ""))
    
    # Build the URL based on whether a category is specified
    if category:
        url = f"{WOLT_RESTAURANT_API_BASE}/v1/pages/venue-list/category-{category.lower()}"
    else:
        url = f"{WOLT_RESTAURANT_API_BASE}/v1/pages/restaurants"
    
    params = {"lat": lat, "lon": lon}
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            data = response.json()
            log.info(f"Wolt API response status: {response.status_code}")

            restaurants = _parse_restaurant_data(data)
            return _format_restaurant_output(restaurants)

    except httpx.HTTPStatusError as e:
        log.error(f"Wolt API HTTP error: {e.response.status_code} - {e.response.text}")
        return f"Error fetching restaurants from Wolt API: HTTP {e.response.status_code}"
    except httpx.RequestError as e:
        log.error(f"Wolt API Request error: {e}")
        return f"Error connecting to Wolt API: {e}"
    except json.JSONDecodeError as e:
        log.error(f"Wolt API: Failed to decode JSON response: {e}")
        return "Error processing restaurant data from Wolt API."
    except Exception as e:
        log.exception(f"An unexpected error occurred while fetching restaurants: {e}")  # Use log.exception to include traceback
        return f"An unexpected error occurred while fetching restaurants: {e}"


#TODO only return venues no items!
@mcp.tool()
async def wolt_venue_list(location_code: str, lat: float = None, lon: float = None, open_now: bool = None, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """List venues that deliver to a location code. Returns a dictionary containing a list of venues
       with their ID, name, rating, and preview menu items, or an error dictionary.
    """
    # Use restaurant API which is more likely to work without authentication
    url = f"{WOLT_RESTAURANT_API_BASE}/v1/pages/restaurants"
    
    params = {"city": location_code}
    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
    if open_now:
        params["filters"] = "open"
    
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    
    log.info(f"Attempting to fetch venue list...")
    log.info(f"URL: {url}")
    log.info(f"Params: {params}")
    log.info(f"Headers: {headers}") # Be cautious logging headers if they contain sensitive info like tokens

    try:
        async with httpx.AsyncClient() as client:
            log.info("Sending GET request...")
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            log.info(f"Request completed with status code: {resp.status_code}")
            resp.raise_for_status()
            log.info("Successfully fetched venue list raw data.")
            # Parse the raw data using the new helper function
            parsed_data = _parse_venue_list_data(resp.json())
            return {"venues": parsed_data} # Return the parsed data in a structured dict

    except httpx.TimeoutException as e:
        log.exception(f"Request timed out after 30 seconds: {e}")
        return {"error": f"Request timed out: {e}"}
    except httpx.HTTPStatusError as e:
        log.exception(f"HTTP Error fetching venue list: {e.response.status_code} - {e.response.text}")
        return {"error": f"HTTP Error: {e.response.status_code}", "details": e.response.text}
    except Exception as e:
        log.exception(f"Generic error fetching venue list: {e}")
        return {"error": str(e)}

"""
@mcp.tool()
async def wolt_venue_profile(slug: str, language: str = "en", auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID) -> dict:
    ""Get full venue profile (hero images, tagline, badges, etc).
    
    Args:
        slug: Venue slug (from URL, e.g., 'mcdonalds-blaha')
        language: Language code for localization (default: 'en')
        auth_token: Optional Wolt authentication token
    ""
    url = f"{WOLT_API_BASE}/v1/pages/venues/{slug}"
    params = {"lang": language}
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch venue profile: {e}")
        return {"error": str(e)}
"""


@mcp.tool()
async def wolt_venue_menu(slug: str, language: str = "en", auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID) -> dict:
    """Get full menu (categories + items) for a venue.
    
    Args:
        slug: Venue slug (from URL, e.g., 'mcdonalds-blaha')
        language: Language code for localization (default: 'en')
        auth_token: Optional Wolt authentication token
    """
    # This API endpoint matches the successful one from wolt_venue_menu_api.py
    url = f"{WOLT_API_BASE}/consumer-api/consumer-assortment/v1/venues/slug/{slug}/assortment"
    
    # Add loading strategy parameter to get full items
    params = {
        "language": language,
        "loading_strategy": "full"
    }
    
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            # Save response to file with timestamp
            from datetime import datetime
            import os
            
            # Create directory if it doesn't exist
            os.makedirs("C:/Code/MetaCortex_v1/wolt", exist_ok=True)
            
            # Format filename with slug and current timestamp
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"C:/Code/MetaCortex_v1/wolt/menu_{slug}_{now}.txt"
            
            # Write response to file
            with open(filename, "w", encoding="utf-8") as f:
                f.write(json.dumps(resp.json(), indent=2))

            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch venue menu: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_menu_items(slug: str, item_ids: list = None, language: str = "en", auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID) -> dict:
    """Fetch one or more specific menu items by ID for a venue.
    
    Args:
        slug: Venue slug (from URL, e.g., 'mcdonalds-blaha')
        item_ids: List of item IDs to fetch
        language: Language code for localization (default: 'en')
        auth_token: Optional Wolt authentication token
    """
    url = f"{WOLT_API_BASE}/consumer-api/consumer-assortment/v1/venues/slug/{slug}/items"
    
    params = {"language": language}
    if item_ids:
        params["ids"] = ",".join(item_ids)
        
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch menu items: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_create_basket(venue_id: str, items: list, currency: str = None, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Create a new basket for a venue and initial items.
    
    Args:
        venue_id: ID of the venue (not the slug)
        items: List of items to add to basket
        currency: Optional currency code
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets"
    payload = {"venueId": venue_id, "items": items}
    if currency:
        payload["currency"] = currency
        
    # This particular endpoint requires authentication
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to create basket: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_get_basket(basket_id: str, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Retrieve a basket by basketId.
    
    Args:
        basket_id: ID of the basket to retrieve
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/{basket_id}"
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to retrieve basket: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_basket_count(auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Get number of active baskets for current user.
    
    Args:
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/count"
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to get basket count: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_checkout(purchase_plan: dict, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Finalise checkout and place the order.
    WARNING: This function should NOT be run during development or testing!
    
    Args:
        purchase_plan: Order details
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    # Adding safety check to prevent accidental orders during development
    if "dev_mode" in purchase_plan and purchase_plan["dev_mode"] == True:
        log.warning("Checkout attempted in dev mode - operation blocked for safety")
        return {"error": "Checkout blocked: dev_mode flag is set to True. This is a safety feature to prevent accidental orders."}
        
    url = f"{WOLT_API_BASE}/order-xp/web/v2/pages/checkout"
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=purchase_plan, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to checkout: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_past_orders(cursor: str = None, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """List the user's past orders (paginated, newest first).
    
    Args:
        cursor: Pagination cursor for fetching next page of results
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/order-xp/web/v1/pages/orders"
    params = {}
    if cursor:
        params["cursor"] = cursor
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch past orders: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_geocode_address(place_id: str, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Resolve Google Place ID to street address.
    
    Args:
        place_id: Google Place ID to resolve
        auth_token: Optional Wolt authentication token
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/v1/google/geocode-address"
    params = {"place_id": place_id}
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to geocode address: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_order_tracking(order_id: str, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Get live tracking data for an order.
    
    Args:
        order_id: ID of the order to track
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/pages/order-tracking/{order_id}"
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to get order tracking: {e}")
        return {"error": str(e)}


@mcp.tool()
async def wolt_bulk_delete_baskets(ids: list, auth_token: Optional[str] = AUTH_TOKEN, session_id: Optional[str] = SESSION_ID, language: str = "en") -> dict:
    """Delete multiple baskets in one call.
    
    Args:
        ids: List of basket IDs to delete
        auth_token: Wolt authentication token (required for this operation)
        language: Language code for localization (default: 'en')
    
    Returns:
        API response as a dict
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/bulk/delete"
    payload = {"ids": ids}
    headers = get_auth_headers(language=language, auth_token=auth_token, session_id=session_id)
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            # This endpoint may return an empty body on success
            if resp.content:
                return resp.json()
            return {"success": True}
    except Exception as e:
        log.exception(f"Failed to bulk delete baskets: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Initialize and run the server
    log.info(f"Starting Wolt MCP server... Logging to console and {log_file}") # Log filename at start
    mcp.run(transport='stdio')
    # This code won't be reached until the server is stopped
    log.info("Server stopped")
