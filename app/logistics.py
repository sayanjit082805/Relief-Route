"""
Supply Chain Planning Module for Relief-Route.
Determines optimal truck load-outs based on disaster needs and priorities.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
import json

# ============ SUPPLY DEFINITIONS ============

@dataclass
class Supply:
    """A type of relief supply."""
    name: str
    category: str  # medical, food, water, shelter, rescue
    weight_kg: float  # weight per unit
    volume_m3: float  # volume per unit
    priority_multiplier: float  # how much this helps priority situations
    shelf_life_days: int
    
SUPPLIES = {
    # Medical supplies
    "first_aid_kit": Supply("First Aid Kit", "medical", 2.0, 0.01, 1.5, 365),
    "medicine_pack": Supply("Medicine Pack", "medical", 5.0, 0.02, 2.0, 180),
    "surgical_kit": Supply("Surgical Kit", "medical", 10.0, 0.05, 2.5, 365),
    "stretcher": Supply("Stretcher", "rescue", 8.0, 0.3, 1.8, 9999),
    
    # Water & Food
    "water_bottle_case": Supply("Water (24 bottles)", "water", 12.0, 0.03, 1.8, 730),
    "water_purification": Supply("Water Purification Tablets", "water", 0.5, 0.001, 2.0, 365),
    "food_pack_mre": Supply("MRE Food Pack (10)", "food", 8.0, 0.02, 1.5, 365),
    "baby_food": Supply("Baby Food Pack", "food", 3.0, 0.01, 2.0, 180),
    
    # Shelter
    "tent_family": Supply("Family Tent (4 person)", "shelter", 15.0, 0.1, 1.3, 9999),
    "blanket_pack": Supply("Blankets (10)", "shelter", 8.0, 0.08, 1.2, 9999),
    "tarpaulin": Supply("Tarpaulin Sheet", "shelter", 5.0, 0.05, 1.1, 9999),
    
    # Rescue equipment
    "rescue_rope": Supply("Rescue Rope (50m)", "rescue", 5.0, 0.02, 1.5, 9999),
    "flashlight_pack": Supply("Flashlights (10)", "rescue", 3.0, 0.01, 1.2, 365),
    "generator_portable": Supply("Portable Generator", "rescue", 30.0, 0.15, 1.4, 9999),
}

# ============ TRUCK DEFINITIONS ============

@dataclass 
class Truck:
    """A relief delivery truck."""
    id: str
    capacity_kg: float
    capacity_m3: float
    current_location: str
    status: str  # available, en_route, loading

TRUCK_TEMPLATES = {
    "small": Truck("", 1000, 5.0, "", "available"),
    "medium": Truck("", 3000, 15.0, "", "available"),
    "large": Truck("", 8000, 40.0, "", "available"),
}

# ============ NEED PROFILES BY DISASTER TYPE ============

DISASTER_NEEDS = {
    "earthquake": {
        "medical": 0.35,
        "rescue": 0.25,
        "shelter": 0.20,
        "water": 0.15,
        "food": 0.05,
    },
    "flood": {
        "water": 0.30,  # Clean water is critical
        "food": 0.25,
        "shelter": 0.20,
        "medical": 0.15,
        "rescue": 0.10,
    },
    "landslide": {
        "rescue": 0.35,
        "medical": 0.30,
        "shelter": 0.20,
        "water": 0.10,
        "food": 0.05,
    },
    "unknown": {
        "water": 0.25,
        "food": 0.25,
        "medical": 0.20,
        "shelter": 0.20,
        "rescue": 0.10,
    }
}

# ============ NEED PROFILES BY CATEGORY ============

CATEGORY_NEEDS = {
    "injured_or_dead_people": {"medical": 0.5, "rescue": 0.3},
    "missing_trapped_or_found_people": {"rescue": 0.5, "medical": 0.3},
    "infrastructure_and_utilities_damage": {"rescue": 0.3, "shelter": 0.3},
    "displaced_people_and_evacuations": {"shelter": 0.4, "food": 0.3, "water": 0.2},
    "other_useful_information": {},
    "caution_and_advice": {},
}


# ============ LOAD-OUT OPTIMIZER ============

def compute_loadout(
    disaster_type: str,
    priority_score: int,
    category: str,
    infrastructure_damage: str,
    truck_size: str = "medium",
    population_estimate: int = 100
) -> Dict:
    """
    Compute optimal truck load-out for a disaster location.
    
    Returns a dict with:
    - supplies: list of (supply_name, quantity, weight, volume)
    - total_weight: total weight in kg
    - total_volume: total volume in m3
    - estimated_people_helped: rough estimate
    - priority_supplies: top 3 critical items
    """
    truck = TRUCK_TEMPLATES.get(truck_size, TRUCK_TEMPLATES["medium"])
    max_weight = truck.capacity_kg
    max_volume = truck.capacity_m3
    
    # Get base needs from disaster type
    base_needs = DISASTER_NEEDS.get(disaster_type, DISASTER_NEEDS["unknown"]).copy()
    
    # Adjust based on category
    category_adj = CATEGORY_NEEDS.get(category, {})
    for cat, boost in category_adj.items():
        if cat in base_needs:
            base_needs[cat] = min(1.0, base_needs[cat] + boost * 0.3)
    
    # Boost medical if infrastructure damaged
    if infrastructure_damage == "yes":
        base_needs["medical"] = min(1.0, base_needs.get("medical", 0) + 0.15)
        base_needs["rescue"] = min(1.0, base_needs.get("rescue", 0) + 0.10)
    
    # Normalize needs
    total = sum(base_needs.values())
    needs = {k: v/total for k, v in base_needs.items()}
    
    # Allocate capacity to each category
    category_budgets = {
        cat: {"weight": max_weight * ratio, "volume": max_volume * ratio}
        for cat, ratio in needs.items()
    }
    
    # Select supplies for each category
    loadout = []
    total_weight = 0
    total_volume = 0
    
    for category, budget in category_budgets.items():
        # Get supplies in this category, sorted by priority multiplier
        cat_supplies = [
            (name, s) for name, s in SUPPLIES.items() 
            if s.category == category
        ]
        cat_supplies.sort(key=lambda x: x[1].priority_multiplier, reverse=True)
        
        cat_weight = 0
        cat_volume = 0
        
        for supply_name, supply in cat_supplies:
            # How many can we fit?
            max_by_weight = int((budget["weight"] - cat_weight) / supply.weight_kg)
            max_by_volume = int((budget["volume"] - cat_volume) / supply.volume_m3)
            quantity = min(max_by_weight, max_by_volume)
            
            # Scale by population and priority
            quantity = min(quantity, max(5, population_estimate // 10))
            
            if quantity > 0:
                item_weight = quantity * supply.weight_kg
                item_volume = quantity * supply.volume_m3
                
                loadout.append({
                    "supply": supply_name,
                    "name": supply.name,
                    "quantity": quantity,
                    "weight_kg": item_weight,
                    "volume_m3": item_volume,
                    "category": supply.category
                })
                
                cat_weight += item_weight
                cat_volume += item_volume
                total_weight += item_weight
                total_volume += item_volume
    
    # Sort by priority (medical/rescue first)
    priority_order = {"medical": 0, "rescue": 1, "water": 2, "food": 3, "shelter": 4}
    loadout.sort(key=lambda x: priority_order.get(x["category"], 5))
    
    # Estimate people helped (rough: 1 person per 10kg of supplies)
    people_helped = int(total_weight / 10)
    
    return {
        "supplies": loadout,
        "total_weight_kg": round(total_weight, 1),
        "total_volume_m3": round(total_volume, 2),
        "truck_size": truck_size,
        "capacity_used_pct": round(total_weight / max_weight * 100, 1),
        "estimated_people_helped": people_helped,
        "priority_supplies": [s["name"] for s in loadout[:3]],
        "disaster_type": disaster_type
    }


def plan_supply_chain(incidents: List[Dict], available_trucks: int = 5) -> Dict:
    """
    Plan supply chain for multiple incidents.
    
    Args:
        incidents: List of incident dicts with location, priority, disaster_type, etc.
        available_trucks: Number of trucks available
        
    Returns:
        Deployment plan with truck assignments and routes
    """
    # Sort incidents by priority (highest first)
    sorted_incidents = sorted(incidents, key=lambda x: x.get("priority", 0), reverse=True)
    
    deployments = []
    trucks_assigned = 0
    
    for incident in sorted_incidents:
        if trucks_assigned >= available_trucks:
            break
            
        priority = incident.get("priority", 0)
        
        # Assign truck size based on priority
        if priority >= 70:
            truck_size = "large"
            trucks_needed = 1
        elif priority >= 50:
            truck_size = "medium"
            trucks_needed = 1
        else:
            truck_size = "small"
            trucks_needed = 1
        
        if trucks_assigned + trucks_needed > available_trucks:
            continue
            
        # Compute loadout for this deployment
        loadout = compute_loadout(
            disaster_type=incident.get("disaster_type", "unknown"),
            priority_score=priority,
            category=incident.get("category", "other_useful_information"),
            infrastructure_damage=incident.get("infrastructure_damage", "no"),
            truck_size=truck_size
        )
        
        deployments.append({
            "truck_id": f"TRUCK-{trucks_assigned + 1:03d}",
            "truck_size": truck_size,
            "destination": incident.get("location", "Unknown"),
            "priority_score": priority,
            "disaster_type": incident.get("disaster_type", "unknown"),
            "loadout": loadout,
            "status": "ready_to_deploy"
        })
        
        trucks_assigned += trucks_needed
    
    # Summary stats
    total_weight = sum(d["loadout"]["total_weight_kg"] for d in deployments)
    total_people = sum(d["loadout"]["estimated_people_helped"] for d in deployments)
    
    return {
        "deployments": deployments,
        "trucks_used": trucks_assigned,
        "trucks_available": available_trucks - trucks_assigned,
        "total_supplies_kg": round(total_weight, 1),
        "estimated_people_helped": total_people,
        "unserved_incidents": len(sorted_incidents) - len(deployments)
    }


# For testing
if __name__ == "__main__":
    # Test single loadout
    loadout = compute_loadout(
        disaster_type="earthquake",
        priority_score=70,
        category="injured_or_dead_people",
        infrastructure_damage="yes",
        truck_size="large"
    )
    print("Single Loadout:")
    print(json.dumps(loadout, indent=2))
    
    # Test supply chain planning
    test_incidents = [
        {"location": "Kathmandu", "priority": 85, "disaster_type": "earthquake", 
         "category": "injured_or_dead_people", "infrastructure_damage": "yes"},
        {"location": "Gorkha", "priority": 72, "disaster_type": "earthquake",
         "category": "infrastructure_and_utilities_damage", "infrastructure_damage": "yes"},
        {"location": "Pokhara", "priority": 45, "disaster_type": "earthquake",
         "category": "displaced_people_and_evacuations", "infrastructure_damage": "no"},
    ]
    
    plan = plan_supply_chain(test_incidents, available_trucks=3)
    print("\n\nSupply Chain Plan:")
    print(json.dumps(plan, indent=2))
