# 🌫️ Delhi Smart AQI Dashboard & Predictor (SIH)

![Project Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-red.svg)
![Machine Learning](https://img.shields.io/badge/ML-XGBoost-orange.svg)

An AI-powered, real-time air quality monitoring and forecasting system tailored for Delhi, developed for the **Smart India Hackathon (SIH)**. This platform utilizes real-time satellite data, weather forecasting, and machine learning to predict the Air Quality Index (AQI) up to 48 hours in advance and analyze regional pollution sources, particularly stubble burning.

---

## 🌟 Key Features

### 1. 📈 48-Hour AQI Forecasting
Our robust XGBoost models predict the AQI for Delhi at **T+1 (24 hours)** and **T+2 (48 hours)**. The forecasting engine takes into account:
- Historical AQI data
- Wind speed and direction
- Cyclic date patterns (seasonality)
- Real-time Fire Radiative Power (FRP) metrics

### 2. 🔥 Real-Time Fire Radiative Power (FRP) Tracking
Direct integration with the **NASA FIRMS API** to fetch data across multiple satellites (MODIS, VIIRS_SNPP, VIIRS_NOAA20, VIIRS_NOAA21). We monitor active fire points across:
- **Punjab**
- **Haryana**
- **Western Uttar Pradesh**

### 3. 📍 Regional Impact Analysis
A sophisticated machine learning model that attributes Delhi's current AQI to various geographic zones. Find out exactly *why* the air quality is fluctuating by quantifying the percentage contribution of stubble burning from neighboring states.

### 4. 🗺️ Smart Routing Map
An interactive **Folium map** designed to help users find the cleanest routes between popular landmarks in Delhi. The AI analyzes real-time AQI along possible paths and recommends the healthiest journey.

### 5. 🚀 Stunning Streamlit Interface
A beautifully crafted dashboard with glassmorphism design, gradient elements, real-time gauges, and interactive Plotly charts.

---

## 🏗️ Architecture & Technologies

- **Frontend Application**: Streamlit
- **Data Visualization**: Plotly, Folium Maps
- **Data Manipulation**: Pandas, NumPy
- **Machine Learning**: XGBoost, Scikit-learn, Joblib
- **APIs Used**:
  - `NASA FIRMS` (Stubble Burning / Active Fires)
  - `WAQI` (World Air Quality Index for real-time pollutants)
  - `Open-Meteo` (Wind speed and direction forecasting)

---

## 📂 Project Structure

```bash
📦 Smart-India-Hackathon
 ┣ 📂 SIH_AQI_MODELS             # Serialized XGBoost models and scalers (.joblib / .pkl)
 ┣ 📂 frontend
 ┃ ┣ 📜 app2.py                  # Main Streamlit Dashboard Application
 ┃ ┣ 📜 map5.py                  # Smart Routing map generation logic
 ┃ ┗ 📜 latest_forecast.json     # Cached forecast data
 ┣ 📜 aqi_predict_function.py    # Core pipeline for data fetching & T+1/T+2 prediction
 ┣ 📜 source.py                  # Pipeline for Regional Source Influence analysis
 ┣ 📜 requirements.txt           # Project dependencies
 ┗ 📜 README.md                  # This documentation file
```

---

## 🛠️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Dinesh-luffy/Smart-India-Hackathon.git
cd Smart-India-Hackathon
```

### 2. Create a Virtual Environment (Optional but recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up API Keys
Ensure you replace the placeholders in `aqi_predict_function.py` and `source.py` with your active API keys if you plan to fetch live data:
- **WAQI Token**: Used in `get_wqi_data()`
- **NASA FIRMS Key**: Used in `get_firms_data()`

---

## 🚀 Usage

### Step 1: Update Predictions and Source Data
Before running the dashboard, you can refresh the backend models to pull the latest API data and save the outputs to JSON files.
```bash
python aqi_predict_function.py
python source.py
```

### Step 2: Run the Dashboard
Navigate into the frontend directory and launch the Streamlit app.
```bash
cd frontend
streamlit run app2.py
```
> The application will open in your default browser at `http://localhost:8501`.

---

## 💡 How It Works (The Data Pipeline)

1. **Ingestion**: The backend scripts hit WAQI, Open-Meteo, and NASA FIRMS. Data includes PM2.5, PM10, CO, Wind Speed/Direction, and cumulative Fire Radiative Power (FRP) over 3 days.
2. **Preprocessing**: The raw API responses are merged, missing features are imputed, and cyclic features (sin/cos for day and month) are added. The data is transformed using a pre-fit `StandardScaler`.
3. **Inference**: The processed feature vector is passed to two dedicated XGBoost models (`xgb_24h_model_final` and `xgb_48h_model_final`).
4. **Display**: The predicted results and localized fire influences are saved into `.json` caches, which the Streamlit frontend gracefully visualizes for end-users.

---

<p align="center">
  <i>Built with ❤️ for a Cleaner Environment</i>
</p>
