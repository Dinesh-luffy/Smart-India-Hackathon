import requests
import pandas as pd
import joblib
import json
from pathlib import Path

# -------------------------------
# 1️⃣ Load models and label encoders
# -------------------------------
source_model = joblib.load(r"D:\SIH project\Smart-India-Hackathon\SIH_AQI_MODELS\source_contribution_model (2).pkl")
source_label_encoder = joblib.load(r"D:\SIH project\Smart-India-Hackathon\SIH_AQI_MODELS\label_encoder (2).pkl")

# -------------------------------
# 2️⃣ Delhi and API setup
# -------------------------------
DELHI_LAT, DELHI_LON = 28.61, 77.23
DELHI_BBOX = "76.83,28.38,77.35,28.88"
NASA_API_KEY = "b7a443e02865dfb5cf44a92a73eaaa32"  # FIRMS

# -------------------------------
# 3️⃣ Fetch NASA FIRMS fire data
# -------------------------------
fires_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{NASA_API_KEY}/VIIRS_SNPP_NRT/1/{DELHI_BBOX}"
try:
    fires = pd.read_csv(fires_url)
    fires_summary = {
        "confidence": fires["confidence"].mean() if "confidence" in fires.columns else 0,
        "fire_count": len(fires)
    }
except Exception as e:
    print("⚠ Error fetching NASA FIRMS data:", e)
    fires_summary = {"confidence": 0, "fire_count": 0}

# -------------------------------
# 4️⃣ Fetch 3-day wind forecast
# -------------------------------
try:
    meteo_url = f"https://api.open-meteo.com/v1/forecast?latitude={DELHI_LAT}&longitude={DELHI_LON}&daily=wind_speed_10m_max&timezone=auto&forecast_days=3"
    weather = requests.get(meteo_url, timeout=10).json()
    wind_forecast = weather["daily"]["wind_speed_10m_max"]
except Exception as e:
    print("⚠ Error fetching weather data:", e)
    wind_forecast = [0, 0, 0]

# -------------------------------
# 5️⃣ Fetch WAQI AQI data
# -------------------------------
WAQI_TOKEN = "acadb8bdb1b5c6cb7b5402dc5029a35c68e6c1f8"
try:
    waqi_url = f"https://api.waqi.info/feed/delhi/?token={WAQI_TOKEN}"
    aqi_data = requests.get(waqi_url, timeout=10).json()
    delhi_aqi = aqi_data.get("data", {}).get("aqi", 0) or 0
except Exception as e:
    print("⚠ Error fetching AQI data:", e)
    delhi_aqi = 0

# -------------------------------
# 6️⃣ Prepare features for source model
# -------------------------------
features = pd.DataFrame([{
    "Delhi_AQI": delhi_aqi,
    "StubbleBurning_confidence": fires_summary["confidence"],
    "StubbleBurning_count": fires_summary["fire_count"],
    "WindSpeed_Day1": wind_forecast[0],
    "WindSpeed_Day2": wind_forecast[1],
    "WindSpeed_Day3": wind_forecast[2]
}])

# Add missing columns for source_model
missing_cols_source = [col for col in source_model.feature_names_in_ if col not in features.columns]
if missing_cols_source:
    features = pd.concat([features, pd.DataFrame(0, index=features.index, columns=missing_cols_source)], axis=1)
features_source = features[source_model.feature_names_in_]
features_source.columns = features_source.columns.astype(str)

# -------------------------------
# 7️⃣ Compute feature importances & region influence
# -------------------------------
importances = pd.DataFrame({
    'Feature': source_model.feature_names_in_,
    'Importance': source_model.feature_importances_
}).sort_values(by='Importance', ascending=False)

regions = {
    'Punjab': importances[importances['Feature'].str.contains('Punjab', case=False)]['Importance'].sum(),
    'Haryana': importances[importances['Feature'].str.contains('Haryana', case=False)]['Importance'].sum(),
    'UP_West': importances[importances['Feature'].str.contains('UP_West', case=False)]['Importance'].sum(),
    'Rajasthan': importances[importances['Feature'].str.contains('Rajasthan', case=False)]['Importance'].sum(),
}

top_players = pd.DataFrame(list(regions.items()), columns=['Region', 'Influence'])
top_players["Influence_%"] = (top_players["Influence"] / top_players["Influence"].sum()) * 100
top_players = top_players.sort_values(by="Influence_%", ascending=False).reset_index(drop=True)

# Human-readable reasons
reasons = {
    "Punjab": "High stubble burning detected across northern Punjab 🚜🔥",
    "Haryana": "Consistent fire counts and wind drift toward Delhi 🌬",
    "UP_West": "Moderate stubble and industrial impact near NCR 🏭",
    "Rajasthan": "Dust and boundary-layer transport during dry periods 🌵"
}
top_players["Reason"] = top_players["Region"].map(reasons)

# -------------------------------
# 8️⃣ Save top polluting source regions to JSON
# -------------------------------
output_data = []
for _, row in top_players.iterrows():
    output_data.append({
        "Region": row["Region"],
        "Influence_%": round(row["Influence_%"], 1),
        "Reason": row["Reason"]
    })

output_path = Path(__file__).parent / "source_contribution.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=4)

print(f"✅ Source contribution data saved to: {output_path}")
