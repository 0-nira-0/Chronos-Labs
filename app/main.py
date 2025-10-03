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

@app.get("/api/passport/today")
def get_passport():
    try:
        return load_json(CURRENT_FILE)
    except FileNotFoundError:
        raise HTTPException(404, "Current passport file not found")

def current_button(metric_name, threshold_name):
    p = load_json(CURRENT_FILE)
    value = float(p["metrics"][metric_name])
    threshold = float(p["thresholds"][threshold_name])
    flag = value <= threshold if metric_name == "tmin_c" else value >= threshold
    return {"flag": flag, "value": value, "threshold": threshold}

@app.get("/api/buttons/very-wet")
def btn_very_wet():
    return current_button("precip_24h_mm", "very_wet_mm")

@app.get("/api/buttons/windy")
def btn_windy():
    return current_button("wind_sust_max_mps", "windy_sust_mps")

@app.get("/api/buttons/heat")
def btn_heat():
    return current_button("tmax_c", "heat_c")

@app.get("/api/buttons/cold")
def btn_cold():
    return current_button("tmin_c", "cold_c")

def historical_button(key):
    h = load_json(HISTORICAL_FILE)
    prob_any = h.get("buttons", {}).get(key, {}).get("prob_any_window")
    threshold = h.get("buttons", {}).get(key, {}).get("threshold")
    return {
        "metric": key,
        "probability_percent": None if prob_any is None else round(prob_any * 100, 1),
        "threshold": threshold
    }

@app.get("/api/historical/very_wet")
def hist_very_wet():
    return historical_button("very_wet")

@app.get("/api/historical/windy")
def hist_windy():
    return historical_button("windy")

@app.get("/api/historical/heat")
def hist_heat():
    return historical_button("heat")

@app.get("/api/historical/cold")
def hist_cold():
    return historical_button("cold")
