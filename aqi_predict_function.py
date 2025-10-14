import pandas as pd
import numpy as np
import joblib
import os
import datetime
import requests 
import io 

# --- 1. Define Model Paths (Local VS Code Setup) ---
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'SIH_AQI_MODELS') 

SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.joblib')
MODEL_24H_PATH = os.path.join(MODEL_DIR, 'xgb_24h_model_final.joblib')
MODEL_48H_PATH = os.path.join(MODEL_DIR, 'xgb_48h_model_final.joblib')

# --- 2. API KEYS & Locations ---
WAQI_API_KEY = "acadb8bdb1b5c6cb7b5402dc5029a35c68e6c1f8"  # Your WAQI token
FIRMS_MAP_KEY = "b7a443e02865dfb5cf44a92a73eaaa32"

FIRE_REGIONS = {
    "Haryana": {"min_lat": 27.5, "max_lat": 31.0, "min_lon": 74.0, "max_lon": 77.5, "model_col": "FRP_Haryana"},
    "Punjab":  {"min_lat": 29.5, "max_lat": 32.5, "min_lon": 73.5, "max_lon": 76.5, "model_col": "FRP_Punjab"},
    "UP_West": {"min_lat": 26.5, "max_lat": 30.0, "min_lon": 77.5, "max_lon": 80.0, "model_col": "FRP_UP_West"},
}

LOCATIONS = {
    "Delhi": {"lat": 28.70, "lon": 77.20},
    "Haryana": {"lat": 29.00, "lon": 76.00},
    "westup": {"lat": 28.00, "lon": 78.00}, 
}

# --- 3. API Functions ---

def get_wqi_data():
    """Fetch live AQI and pollutants from WAQI for Delhi"""
    url = f"https://api.waqi.info/feed/delhi/?token={WAQI_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data["status"] != "ok":
            raise ValueError(data)
        aqi = data["data"]["aqi"]
        iaqi = data["data"]["iaqi"]
        pm25 = iaqi.get("pm25", {}).get("v", 0)
        pm10 = iaqi.get("pm10", {}).get("v", 0)
        co = iaqi.get("co", {}).get("v", 0)
        
        clean_data_map = {
            "Delhi_AQI": aqi,
            "PM2.5": pm25,
            "PM10": pm10,
            "CO": co,
            # Add mock lagged data for model input
            "Delhi_aqi_lag1": aqi * 0.95,
            "delhi_aqi_lag2": aqi * 0.90,
            "Delhi_aqi_lag3": aqi * 0.85,
            "Delhi_aqi_lag7": aqi * 1.05,
            "PM2.5_lag1": pm25 * 0.95,
            "PM10_lag1": pm10 * 0.95,
            "CO_lag1": co * 0.95,
            "Delhi_windspeed": 3.5,
            "Delhi_windirection": 290,
        }
        print(f"✅ Live AQI Input: Delhi AQI (T) set to {aqi} (from WAQI).")
        return clean_data_map
    except Exception as e:
        print(f"❌ Failed to retrieve AQI: {e}")
        # fallback mock values
        return {
            "Delhi_AQI": 110,
            "PM2.5": 110,
            "PM10": 200,
            "CO": 1.8,
            "Delhi_aqi_lag1": 104.5,
            "delhi_aqi_lag2": 99,
            "Delhi_aqi_lag3": 93.5,
            "Delhi_aqi_lag7": 115.5,
            "PM2.5_lag1": 104.5,
            "PM10_lag1": 190,
            "CO_lag1": 1.7,
            "Delhi_windspeed": 3.5,
            "Delhi_windirection": 290,
        }

def get_openmeteo_forecast():
    """Fetch daily average wind speed/direction forecasts for T+1 and T+2"""
    wind_forecast = {}
    for region, coords in LOCATIONS.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": coords["lat"],
                "longitude": coords["lon"],
                "daily": "wind_speed_10m_max,wind_direction_10m_dominant",
                "timezone": "auto",
                "forecast_days": 3
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            wind_forecast[region] = {
                "wind_speed_10m_max_T1": data['daily']['wind_speed_10m_max'][1],
                "wind_direction_10m_dominant_T1": data['daily']['wind_direction_10m_dominant'][1],
                "wind_speed_10m_max_T2": data['daily']['wind_speed_10m_max'][2],
                "wind_direction_10m_dominant_T2": data['daily']['wind_direction_10m_dominant'][2],
            }
        except Exception as e:
            wind_forecast[region] = {
                "wind_speed_10m_max_T1": 3.5,
                "wind_direction_10m_dominant_T1": 290,
                "wind_speed_10m_max_T2": 3.5,
                "wind_direction_10m_dominant_T2": 290,
            }
    return wind_forecast
def get_firms_data():
    """
    Fetch NASA FIRMS fire data for the past 3 days from all major satellites:
    MODIS, VIIRS S-NPP, VIIRS NOAA-20, VIIRS NOAA-21.
    Combines results per region (Haryana, Punjab, UP West).
    If no detections, returns 0.
    """

    FIRMS_SOURCES = [
        "MODIS_NRT",
        "VIIRS_SNPP_NRT",
        "VIIRS_NOAA20_NRT",
        "VIIRS_NOAA21_NRT",
    ]

    DAYS_BACK = 3  # last 3 days cumulative
    fire_data_result = {}

    print(f"\n🔥 Fetching FIRMS fire data (last {DAYS_BACK} days × 4 satellites)...")

    for region, coords in FIRE_REGIONS.items():
        total_frp_all = 0.0
        valid_points = 0

        for source in FIRMS_SOURCES:
            for day_offset in range(DAYS_BACK):
                try:
                    # Example URL: /api/area/csv/{key}/{source}/{bbox}/{day_offset+1}
                    bbox = f"{coords['min_lon']},{coords['min_lat']},{coords['max_lon']},{coords['max_lat']}/{day_offset+1}"
                    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/{source}/{bbox}"
                    response = requests.get(url, timeout=20)
                    response.raise_for_status()

                    df = pd.read_csv(io.StringIO(response.content.decode('utf-8')), skiprows=[1, 2])
                    if 'frp' in df.columns and not df.empty:
                        total_frp_all += df['frp'].sum()
                        valid_points += len(df)

                except Exception as e:
                    print(f"⚠️ {source} D-{day_offset} fetch failed for {region}: {e}")
                    continue

        fire_data_result[coords["model_col"]] = round(total_frp_all, 2)
        print(f"🔥 {region}: 3-day combined FRP = {fire_data_result[coords['model_col']]:.2f} ({valid_points} detections)")

    return fire_data_result


# --- Load Models ---
try:
    SCALER = joblib.load(SCALER_PATH)
    MODEL_24H = joblib.load(MODEL_24H_PATH)
    MODEL_48H = joblib.load(MODEL_48H_PATH)
    MODEL_FEATURE_NAMES = list(SCALER.feature_names_in_)
    print("✅ Models and Scaler loaded successfully on initialization.")
except Exception as e:
    print(f"❌ ERROR loading models: {e}")
    pass

def make_live_forecast(current_day_data_dict={}):
    """Main function to make T+1 and T+2 AQI forecast"""
    if 'SCALER' not in globals() or 'MODEL_24H' not in globals():
        return 0, 0

    live_aqi_data = get_wqi_data()
    live_wind_forecast = get_openmeteo_forecast()
    live_fire_data = get_firms_data()

    clean_data_map = {**live_aqi_data, **live_fire_data}

    # Add cyclical date features
    today = datetime.date.today()
    clean_data_map['day_sin'] = np.sin(2 * np.pi * today.timetuple().tm_yday / 366)
    clean_data_map['day_cos'] = np.cos(2 * np.pi * today.timetuple().tm_yday / 366)
    clean_data_map['month_sin'] = np.sin(2 * np.pi * today.month / 12)
    clean_data_map['month_cos'] = np.cos(2 * np.pi * today.month / 12)

    # Add wind forecasts
    for region, data in live_wind_forecast.items():
        clean_data_map[f'{region}_windspeed_T+1_WIND'] = data['wind_speed_10m_max_T1']
        clean_data_map[f'{region}_windirection_T+1_WIND'] = data['wind_direction_10m_dominant_T1']
        clean_data_map[f'{region}_windspeed_T+2_WIND'] = data['wind_speed_10m_max_T2']
        clean_data_map[f'{region}_windirection_T+2_WIND'] = data['wind_direction_10m_dominant_T2']

    # Map clean data to model features
    input_row = {}
    for messy_feature_name in MODEL_FEATURE_NAMES:
        clean_key_1 = messy_feature_name.strip()
        clean_key_2 = messy_feature_name.strip().replace(' ', '_')
        if clean_key_1 in clean_data_map:
            input_row[messy_feature_name] = clean_data_map[clean_key_1]
        elif clean_key_2 in clean_data_map:
            input_row[messy_feature_name] = clean_data_map[clean_key_2]
        else:
            input_row[messy_feature_name] = 0.0

    input_df = pd.DataFrame([input_row], columns=MODEL_FEATURE_NAMES)
    input_scaled = SCALER.transform(input_df)

    pred_24h = MODEL_24H.predict(input_scaled)[0]
    pred_48h = MODEL_48H.predict(input_scaled)[0]

    return round(pred_24h), round(pred_48h)

# --- Example Usage ---
if __name__ == '__main__':
    # --- Make live forecast once ---
    prediction_24h, prediction_48h = make_live_forecast()

    # --- Fetch all live data only ONCE ---
    live_aqi_data = get_wqi_data()
    live_fire_data = get_firms_data()

    output = {
        "Delhi_AQI_Today": live_aqi_data["Delhi_AQI"],
        "Forecast_T1": prediction_24h,
        "Forecast_T2": prediction_48h,
        "FRP_Haryana": live_fire_data.get("FRP_Haryana", 0),
        "FRP_Punjab": live_fire_data.get("FRP_Punjab", 0),
        "FRP_UP_West": live_fire_data.get("FRP_UP_West", 0),
        "Updated_At": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # --- Save to JSON file ---
    import json
    with open("latest_forecast.json", "w") as f:
        json.dump(output, f, indent=4)

    print("✅ Saved forecast to latest_forecast.json")
