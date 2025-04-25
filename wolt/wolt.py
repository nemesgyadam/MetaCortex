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


if __name__ == "__main__":
    # Initialize and run the server
    log.info("Starting Wolt MCP server...")
    mcp.run(transport='stdio')
    # This code won't be reached until the server is stopped
    log.info("Server stopped")
