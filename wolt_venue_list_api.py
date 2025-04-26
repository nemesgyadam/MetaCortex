"""
Simple Python script to call Wolt venue list API with authentication.
"""
import httpx
import asyncio
from typing import Dict, Any, Optional


async def get_wolt_venue_list(
    location_code: str,
    lat: float,
    lon: float,
    open_now: bool = True,
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Call Wolt venue list API with proper authentication.

    Args:
        location_code: Location code string (e.g., 'budapest')
        lat: Latitude coordinate
        lon: Longitude coordinate
        open_now: Filter to only show open venues
        auth_token: Wolt authentication token (optional)

    Returns:
        API response as dictionary
    """
    # Base URL for Wolt API
    base_url = "https://restaurant-api.wolt.com"
    
    # Endpoint for venue list - using discovery endpoint which is more common
    endpoint = f"/v1/pages/restaurants"
    
    # Query parameters
    params = {
        "lat": lat,
        "lon": lon,
        "city": location_code
    }
    
    if open_now:
        params["filters"] = "open"
    
    # Headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "App-Language": "en",
        "Platform": "Web",
        "Client-Version": "1.15.5",
        "w-wolt-session-id": "session-id-placeholder",
        "x-wolt-web-clientid": "client-id-placeholder",
    }
    
    # Add authentication token if provided
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        # Make the API request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}{endpoint}",
                params=params,
                headers=headers,
                timeout=30
            )
            
            # Raise for HTTP errors
            response.raise_for_status()
            
            # Return the JSON response
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP Error: {e}")
        return {"error": str(e)}
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}


async def main():
    """
    Main function to demonstrate API call.
    """
    # Budapest coordinates
    lat = 47.4775359
    lon = 19.0459652
    location_code = "budapest"
    
    # Replace with your actual auth token if you have one
    # You can obtain this by inspecting network requests in browser dev tools
    # when using the Wolt website or app
    auth_token = None  # "your_auth_token_here"
    
    print(f"Fetching venues for {location_code}...")
    result = await get_wolt_venue_list(
        location_code=location_code,
        lat=lat,
        lon=lon,
        open_now=True,
        auth_token=auth_token
    )
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        # Process and display results
        if "sections" in result:
            sections = result.get("sections", [])
            print(f"Found {len(sections)} sections")
            
            venues = []
            for section in sections:
                section_items = section.get("items", [])
                for item in section_items:
                    if item.get("venue"):
                        venues.append(item["venue"])
            
            print(f"Found {len(venues)} venues")
            
            # Display first 5 venues if available
            for i, venue in enumerate(venues[:5]):
                name = venue.get("name", "Unknown")
                rating = venue.get("rating", {}).get("score", 0)
                reviews = venue.get("rating", {}).get("count", 0)
                print(f"{i+1}. {name} (Rating: {rating}/10 from {reviews} reviews)")
        else:
            print("Unexpected response format")
            print(result)


if __name__ == "__main__":
    asyncio.run(main())
