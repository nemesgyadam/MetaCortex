"""
Simple Python script to fetch a venue's full menu and category items from Wolt API.
"""
import httpx
import asyncio
import json
from typing import Dict, Any, Optional


async def get_venue_menu(
    venue_slug: str,
    language: str = "en",
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve the full menu (categories + items) for a Wolt venue.

    Args:
        venue_slug: Venue slug (same as in Wolt URL, e.g., 'zing-burger-co-mom')
        language: Localisation language code (ISO-639-1)
        auth_token: Wolt authentication token (optional)

    Returns:
        API response as dictionary containing the full menu
    """
    # Base URL for Wolt API
    base_url = "https://consumer-api.wolt.com"
    
    # Endpoint for venue menu
    endpoint = f"/consumer-api/consumer-assortment/v1/venues/slug/{venue_slug}/assortment"
    
    # Query parameters
    params = {
        "language": language
    }
    
    # Headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "App-Language": language,
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


def print_menu_summary(menu_data: Dict[str, Any]) -> None:
    """
    Print a summary of the menu data in a structured format.
    
    Args:
        menu_data: Menu data from the API response
    """
    if "error" in menu_data:
        print(f"Error: {menu_data['error']}")
        return
    
    # Extract basic information
    assortment_id = menu_data.get("assortment_id", "Unknown")
    loading_strategy = menu_data.get("loading_strategy", "Unknown")
    primary_language = menu_data.get("primary_language", "Unknown")
    selected_language = menu_data.get("selected_language", "Unknown")
    
    print(f"Assortment ID: {assortment_id}")
    print(f"Loading Strategy: {loading_strategy}")
    print(f"Primary Language: {primary_language}")
    print(f"Selected Language: {selected_language}")
    
    # Display available languages
    available_languages = menu_data.get("available_languages", [])
    language_names = [lang.get("name", "Unknown") for lang in available_languages]
    print(f"Available Languages: {', '.join(language_names)}")
    
    # Extract and display categories
    categories = menu_data.get("categories", [])
    print(f"\nFound {len(categories)} categories")
    
    # Display category details
    for i, category in enumerate(categories[:10]):  # Show only first 10 categories
        name = category.get("name", "Unknown Category")
        description = category.get("description", "")
        slug = category.get("slug", "")
        item_ids = category.get("item_ids", [])
        
        # Get image URL if available
        image_url = ""
        images = category.get("images", [])
        if images and len(images) > 0:
            image_url = images[0].get("url", "")
        
        print(f"\nCategory {i+1}: {name}")
        if description:
            print(f"  Description: {description}")
        print(f"  Slug: {slug}")
        print(f"  Items: {len(item_ids)}")
        if image_url:
            print(f"  Image: {image_url}")
    
    if len(categories) > 10:
        print(f"\n... and {len(categories) - 10} more categories")
    
    # Show items information
    items = menu_data.get("items", [])
    print(f"\nTotal items in 'items' array: {len(items)}")
    
    # Explain the structure
    print("\nNote: This venue appears to use a 'partial' loading strategy,")
    print("which means menu items are likely loaded on-demand when a category is selected.")
    print("The API response contains only category information without actual items.")


async def get_category_items(
    venue_slug: str,
    category_id: str,
    assortment_id: str,
    language: str = "en",
    auth_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve items for a specific category in a Wolt venue.

    Args:
        venue_slug: Venue slug (same as in Wolt URL)
        category_id: Category ID to fetch items for
        assortment_id: Assortment ID from the menu data
        language: Localisation language code (ISO-639-1)
        auth_token: Wolt authentication token (optional)

    Returns:
        API response as dictionary containing the category items
    """
    # Base URL for Wolt API
    base_url = "https://consumer-api.wolt.com"
    
    # Try approach #1: Get the full assortment with a specific category ID
    endpoint = f"/consumer-api/consumer-assortment/v1/venues/slug/{venue_slug}/assortment"
    
    # Query parameters - include loading_strategy parameter
    params = {
        "language": language,
        "selected_category_id": category_id,
        "loading_strategy": "full"
    }
    
    # Headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "App-Language": language,
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
        print(f"HTTP Error for approach #1: {e}")
        
        # Try approach #2: Alternative endpoint for items
        try:
            alt_endpoint = f"/consumer-api/consumer-assortment/v1/venues/slug/{venue_slug}/categories/{category_id}/items"
            alt_response = await client.get(
                f"{base_url}{alt_endpoint}",
                params={"language": language},
                headers=headers,
                timeout=30
            )
            alt_response.raise_for_status()
            return alt_response.json()
        except httpx.HTTPStatusError as e2:
            print(f"HTTP Error for approach #2: {e2}")
            
            # Try approach #3: Direct assortment ID endpoint
            try:
                assort_endpoint = f"/v3/assortment/{assortment_id}/category/{category_id}"
                assort_response = await client.get(
                    f"https://restaurant-api.wolt.com{assort_endpoint}",
                    params={"language": language},
                    headers=headers,
                    timeout=30
                )
                assort_response.raise_for_status()
                return assort_response.json()
            except httpx.HTTPStatusError as e3:
                print(f"HTTP Error for approach #3: {e3}")
                return {"error": f"All approaches failed. Latest error: {e3}"}
            except Exception as e3:
                print(f"Unexpected error in approach #3: {e3}")
                return {"error": str(e3)}
        except Exception as e2:
            print(f"Unexpected error in approach #2: {e2}")
            return {"error": str(e2)}
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}


def print_category_items(category_data: Dict[str, Any]) -> None:
    """
    Print details of items in a category.
    
    Args:
        category_data: Category data from the API response
    """
    if "error" in category_data:
        print(f"Error: {category_data['error']}")
        return
        
    # Different API endpoints return different structures, so we need to handle each
    
    # Try to extract items from the main response
    items = category_data.get("items", [])
    
    # If items not found directly, try looking in different locations in the response
    if not items and "categories" in category_data:
        # Look for the specific category that might have items
        for category in category_data.get("categories", []):
            if "item_ids" in category and category["item_ids"]:
                # Extract items using item_ids
                item_ids = category.get("item_ids", [])
                # Find items in the items array that match these IDs
                all_items = category_data.get("items", [])
                items = [item for item in all_items if item.get("id") in item_ids]
                break
    
    # Use different structure for approach #3 response
    if not items and "catalog" in category_data:
        items = category_data.get("catalog", {}).get("items", [])
    
    # Extract category information (works for most response formats)
    # Try different paths to find category name
    category_name = "Unknown Category"
    if "name" in category_data:
        category_name = category_data.get("name")
    elif "categories" in category_data:
        # Find the first category with items
        for category in category_data.get("categories", []):
            if category.get("item_ids"):
                category_name = category.get("name", "Unknown Category")
                break
    elif "catalog" in category_data and "categories" in category_data["catalog"]:
        categories = category_data["catalog"]["categories"]
        if categories:
            category_name = categories[0].get("name", "Unknown Category")
    
    # Try to get description from various possible locations
    category_description = ""
    if "description" in category_data:
        category_description = category_data.get("description", "")
    
    print(f"\nCategory: {category_name}")
    if category_description:
        print(f"Description: {category_description}")
    
    print(f"Found {len(items)} items in this category\n")
    
    # Display item details
    for i, item in enumerate(items):
        name = item.get("name", "Unknown Item")
        description = item.get("description", "No description")
        
        # Handle different price field structures
        price = 0
        currency = "EUR"
        
        # Try multiple price field structures
        if "baseprice" in item:
            price_info = item.get("baseprice", {})
            price = price_info.get("amount", 0) / 100 if price_info else 0
            currency = price_info.get("currency", "EUR") if price_info else "EUR"
        elif "price" in item:
            price_info = item.get("price", {})
            price = price_info.get("amount", 0) / 100 if price_info else 0
            currency = price_info.get("currency", "EUR") if price_info else "EUR"
        
        # Get image URL if available
        image_url = ""
        images = item.get("images", [])
        if images and len(images) > 0:
            image_url = images[0].get("url", "")
            
        # Alternative image path
        if not image_url and "image" in item:
            image_url = item.get("image", {}).get("url", "")
        
        print(f"Item {i+1}: {name}")
        if description:
            print(f"  Description: {description}")
        print(f"  Price: {price} {currency}")
        if image_url:
            print(f"  Image: {image_url}")
        
        # Extract modifiers/options if available
        options = item.get("options", [])
        if options:
            print(f"  Options/Modifiers: {len(options)}")
            for j, option in enumerate(options[:3]):  # Show just the first few options
                option_name = option.get("name", "Unknown Option")
                print(f"    - {option_name}")
            if len(options) > 3:
                print(f"    ... and {len(options) - 3} more options")
        print()


async def search_products(venue_slug: str, search_term: str, language: str = "en", auth_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for products at a venue using a search term.
    This often works better than category-based API endpoints without authentication.
    
    Args:
        venue_slug: Venue slug (same as in Wolt URL)
        search_term: Text to search for (can be empty to return all products)
        language: Localisation language code (ISO-639-1)
        auth_token: Wolt authentication token (optional)
    
    Returns:
        API response as dictionary containing product search results
    """
    # Base URL for Wolt API
    base_url = "https://restaurant-api.wolt.com"
    
    # Endpoint for product search
    endpoint = f"/v1/pages/venue/search/{venue_slug}"
    
    # Query parameters
    params = {
        "q": search_term,
        "lang": language
    }
    
    # Headers with authentication
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "App-Language": language,
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
        print(f"HTTP Error in product search: {e}")
        return {"error": str(e)}
    except httpx.RequestError as e:
        print(f"Request Error: {e}")
        return {"error": str(e)}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {"error": str(e)}


def print_product_search_results(search_data: Dict[str, Any]) -> None:
    """
    Print details of product search results.
    
    Args:
        search_data: Product search data from the API response
    """
    if "error" in search_data:
        print(f"Error: {search_data['error']}")
        return
    
    # Extract sections which contain items
    sections = []
    if "sections" in search_data:
        sections = search_data.get("sections", [])
    
    # If we can't find sections, try to extract from other parts of the response
    if not sections and "results" in search_data:
        sections = search_data.get("results", {}).get("sections", [])
    
    if not sections:
        print("No product sections found in the response")
        return
    
    # Count total items
    total_items = 0
    for section in sections:
        items = section.get("items", [])
        total_items += len(items)
    
    print(f"\nFound {len(sections)} sections with a total of {total_items} items")
    
    # Display items by section
    for section_idx, section in enumerate(sections):
        section_title = section.get("title", f"Section {section_idx + 1}")
        items = section.get("items", [])
        
        print(f"\nSection: {section_title} ({len(items)} items)")
        
        # Display item details
        for i, item in enumerate(items[:10]):  # Limit to 10 items per section for brevity
            # Try to extract item info from different possible structures
            item_data = item
            if "item" in item:
                item_data = item.get("item", {})
            elif "product" in item:
                item_data = item.get("product", {})
            
            name = item_data.get("name", "Unknown Item")
            description = item_data.get("description", "No description")
            
            # Handle different price field structures
            price = 0
            currency = "EUR"
            
            # Try multiple price field locations
            price_info = None
            if "price" in item_data:
                price_info = item_data.get("price")
            elif "baseprice" in item_data:
                price_info = item_data.get("baseprice")
            elif "price_info" in item_data:
                price_info = item_data.get("price_info")
            
            if price_info:
                if isinstance(price_info, dict):
                    price = price_info.get("amount", 0) / 100 if "amount" in price_info else price_info.get("price", 0) / 100
                    currency = price_info.get("currency", "EUR")
                elif isinstance(price_info, (int, float)):
                    price = price_info / 100
            
            # Get image URL if available
            image_url = ""
            if "image" in item_data:
                image = item_data.get("image", {})
                if isinstance(image, dict):
                    image_url = image.get("url", "")
                elif isinstance(image, str):
                    image_url = image
            elif "images" in item_data:
                images = item_data.get("images", [])
                if images and len(images) > 0:
                    if isinstance(images[0], dict):
                        image_url = images[0].get("url", "")
                    elif isinstance(images[0], str):
                        image_url = images[0]
            
            print(f"Item {i+1}: {name}")
            if description and description != "None":
                print(f"  Description: {description}")
            if price > 0:
                print(f"  Price: {price} {currency}")
            if image_url:
                print(f"  Image: {image_url}")
            print()
        
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more items in this section")


async def main():
    """
    Main function to demonstrate API calls.
    """
    # Example venue slug - you can replace this with an actual venue
    venue_slug = "pirog-delikatesz"  # Use a real venue slug from Wolt
    
    # Replace with your actual auth token if you have one
    auth_token = None  # "your_auth_token_here"
    
    # Get venue menu in English
    print(f"Fetching menu structure for venue: {venue_slug}")
    menu_result = await get_venue_menu(
        venue_slug=venue_slug,
        language="en",
        auth_token=auth_token
    )
    
    # Print structured menu information
    print_menu_summary(menu_result)
    
    # Save the result to a file for further inspection
    with open(f"{venue_slug}_menu.json", "w", encoding="utf-8") as f:
        json.dump(menu_result, f, indent=2, ensure_ascii=False)
        print(f"\nFull menu structure saved to {venue_slug}_menu.json")
    
    # Try category-based approach first
    categories = menu_result.get("categories", [])
    if categories:
        # Choose the first category with a valid ID
        for category in categories:
            category_id = category.get("id", "")
            category_name = category.get("name", "Unknown")
            category_slug = category.get("slug", "")
            if category_id:
                assortment_id = menu_result.get("assortment_id", "")
                print(f"\nAttempting to fetch items for category: {category_name} (id: {category_id})")
                category_result = await get_category_items(
                    venue_slug=venue_slug,
                    category_id=category_id,
                    assortment_id=assortment_id,
                    language="en",
                    auth_token=auth_token
                )
                
                # Save category items to a file
                filename = f"{venue_slug}_{category_slug if category_slug else category_id}_items.json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(category_result, f, indent=2, ensure_ascii=False)
                    print(f"Category API response saved to {filename}")
                
                # Print item information
                print_category_items(category_result)
                break
    
    # Now try the product search approach
    print("\n\nAttempting direct product search (often works better without authentication)")
    
    # First try an empty search to get all products
    search_result = await search_products(
        venue_slug=venue_slug,
        search_term="",  # Empty search term to try to get all products
        language="en",
        auth_token=auth_token
    )
    
    # Save search results to a file
    with open(f"{venue_slug}_product_search.json", "w", encoding="utf-8") as f:
        json.dump(search_result, f, indent=2, ensure_ascii=False)
        print(f"Product search results saved to {venue_slug}_product_search.json")
    
    # Print product information
    print_product_search_results(search_result)
    
    # Try a specific search term if the first search didn't yield results
    if "error" in search_result or not search_result.get("sections", []):
        print("\nTrying search with a specific term...")
        specific_search_result = await search_products(
            venue_slug=venue_slug,
            search_term="pizza",  # Common food item that might be on the menu
            language="en",
            auth_token=auth_token
        )
        
        # Save specific search results to a file
        with open(f"{venue_slug}_product_search_pizza.json", "w", encoding="utf-8") as f:
            json.dump(specific_search_result, f, indent=2, ensure_ascii=False)
            print(f"Product search results for 'pizza' saved to {venue_slug}_product_search_pizza.json")
        
        # Print product information
        print_product_search_results(specific_search_result)


if __name__ == "__main__":
    asyncio.run(main())
