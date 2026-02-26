"""
Relief-Route: Humanitarian Logistics Optimizer
Main Pathway processor for disaster report analysis.
"""

import pathway as pw
from llm import extract_incident
from scoring import compute_priority
from weather import get_rainfall
import json
import os

# Get the project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Configuration
USE_SAMPLE = os.getenv("USE_SAMPLE", "true").lower() == "true"

if USE_SAMPLE:
    DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/disaster_reports_sample.csv")
else:
    DATA_PATH = os.path.join(PROJECT_ROOT, "data/processed/disaster_reports.csv")

OUTPUT_PATH = os.path.join(PROJECT_ROOT, "outputs/results.csv")

print(f"Loading data from: {DATA_PATH}")
print(f"Output will be written to: {OUTPUT_PATH}")

# Define schema for disaster reports
class ReportSchema(pw.Schema):
    text: str
    label: str
    disaster_type: str
    region: str
    source: str

# Read disaster reports
social = pw.io.csv.read(
    DATA_PATH,
    schema=ReportSchema,
    mode="static"
)

def analyze_report(text: str, label: str, region: str) -> str:
    """
    Analyze a disaster report and return structured JSON.
    Uses LLM extraction (mock or real) + weather data + priority scoring.
    """
    try:
        # Extract incident details using LLM
        incident = extract_incident(text)
        
        # Use region as fallback if location unknown
        location = incident["location"]
        if location == "unknown":
            location = region
        
        # Get weather data for location
        rainfall = get_rainfall(location)
        
        # Compute priority score
        priority = compute_priority(
            incident["urgency_score"],
            rainfall,
            incident["infrastructure_damage"]
        )
        
        return json.dumps({
            "location": location,
            "priority": priority,
            "disaster_type": incident["disaster_type"],
            "urgency_score": incident["urgency_score"],
            "infrastructure_damage": incident["infrastructure_damage"],
            "rainfall_mm": rainfall,
            "category": label,
            "status": "pending"
        })
    except Exception as e:
        print(f"Analysis error: {e}")
        return json.dumps({
            "location": region,
            "priority": 0,
            "disaster_type": "unknown",
            "urgency_score": 1,
            "infrastructure_damage": "no",
            "rainfall_mm": 0,
            "category": label,
            "status": "error"
        })

# Process each report - single analysis call per row
analyzed = social.select(
    text=social.text,
    analysis=pw.apply(
        lambda t, l, r: analyze_report(t, l, r),
        social.text, social.label, social.region
    )
)

# Extract fields from analysis JSON with explicit types
results = analyzed.select(
    text=analyzed.text,
    location=pw.apply(lambda a: str(json.loads(a)["location"]), analyzed.analysis),
    priority=pw.apply(lambda a: int(json.loads(a)["priority"]), analyzed.analysis),
    disaster_type=pw.apply(lambda a: str(json.loads(a)["disaster_type"]), analyzed.analysis),
    urgency_score=pw.apply(lambda a: int(json.loads(a)["urgency_score"]), analyzed.analysis),
    infrastructure_damage=pw.apply(lambda a: str(json.loads(a)["infrastructure_damage"]), analyzed.analysis),
    rainfall_mm=pw.apply(lambda a: float(json.loads(a)["rainfall_mm"]), analyzed.analysis),
    category=pw.apply(lambda a: str(json.loads(a)["category"]), analyzed.analysis),
)

# Output to CSV (no filter needed - analyze_report handles errors gracefully)
pw.io.csv.write(results, OUTPUT_PATH)

print("Starting Pathway processing...")
pw.run()
print("Processing complete!")
