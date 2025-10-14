import streamlit as st
import threading
from aqi_predict_function import make_live_forecast, get_wqi_data, get_openmeteo_forecast, get_firms_data

st.set_page_config(page_title="AQI Forecast Dashboard", layout="wide")
st.title("AQI Forecast Dashboard 🌆")

# --- 1️⃣ Show live AQI immediately ---
aqi_data = get_wqi_data()
st.metric("Delhi AQI (Today)", aqi_data['Delhi_AQI'])

# --- 2️⃣ Show wind forecast immediately ---
wind_forecast = get_openmeteo_forecast()
st.subheader("Wind Forecast (T+1 / T+2)")
st.json(wind_forecast)

# --- 3️⃣ Placeholders for FIRMS fire data & forecast results ---
fire_placeholder = st.empty()
forecast_placeholder = st.empty()

# --- 4️⃣ Background thread for fire data & AQI forecast ---
def background_fetch():
    fire_placeholder.info("🔥 Fetching FIRMS fire data... This may take a few seconds.")
    
    # Fetch fire data (can take a while)
    fire_data = get_firms_data()
    fire_placeholder.success("✅ FIRMS fire data fetched!")

    # Run AQI forecast now that fire data is ready
    t1_aqi, t2_aqi = make_live_forecast(fire_data)
    forecast_placeholder.success(f"**T+1 AQI:** {t1_aqi}  |  **T+2 AQI:** {t2_aqi}")

# Start background fetch without blocking Streamlit UI
threading.Thread(target=background_fetch, daemon=True).start()
