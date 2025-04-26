# Utility functions used by multiple modules
import httpx

def utf8len(s):
    return len(s.encode('utf-8'))

async def get_location_from_ip(ip: str = None) -> dict:
    """Get location information from an IP address.
    
    Args:
        ip (str, optional): IP address to look up. If None, uses the requester's IP.
        
    Returns:
        dict: Location data including latitude, longitude, and possibly altitude.
    """
    async with httpx.AsyncClient() as client:
        # First get basic geolocation from IP
        if ip:
            response = await client.get(f"http://ip-api.com/json/{ip}")
        else:
            # If no IP provided, service will use the requesting IP
            response = await client.get("http://ip-api.com/json/")
            
        if response.status_code == 200:
            location = response.json()
            
            # Now get altitude using Open-Elevation API with the coordinates
            if "lat" in location and "lon" in location:
                try:
                    elevation_response = await client.get(
                        "https://api.open-elevation.com/api/v1/lookup",
                        params={"locations": f"{location['lat']},{location['lon']}"}
                    )
                    if elevation_response.status_code == 200:
                        elevation_data = elevation_response.json()
                        if "results" in elevation_data and len(elevation_data["results"]) > 0:
                            location["altitude"] = int(elevation_data["results"][0]["elevation"])
                except Exception as e:
                    # If elevation lookup fails, continue without altitude
                    location["altitude_error"] = str(e)
                    
            return location
        else:
            return {"error": f"Failed to get location: {response.status_code}"}