from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json, os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CURRENT_FILE = "passport_day_2025-08-23.json"
HISTORICAL_FILE = "historical_passport_day_0823.json"

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"{filename} not found in /data/")
    with open(path, "r") as f:
        return json.load(f)

def current_button(metric_name, threshold_name):
    p = load_json(CURRENT_FILE)
    value = float(p["metrics"][metric_name])
    threshold = float(p["thresholds"][threshold_name])
    flag = value <= threshold if metric_name == "tmin_c" else value >= threshold
    return {"flag": flag, "value": value, "threshold": threshold}

def historical_button(key):
    h = load_json(HISTORICAL_FILE)
    prob_any = h.get("buttons", {}).get(key, {}).get("prob_any_window")
    threshold = h.get("buttons", {}).get(key, {}).get("threshold")
    return {
        "metric": key,
        "probability_percent": None if prob_any is None else round(prob_any * 100, 1),
        "threshold": threshold
    }

@app.get("/api/passport")
def passport_combined():
    try:
        live_forecast = {
            "very_wet": current_button("precip_24h_mm", "very_wet_mm"),
            "windy": current_button("wind_sust_max_mps", "windy_sust_mps"),
            "heat": current_button("tmax_c", "heat_c"),
            "cold": current_button("tmin_c", "cold_c")
        }

        event_history = {
            "very_wet": historical_button("very_wet"),
            "windy": historical_button("windy"),
            "heat": historical_button("heat"),
            "cold": historical_button("cold")
        }

        return {"event_history": event_history, "live_forecast": live_forecast}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
