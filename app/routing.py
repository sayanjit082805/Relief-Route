"""
Route Planning Module for Relief-Route.
Computes optimal delivery routes considering road blockages.
"""

import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import json

# Try to import OSMnx for real routing, fall back to mock
USE_MOCK_ROUTING = os.getenv("USE_MOCK_ROUTING", "true").lower() == "true"

if not USE_MOCK_ROUTING:
    try:
        import osmnx as ox
        import networkx as nx
        print("OSMnx routing initialized")
    except ImportError:
        print("OSMnx not available, using mock routing")
        USE_MOCK_ROUTING = True
else:
    print("Using MOCK routing mode")


# ============ WAREHOUSE LOCATIONS ============

WAREHOUSES = {
    "Nepal": {
        "name": "Kathmandu Central Warehouse",
        "location": "Kathmandu, Nepal",
        "coordinates": (27.7172, 85.3240),
        "capacity_trucks": 20,
        "supplies_available": True
    },
    "India": {
        "name": "Delhi Relief Center", 
        "location": "New Delhi, India",
        "coordinates": (28.6139, 77.2090),
        "capacity_trucks": 50,
        "supplies_available": True
    },
}

# Known locations with coordinates (for mock routing)
LOCATION_COORDS = {
    "Kathmandu": (27.7172, 85.3240),
    "Bhaktapur": (27.6710, 85.4298),
    "Lalitpur": (27.6588, 85.3247),
    "Pokhara": (28.2096, 83.9856),
    "Gorkha": (28.0000, 84.6333),
    "Sindhupalchok": (27.9500, 85.6833),
    "Dolakha": (27.7167, 86.0667),
    "Chitwan": (27.5291, 84.3542),
    "Nepal": (27.7172, 85.3240),  # Default to Kathmandu
    "India": (28.6139, 77.2090),  # Default to Delhi
    "Kashmir": (34.0837, 74.7973),
    "Delhi": (28.6139, 77.2090),
    "Mumbai": (19.0760, 72.8777),
}

# Simulated blocked roads
BLOCKED_ROADS = [
    {"from": "Kathmandu", "to": "Sindhupalchok", "reason": "Landslide", "severity": "complete"},
    {"from": "Gorkha", "to": "Dolakha", "reason": "Bridge collapsed", "severity": "complete"},
]


@dataclass
class Route:
    """A computed delivery route."""
    origin: str
    destination: str
    distance_km: float
    estimated_time_hours: float
    route_type: str  # direct, alternative, blocked
    waypoints: List[str]
    warnings: List[str]
    road_conditions: str  # clear, partial_blockage, hazardous


# ============ DISTANCE CALCULATION ============

def haversine_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate distance between two coordinates in km."""
    import math
    
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371  # Earth's radius in km
    
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlat = lat2 - lat1
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c


def get_coordinates(location: str) -> Tuple[float, float]:
    """Get coordinates for a location."""
    # Check known locations
    for name, coords in LOCATION_COORDS.items():
        if name.lower() in location.lower():
            return coords
    
    # Default to Nepal center
    return (27.7172, 85.3240)


# ============ MOCK ROUTING ============

def mock_compute_route(origin: str, destination: str, avoid_blocked: bool = True) -> Route:
    """
    Compute route using mock data (no external API calls).
    """
    origin_coords = get_coordinates(origin)
    dest_coords = get_coordinates(destination)
    
    # Calculate straight-line distance
    distance = haversine_distance(origin_coords, dest_coords)
    
    # Add road factor (roads are typically 1.3-1.5x longer than straight line)
    road_distance = distance * 1.4
    
    # Check for blocked roads
    warnings = []
    route_type = "direct"
    road_conditions = "clear"
    
    for blockage in BLOCKED_ROADS:
        if (blockage["from"].lower() in origin.lower() and 
            blockage["to"].lower() in destination.lower()) or \
           (blockage["to"].lower() in origin.lower() and 
            blockage["from"].lower() in destination.lower()):
            
            if avoid_blocked:
                # Add detour
                road_distance *= 1.8
                route_type = "alternative"
                road_conditions = "hazardous"
                warnings.append(f"⚠️ Primary route blocked: {blockage['reason']}")
                warnings.append("🔄 Using alternative route (longer)")
            else:
                route_type = "blocked"
                warnings.append(f"🚫 Route blocked: {blockage['reason']}")
    
    # Estimate time (average 30 km/h in disaster conditions)
    avg_speed = 25 if road_conditions == "hazardous" else 35
    time_hours = road_distance / avg_speed
    
    # Generate waypoints
    waypoints = [origin]
    if route_type == "alternative":
        # Add intermediate point
        waypoints.append("Via alternate route")
    waypoints.append(destination)
    
    return Route(
        origin=origin,
        destination=destination,
        distance_km=round(road_distance, 1),
        estimated_time_hours=round(time_hours, 1),
        route_type=route_type,
        waypoints=waypoints,
        warnings=warnings,
        road_conditions=road_conditions
    )


# ============ REAL ROUTING (OSMnx) ============

def osmnx_compute_route(origin: str, destination: str) -> Route:
    """
    Compute route using OSMnx and real road network data.
    """
    try:
        # Get the area graph
        origin_coords = get_coordinates(origin)
        
        # Create graph around the area
        G = ox.graph_from_point(origin_coords, dist=50000, network_type="drive")
        
        # Get destination coordinates
        dest_coords = get_coordinates(destination)
        
        # Find nearest nodes
        orig_node = ox.distance.nearest_nodes(G, origin_coords[1], origin_coords[0])
        dest_node = ox.distance.nearest_nodes(G, dest_coords[1], dest_coords[0])
        
        # Compute shortest path
        route = nx.shortest_path(G, orig_node, dest_node, weight="length")
        
        # Calculate total distance
        distance = sum(G[route[i]][route[i+1]][0].get("length", 0) 
                      for i in range(len(route)-1)) / 1000  # Convert to km
        
        # Estimate time
        time_hours = distance / 30  # Assume 30 km/h average
        
        return Route(
            origin=origin,
            destination=destination,
            distance_km=round(distance, 1),
            estimated_time_hours=round(time_hours, 1),
            route_type="direct",
            waypoints=[origin, destination],
            warnings=[],
            road_conditions="clear"
        )
        
    except Exception as e:
        print(f"OSMnx routing failed: {e}, falling back to mock")
        return mock_compute_route(origin, destination)


# ============ MAIN INTERFACE ============

def compute_route(origin: str, destination: str, avoid_blocked: bool = True) -> Route:
    """
    Compute optimal route from origin to destination.
    
    Args:
        origin: Starting location
        destination: Destination location
        avoid_blocked: Whether to avoid known blocked roads
        
    Returns:
        Route object with distance, time, and warnings
    """
    if USE_MOCK_ROUTING:
        return mock_compute_route(origin, destination, avoid_blocked)
    else:
        return osmnx_compute_route(origin, destination)


def get_nearest_warehouse(location: str) -> Dict:
    """Find the nearest warehouse to a location."""
    location_coords = get_coordinates(location)
    
    nearest = None
    min_distance = float('inf')
    
    for region, warehouse in WAREHOUSES.items():
        distance = haversine_distance(location_coords, warehouse["coordinates"])
        if distance < min_distance:
            min_distance = distance
            nearest = {**warehouse, "region": region, "distance_km": round(distance, 1)}
    
    return nearest


def plan_delivery_routes(destinations: List[Dict], warehouse_region: str = None) -> List[Dict]:
    """
    Plan delivery routes for multiple destinations.
    
    Args:
        destinations: List of dicts with 'location' and 'priority'
        warehouse_region: Optional specific warehouse to use
        
    Returns:
        List of planned routes with details
    """
    routes = []
    
    # Sort by priority (highest first)
    sorted_dests = sorted(destinations, key=lambda x: x.get("priority", 0), reverse=True)
    
    for dest in sorted_dests:
        location = dest.get("location", "Unknown")
        
        # Find best warehouse
        if warehouse_region and warehouse_region in WAREHOUSES:
            warehouse = WAREHOUSES[warehouse_region]
            warehouse_loc = warehouse["location"]
        else:
            nearest = get_nearest_warehouse(location)
            warehouse_loc = nearest["location"]
        
        # Compute route
        route = compute_route(warehouse_loc, location)
        
        routes.append({
            "destination": location,
            "priority": dest.get("priority", 0),
            "disaster_type": dest.get("disaster_type", "unknown"),
            "warehouse": warehouse_loc,
            "distance_km": route.distance_km,
            "estimated_time_hours": route.estimated_time_hours,
            "route_type": route.route_type,
            "road_conditions": route.road_conditions,
            "warnings": route.warnings,
            "waypoints": route.waypoints
        })
    
    return routes


def get_blocked_roads() -> List[Dict]:
    """Get list of currently blocked roads."""
    return BLOCKED_ROADS


def add_road_blockage(from_loc: str, to_loc: str, reason: str, severity: str = "complete"):
    """Add a new road blockage."""
    BLOCKED_ROADS.append({
        "from": from_loc,
        "to": to_loc,
        "reason": reason,
        "severity": severity
    })


# For testing
if __name__ == "__main__":
    print("Testing Route Planning...\n")
    
    # Test single route
    route = compute_route("Kathmandu Central Warehouse", "Gorkha")
    print(f"Route: {route.origin} -> {route.destination}")
    print(f"  Distance: {route.distance_km} km")
    print(f"  Time: {route.estimated_time_hours} hours")
    print(f"  Type: {route.route_type}")
    print(f"  Conditions: {route.road_conditions}")
    print(f"  Warnings: {route.warnings}")
    
    # Test blocked route
    print("\n\nTesting blocked route (Kathmandu -> Sindhupalchok):")
    route2 = compute_route("Kathmandu", "Sindhupalchok")
    print(f"  Distance: {route2.distance_km} km")
    print(f"  Type: {route2.route_type}")
    print(f"  Warnings: {route2.warnings}")
    
    # Test multi-destination planning
    print("\n\nMulti-destination planning:")
    destinations = [
        {"location": "Gorkha", "priority": 85, "disaster_type": "earthquake"},
        {"location": "Pokhara", "priority": 45, "disaster_type": "earthquake"},
        {"location": "Sindhupalchok", "priority": 72, "disaster_type": "landslide"},
    ]
    planned = plan_delivery_routes(destinations)
    print(json.dumps(planned, indent=2))
