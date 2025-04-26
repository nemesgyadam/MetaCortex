import json
import sys
import logging
from typing import List, Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("wolt")

# Constants
WOLT_API_BASE = "https://consumer-api.wolt.com"

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)


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
                            "online": True  # Already filtered for online
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
            f"  {i + 1}. {r['name']} (Rating: {r['rating_score']}/{r['rating_volume']}, Price: {price_str}, Address: {r['address']})"
        )
    return "\n".join(output_lines)


@mcp.tool()
async def list_italian_restaurants(lat: float, lon: float) -> str:
    """Fetches a list of Italian restaurants near the given latitude and longitude using the Wolt API.

    Args:
        lat: Latitude coordinate.
        lon: Longitude coordinate.

    Returns:
        A string containing a formatted list of nearby Italian restaurants or an error message.
    """
    log.info(f"Fetching Italian restaurants near lat={lat}, lon={lon}")
    url = f"{WOLT_API_BASE}/v1/pages/venue-list/category-italian"
    params = {"lat": lat, "lon": lon}
    headers = {"accept": "application/json"}

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

@mcp.tool()
async def wolt_venue_list(location_code: str, latlng: str = None, open_now: bool = None) -> dict:
    """List venues that deliver to a location code. Optionally filter by latlng and openNow."""
    url = f"{WOLT_API_BASE}/v1/pages/venue-list/{location_code}"
    params = {}
    if latlng:
        params["latlng"] = latlng
    if open_now is not None:
        params["openNow"] = str(open_now).lower()
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch venue list: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_venue_profile(slug: str, language: str = None) -> dict:
    """Get full venue profile (hero images, tagline, badges, etc)."""
    url = f"{WOLT_API_BASE}/consumer-api/venue-content-api/v3/web/venue-content/slug/{slug}"
    params = {}
    if language:
        params["language"] = language
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch venue profile: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_venue_menu(slug: str, language: str = None) -> dict:
    """Get full menu (categories + items) for a venue."""
    url = f"{WOLT_API_BASE}/consumer-api/consumer-assortment/v1/venues/slug/{slug}/assortment"
    params = {}
    if language:
        params["language"] = language
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch venue menu: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_menu_items(slug: str, item_ids: list = None, language: str = None) -> dict:
    """Fetch one or more specific menu items by ID for a venue."""
    url = f"{WOLT_API_BASE}/consumer-api/consumer-assortment/v1/venues/slug/{slug}/assortment/items"
    params = {}
    if item_ids:
        params["item_ids"] = ",".join(item_ids)
    if language:
        params["language"] = language
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch menu items: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_create_basket(venue_id: str, items: list, currency: str = None) -> dict:
    """Create a new basket for a venue and initial items."""
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets"
    payload = {"venue_id": venue_id, "items": items}
    if currency:
        payload["currency"] = currency
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to create basket: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_get_basket(basket_id: str) -> dict:
    """Retrieve a basket by basketId."""
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/{basket_id}"
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to retrieve basket: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_basket_count() -> dict:
    """Get number of active baskets for current user."""
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/count"
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to get basket count: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_checkout(purchase_plan: dict) -> dict:
    """Finalise checkout and place the order."""
    url = f"{WOLT_API_BASE}/order-xp/web/v2/pages/checkout"
    headers = {"accept": "application/json", "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=purchase_plan, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to checkout: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_past_orders(cursor: str = None) -> dict:
    """List the user’s past orders (paginated, newest first)."""
    url = f"{WOLT_API_BASE}/order-xp/web/v1/pages/orders"
    params = {}
    if cursor:
        params["cursor"] = cursor
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to fetch past orders: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_geocode_address(place_id: str) -> dict:
    """Resolve Google Place ID to street address."""
    url = f"{WOLT_API_BASE}/v1/google/geocode-address"
    params = {"place_id": place_id}
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to geocode address: {e}")
        return {"error": str(e)}

@mcp.tool()
async def wolt_order_tracking(order_id: str) -> dict:
    """Get live tracking data for an order."""
    url = f"{WOLT_API_BASE}/order-xp/v1/pages/order-tracking/{order_id}"
    headers = {"accept": "application/json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        log.exception(f"Failed to get order tracking: {e}")
        return {"error": str(e)}


@mcp.tool()
async def wolt_bulk_delete_baskets(ids: list) -> dict:
    """Delete multiple baskets in one call.
    Args:
        ids: List of basket IDs to delete.
    Returns:
        API response as a dict.
    """
    url = f"{WOLT_API_BASE}/order-xp/v1/baskets/bulk/delete"
    payload = {"ids": ids}
    headers = {"accept": "application/json", "Content-Type": "application/json"}
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
    log.info("Starting Wolt MCP server...")
    mcp.run(transport='stdio')
    # This code won't be reached until the server is stopped
    log.info("Server stopped")
