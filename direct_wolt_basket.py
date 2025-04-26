"""
Direct script to add an item to a Wolt basket using the API directly.
No MCP/ClientManager dependency.
"""
import asyncio
import httpx
from typing import Dict, Any, Optional


async def create_basket(
    venue_id: str,
    item_id: str,
    quantity: int = 1,
    auth_token: str = None,
    session_id: str = None,
    client_id: str = "web",
    language: str = "en"
) -> Dict[str, Any]:
    """
    Create a basket with an item directly using the Wolt API.
    
    Args:
        venue_id: ID of the venue
        item_id: ID of the item to add
        quantity: Quantity of items to add
        auth_token: Optional authentication token (Bearer token)
        session_id: Optional session ID for authentication
        client_id: Client ID (default: web)
        language: Language code (default: en)
        
    Returns:
        Response JSON from the Wolt API
    """
    # API endpoint
    base_url = "https://consumer-api.wolt.com"
    endpoint = "/order-xp/v1/baskets"
    url = f"{base_url}{endpoint}"
    
    # Prepare headers following the pattern from wolt_venue_menu_api.py
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
        headers["Authorization"] = "Bearer "+auth_token
    
    # Prepare basket creation request data
    data = {
        "venue_id": venue_id,
        "items": [
            {
                "id": item_id,
                "quantity": quantity,
                "price": 95000  # Price of item in smallest currency unit (from API response)
            }
        ],
        "currency": "HUF"  # Example for Hungary, change if needed
    }
    
    print(f"Making request to {url}")
    print(f"Headers: {headers}")
    print(f"Request data: {data}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            
            # Get the response content regardless of status code
            response_text = response.text
            
            # Print response details for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response_text[:500]}..." if len(response_text) > 500 else response_text)
            
            # Force raise an exception for HTTP errors
            response.raise_for_status()
            
            # Return the JSON response if successful
            return response.json()
            
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e}")
        # Try to parse the error response if possible
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error details: {error_data}")
                return {"error": str(e), "details": error_data}
            except Exception:
                pass
        return {"error": str(e)}
    except Exception as e:
        print(f"Error creating basket: {e}")
        return {"error": str(e)}


async def main():
    # Pistachio-Mascarpone Calzone from the provided data
    item_id = "1812dce8d7ff69f637dcc217"# "0edff4489301896552b7fb23"
    
    # Venue ID for the restaurant (Pizza Me or similar)
    venue_id = "5e3a8a3e2e4c5b000c9d2f3e"# "617bd8b17317edf628e3dd26"
    
    # Authentication values
   
    AUTH_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjY4MDMzZDU2MDAwMDAwMDAwMDAwMDAwMCIsInR5cCI6IngudXNlcitqd3QifQ.eyJhdWQiOlsicmVzdGF1cmFudC1hcGkiLCJpbnRlZ3JhdGlvbi1jb25maWctc2VydmljZSIsIm1lYWwtYmVuZWZpdHMtc2VydmljZSIsImNvbnN1bWVyLWFzc29ydG1lbnQiLCJsb3lhbHR5LWdhdGV3YXkiLCJwYXltZW50LXNlcnZpY2UiLCJzdWJzY3JpcHRpb24tc2VydmljZSIsIndscy1jdXN0b21lci1zZXJ2aWNlIiwiY29udmVyc2Utd2lkZ2V0LWNvbnN1bWVyIiwiZS13YWxsZXQtc2VydmljZSIsImRhYXMtcHVibGljLWFwaSIsIndvbHQtY29tIiwib3JkZXItdHJhY2tpbmciLCJnaWZ0LWNhcmQtc2hvcCIsImNvdXJpZXJjbGllbnQiLCJ0b3B1cC1zZXJ2aWNlIiwic3VwcG9ydC1mdW5uZWwiLCJwYXltZW50cy10aXBzLXNlcnZpY2UiLCJkaWZmdXNpb24iLCJ3b2x0YXV0aCIsImFjdGl2aXR5LWh1YiIsInJldHVybnMtYXBpIiwibG95YWx0eS1wcm9ncmFtLWFwaSIsImNvcnBvcmF0ZS1wb3J0YWwtYXBpIiwidmVudWUtY29udGVudC1hcGkiLCJvcmRlci14cCIsImFkLWluc2lnaHRzIl0sImlzcyI6IndvbHRhdXRoIiwianRpIjoiMTVmZmNhZDgyMmExMTFmMGI0ZGUxNjg0MGY1ZGFiMzIiLCJ1c2VyIjp7ImlkIjoiNWU4YjI4YWFkY2UyY2RiODY0MmIzNTNkIiwibmFtZSI6eyJmaXJzdF9uYW1lIjoiTmVtZXMiLCJsYXN0X25hbWUiOiJcdTAwYzFkXHUwMGUxbSJ9LCJlbWFpbCI6Im5lbWVzZ3lhZGFtQGdtYWlsLmNvbSIsInJvbGVzIjpbInVzZXIiXSwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX251bWJlcl92ZXJpZmllZCI6dHJ1ZSwiY291bnRyeSI6IkhVTiIsImxhbmd1YWdlIjoiaHUiLCJwcm9maWxlX3BpY3R1cmUiOnsidXJsIjoiaHR0cHM6Ly9jcmVkaXRvcm5vdG1lZGlhLnMzLmFtYXpvbmF3cy5jb20vZTFhYzQ3YmNmM2Q4ZTc0Y2JmMGI0NjAxZjA4MjFmODZmOWRlYzMyYjNmOTQxZWJmNzFkMWQ4Y2QwZGYxNDQ5YzNlNDdlODJlZDA4MDRlMTc0NmRlNjZhNjBkYmRmODUxYjQwNDliMDRhNWZmZGNkOGExN2MzMWQ3NTg3ODUzMGEifSwicGVybWlzc2lvbnMiOltdLCJwaG9uZV9udW1iZXIiOiIrMzYzMDYwMjY4MTgiLCJ0ZW5hbnQiOiJ3b2x0In0sImlhdCI6MTc0NTY3MzU3MCwiZXhwIjoxNzQ1Njc1MzcwLCJhbXIiOltdfQ.r9Uh8iA2DvMuV-8fc27pPu-ZJEvbHlHQvcOPZBZpPUVVAqVCnHih2sB_nKePhhBFYqOIdq0QJc-b7QXJC-F6gA"

    SESSION_ID = "1af23bc3-fb71-4e6d-980d-0d9b7ed583e0"

    # You need to get real authentication values from your browser's network tab
    # when logged into Wolt to make this API call work
    
    print(f"Creating basket with item {item_id} for venue {venue_id}...")
    
    result = await create_basket(
        venue_id=venue_id,
        item_id=item_id,
        quantity=1,
        auth_token=AUTH_TOKEN,
        session_id=SESSION_ID,
        language="en"
    )
    
    # Print the result
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Successfully added item to basket!")
        print(f"Basket ID: {result.get('id', 'N/A')}")
        print(f"Total price: {result.get('price', 0) / 100} {result.get('currency', 'EUR')}")
        
        # Print items in the basket
        items = result.get("items", [])
        if items:
            print("\nItems in basket:")
            for i, item in enumerate(items):
                name = item.get("name", "Unknown item")
                quantity = item.get("quantity", 0)
                price = item.get("price", 0) / 100
                print(f"{i+1}. {name} (x{quantity}) - {price} {result.get('currency', 'EUR')}")


if __name__ == "__main__":
    asyncio.run(main())
