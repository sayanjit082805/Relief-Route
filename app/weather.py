import requests
import os
from dotenv import load_dotenv
from functools import lru_cache

load_dotenv()
API_KEY = os.getenv("OPENWEATHER_KEY")

@lru_cache(maxsize=500)
def get_rainfall(city):
    """Get rainfall with caching to avoid duplicate API calls."""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}"
        data = requests.get(url).json()
        return data.get("rain", {}).get("1h", 0)
    except:
        return 0
