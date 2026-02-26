"""
LLM module for extracting incident information from disaster reports.
Supports both real Gemini API and mock mode for testing.
"""

import os
import json
import re
import time
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

# Configuration
USE_MOCK = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Rate limiting for real API
REQUESTS_PER_MINUTE = 2
MIN_DELAY = 60 / REQUESTS_PER_MINUTE
last_request_time = 0
request_count = 0

# Initialize Gemini client only if not in mock mode
client = None
if not USE_MOCK and GEMINI_API_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Gemini API initialized")
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
        USE_MOCK = True

if USE_MOCK:
    print("Running in MOCK mode - no API calls will be made")


# ============ MOCK EXTRACTION (Rule-based) ============

# Location hierarchy - specific locations first, countries last
# The extraction will prefer more specific matches
NEPAL_CITIES = [
    'Kathmandu', 'Bhaktapur', 'Lalitpur', 'Pokhara', 'Gorkha', 
    'Sindhupalchok', 'Dolakha', 'Rasuwa', 'Nuwakot', 'Dhading',
    'Chitwan', 'Biratnagar', 'Bharatpur'
]

INDIA_STATES = [
    'Kashmir', 'Srinagar', 'Jammu', 'Delhi', 'Mumbai', 'Chennai',
    'Uttarakhand', 'Gujarat', 'Assam', 'Bihar', 'Rajasthan',
    'Uttar Pradesh', 'Madhya Pradesh', 'West Bengal'
]

# Map regions to their normalized names (for grouping in dashboard)
LOCATION_NORMALIZATION = {
    # Nepal regions -> use specific city/district names
    'nepal': 'Kathmandu',  # Default Nepal to Kathmandu if no specific city
    'kathmandu valley': 'Kathmandu',
    
    # India regions -> use specific state names  
    'india': 'Delhi',  # Default India to Delhi if no specific state
    'north india': 'Delhi',
    'new delhi': 'Delhi',
}

# Order matters: check specific locations FIRST, then countries
ALL_LOCATIONS = NEPAL_CITIES + INDIA_STATES

HIGH_URGENCY_KEYWORDS = [
    'dead', 'death', 'killed', 'dying', 'trapped', 'buried', 
    'collapsed', 'destroyed', 'urgent', 'emergency', 'critical',
    'missing', 'stranded', 'rescue', 'help needed'
]

MEDIUM_URGENCY_KEYWORDS = [
    'injured', 'hurt', 'damage', 'destroyed', 'blocked', 'flooded',
    'evacuation', 'displaced', 'homeless', 'rubble', 'survivors'
]

INFRASTRUCTURE_KEYWORDS = [
    'road', 'bridge', 'building', 'hospital', 'school', 'power',
    'electricity', 'water', 'collapsed', 'blocked', 'damaged'
]


def normalize_location(location: str, text: str) -> str:
    """Normalize location names to avoid duplicates like 'Nepal' vs 'Kathmandu'."""
    loc_lower = location.lower()
    text_lower = text.lower()
    
    # Check if this is a generic country name and we can be more specific
    if loc_lower in LOCATION_NORMALIZATION:
        # But first, check if there's a more specific location in the text
        for specific_loc in ALL_LOCATIONS:
            if specific_loc.lower() in text_lower and specific_loc.lower() != loc_lower:
                return specific_loc
        return LOCATION_NORMALIZATION[loc_lower]
    
    return location


def mock_extract_incident(text: str) -> dict:
    """Rule-based extraction for testing without API."""
    text_lower = text.lower()
    
    # Extract location - check specific cities/states FIRST
    location = "unknown"
    
    # First pass: look for specific cities/states
    for loc in ALL_LOCATIONS:
        if loc.lower() in text_lower:
            location = loc
            break
    
    # Second pass: if only country found or unknown, check for country names
    if location == "unknown":
        if 'nepal' in text_lower:
            location = 'Kathmandu'  # Default Nepal reports to Kathmandu
        elif 'india' in text_lower:
            location = 'Delhi'  # Default India reports to Delhi
    
    # Normalize the location
    location = normalize_location(location, text)
    
    # Calculate urgency score (1-5)
    urgency = 2
    for keyword in HIGH_URGENCY_KEYWORDS:
        if keyword in text_lower:
            urgency = max(urgency, 5)
            break
    for keyword in MEDIUM_URGENCY_KEYWORDS:
        if keyword in text_lower:
            urgency = max(urgency, 4)
            break
    
    # Detect infrastructure damage
    infra_damage = "no"
    for keyword in INFRASTRUCTURE_KEYWORDS:
        if keyword in text_lower:
            infra_damage = "yes"
            break
    
    # Detect disaster type
    disaster_type = "unknown"
    if any(word in text_lower for word in ['earthquake', 'quake', 'tremor', 'aftershock']):
        disaster_type = "earthquake"
    elif any(word in text_lower for word in ['flood', 'flooding', 'submerged', 'waterlogged']):
        disaster_type = "flood"
    elif any(word in text_lower for word in ['landslide', 'mudslide']):
        disaster_type = "landslide"
    
    return {
        "disaster_type": disaster_type,
        "urgency_score": urgency,
        "infrastructure_damage": infra_damage,
        "location": location
    }


# ============ REAL API EXTRACTION ============

def rate_limited_request(prompt: str, max_retries: int = 5) -> str:
    """Make rate-limited API request with exponential backoff."""
    global last_request_time, request_count
    
    for attempt in range(max_retries):
        elapsed = time.time() - last_request_time
        if elapsed < MIN_DELAY:
            wait_time = MIN_DELAY - elapsed
            print(f"Rate limiting: waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
        
        try:
            last_request_time = time.time()
            request_count += 1
            print(f"[API #{request_count}] Calling Gemini...")
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            print(f"[API #{request_count}] Success!")
            return response.text
            
        except Exception as e:
            error_str = str(e).lower()
            if "429" in str(e) or "rate" in error_str or "quota" in error_str:
                wait_time = (2 ** attempt) * 30
                print(f"[API #{request_count}] Rate limited, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[API #{request_count}] Error: {e}")
                raise e
    
    raise Exception("Max retries exceeded")


def api_extract_incident(text: str) -> dict:
    """Extract incident info using Gemini API."""
    prompt = f"""
    Extract disaster incident information from this social media report.
    Return ONLY valid JSON with these exact fields:
    
    - disaster_type: earthquake, flood, landslide, or unknown
    - urgency_score: integer 1-5 (5=most urgent, life-threatening)
    - infrastructure_damage: "yes" or "no"
    - location: specific city/district name, or "unknown" if unclear
    
    Report:
    {text}
    
    Return ONLY the JSON object, no markdown or explanation.
    """
    
    try:
        raw_output = rate_limited_request(prompt)
        raw_output = raw_output.strip().replace("```json", "").replace("```", "")
        return json.loads(raw_output)
    except Exception as e:
        print(f"API extraction failed: {e}")
        return mock_extract_incident(text)


# ============ MAIN INTERFACE ============

@lru_cache(maxsize=2000)
def extract_incident(text: str) -> dict:
    """
    Extract incident information from text.
    Uses mock mode for testing or real API in production.
    """
    if USE_MOCK or client is None:
        return mock_extract_incident(text)
    else:
        return api_extract_incident(text)
