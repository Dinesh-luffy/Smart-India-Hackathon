import streamlit as st
import json
from datetime import datetime
from pathlib import Path
import time
import plotly.graph_objects as go
import plotly.express as px

# Import your working map generator
from map5 import generate_map  # make sure generate_map(start, dest) returns map file path

# File paths to your JSONs
FORECAST_PATH = Path(__file__).parent / "latest_forecast.json"
SOURCE_PATH = Path(__file__).parent / "source_contribution.json"

# Custom CSS for stunning visuals
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .main-header {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%);
        padding: 2rem;
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
        backdrop-filter: blur(10px);
    }
    
    .aqi-card {
        background: rgba(255,255,255,0.95);
        border-radius: 20px;
        padding: 2rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .aqi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 50px rgba(0,0,0,0.3);
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(255,255,255,0.8) 100%);
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.15);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.3);
    }
    
    .alert-box {
        background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.9) 100%);
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        border-left: 5px solid;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .source-card {
        background: rgba(255,255,255,0.95);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .source-card:hover {
        transform: translateX(10px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    }
    
    .gradient-text {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------- Helper functions ----------------------------

def load_forecast_data():
    """Load AQI forecast data from JSON file."""
    if not FORECAST_PATH.exists():
        st.error("❌ latest_forecast.json not found.")
        return None
    try:
        with open(FORECAST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error reading forecast file: {e}")
        return None


def load_source_data():
    """Load source contribution data from JSON file."""
    if not SOURCE_PATH.exists():
        return None
    try:
        with open(SOURCE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None


def get_aqi_category(aqi):
    """Return AQI category and color."""
    if aqi <= 100:
        return "Good", "#2ecc71", "✨"
    elif aqi <= 200:
        return "Moderate", "#f1c40f", "😷"
    elif aqi <= 300:
        return "Poor", "#e67e22", "⚠️"
    else:
        return "Severe", "#e74c3c", "☠️"


def aqi_alert_message(aqi):
    """Return warning message based on AQI value."""
    if aqi <= 100:
        return "✅ Air quality is good. Perfect time for outdoor activities!", "#2ecc71"
    elif aqi <= 200:
        return "⚠️ Air quality is moderate. Sensitive individuals should limit prolonged outdoor exertion.", "#f1c40f"
    elif aqi <= 300:
        return "🚨 Air quality is poor! Consider wearing a mask and avoiding long outdoor stays.", "#e67e22"
    else:
        return "☠️ Extremely unhealthy air! Stay indoors if possible.", "#e74c3c"


def create_aqi_gauge(aqi_value, title):
    """Create a beautiful gauge chart for AQI."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=aqi_value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24, 'color': '#333'}},
        delta={'reference': 100, 'increasing': {'color': "red"}},
        gauge={
            'axis': {'range': [None, 500], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 100], 'color': '#2ecc71'},
                {'range': [100, 200], 'color': '#f1c40f'},
                {'range': [200, 300], 'color': '#e67e22'},
                {'range': [300, 500], 'color': '#e74c3c'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': aqi_value
            }
        }
    ))
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#333", 'family': "Inter"}
    )
    return fig


def create_source_donut(source_data):
    """Create a donut chart for source contributions."""
    if not source_data:
        return None
    
    regions = [d["Region"] for d in source_data]
    influences = [d["Influence_%"] for d in source_data]
    
    colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe']
    
    fig = go.Figure(data=[go.Pie(
        labels=regions,
        values=influences,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='label+percent',
        textposition='outside',
        textfont=dict(size=14, color='white', family='Inter'),
        hovertemplate='<b>%{label}</b><br>Contribution: %{value:.1f}%<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(
            text="🔥 Regional Pollution Sources",
            font=dict(size=24, color='white', family='Inter')
        ),
        showlegend=False,
        height=400,
        margin=dict(l=20, r=20, t=60, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        annotations=[
            dict(
                text='Sources',
                x=0.5, y=0.5,
                font=dict(size=20, color='white', family='Inter', weight='bold'),
                showarrow=False
            )
        ]
    )
    return fig


# ---------------------------- Dashboard Layout ----------------------------

st.set_page_config(page_title="Delhi Smart AQI Dashboard", layout="wide", page_icon="🌫️")

st.sidebar.markdown("""
<div style="text-align: center; padding: 1rem;">
    <h1 style="color: white;">🛰️ Navigation</h1>
</div>
""", unsafe_allow_html=True)

page = st.sidebar.radio("", ["📊 Live AQI Dashboard", "🗺️ Smart Map"], label_visibility="collapsed")

# -------------------------------------------------------------------------
# PAGE 1: Live AQI Dashboard
# -------------------------------------------------------------------------
if page == "📊 Live AQI Dashboard":
    
    # Header with gradient
    st.markdown("""
    <div class="main-header">
        <h1 class="gradient-text" style="font-size: 3rem; text-align: center; margin: 0;">
            🌫️ Delhi Smart AQI Dashboard
        </h1>
        <p style="text-align: center; color: #666; font-size: 1.2rem; margin-top: 0.5rem;">
            Real-time & Forecasted Air Quality Intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)

    data = load_forecast_data()
    source_data = load_source_data()
    
    if not data:
        st.stop()

    today_aqi = data.get("Delhi_AQI_Today", 0)
    t1 = data.get("Forecast_T1", 0)
    t2 = data.get("Forecast_T2", 0)
    frp_h = data.get("FRP_Haryana", 0)
    frp_p = data.get("FRP_Punjab", 0)
    frp_u = data.get("FRP_UP_West", 0)
    updated_at = data.get("Updated_At", "")

    # AQI Forecast Section
    st.markdown("<h2 style='color: white; text-align: center;'>📈 AQI Forecast</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    for col, label, aqi, day_num in zip([col1, col2, col3],
                                        ["Today", "Tomorrow", "Day After"],
                                        [today_aqi, t1, t2],
                                        [0, 1, 2]):
        cat, color, emoji = get_aqi_category(aqi)
        with col:
            st.markdown(f"""
            <div class="aqi-card">
                <div style="text-align: center;">
                    <h3 style="color: #666; margin-bottom: 0.5rem;">{label}</h3>
                    <div style="font-size: 4rem; font-weight: 800; color: {color}; line-height: 1;">
                        {aqi}
                    </div>
                    <div style="font-size: 2rem; margin: 0.5rem 0;">{emoji}</div>
                    <div style="background: {color}; color: white; padding: 0.5rem; border-radius: 10px; font-weight: 600;">
                        {cat}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Alert Section
    alert_msg, alert_color = aqi_alert_message(today_aqi)
    st.markdown(f"""
    <div class="alert-box" style="border-left-color: {alert_color}; margin-top: 2rem;">
        <h3 style="color: {alert_color}; margin: 0;">🚨 Air Quality Alert</h3>
        <p style="color: #333; font-size: 1.1rem; margin-top: 0.5rem;">{alert_msg}</p>
    </div>
    """, unsafe_allow_html=True)

    # Two column layout for charts and data
    st.markdown("<br>", unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        # Source Contribution Chart
        if source_data:
            fig = create_source_donut(source_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        # Source Details
        if source_data:
            st.markdown("<h3 style='color: white; text-align: center;'>📍 Regional Impact Analysis</h3>", unsafe_allow_html=True)
            for source in source_data:
                influence_color = "#e74c3c" if source["Influence_%"] > 25 else "#f39c12" if source["Influence_%"] > 15 else "#27ae60"
                st.markdown(f"""
                <div class="source-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="color: #333; margin: 0;">{source["Region"]}</h4>
                            <p style="color: #666; margin: 0.5rem 0 0 0; font-size: 0.9rem;">{source["Reason"]}</p>
                        </div>
                        <div style="background: {influence_color}; color: white; padding: 0.5rem 1rem; border-radius: 10px; font-weight: 700; font-size: 1.2rem;">
                            {source["Influence_%"]:.1f}%
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # FRP Metrics with gauges
    st.markdown("<h2 style='color: white; text-align: center; margin-top: 2rem;'>🔥 Fire Radiative Power Monitoring</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fig = create_aqi_gauge(frp_h, "Haryana FRP")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = create_aqi_gauge(frp_p, "Punjab FRP")
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        fig = create_aqi_gauge(frp_u, "West UP FRP")
        st.plotly_chart(fig, use_container_width=True)

    # Trend visualization
    st.markdown("<h2 style='color: white; text-align: center; margin-top: 2rem;'>📊 3-Day AQI Trend</h2>", unsafe_allow_html=True)
    
    days = ['Today', 'Tomorrow', 'Day After']
    aqi_values = [today_aqi, t1, t2]
    colors_trend = [get_aqi_category(aqi)[1] for aqi in aqi_values]
    
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=days,
        y=aqi_values,
        mode='lines+markers',
        line=dict(width=4, color="#02104f"),
        marker=dict(size=15, color=colors_trend, line=dict(width=2, color='white')),
        fill='tozeroy',
        fillcolor='rgba(102, 126, 234, 0.2)',
        text=[f'AQI: {aqi}<br>{get_aqi_category(aqi)[0]}' for aqi in aqi_values],
        hovertemplate='<b>%{x}</b><br>%{text}<extra></extra>'
    ))
    
    fig_trend.update_layout(
        showlegend=False,
        height=300,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(240,248,255,1)',
        plot_bgcolor='rgba(255,255,255,0.9)',
        xaxis=dict(showgrid=False, color="#000000"),
        yaxis=dict(showgrid=True, gridcolor='rgba(0,0,0,0.1)', color="#000000", title='AQI Value'),
        font=dict(family='Inter', color="#000000"),
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_trend, use_container_width=True)

    # Footer
    st.markdown(f"""
    <div style="text-align: center; color: white; margin-top: 3rem; padding: 1rem; background: rgba(255,255,255,0.1); border-radius: 10px;">
        <p style="margin: 0;">🕒 Last Updated: <strong>{updated_at}</strong></p>
        <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.8;">Data refreshes every hour</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------------------
# PAGE 2: Smart Map
# -------------------------------------------------------------------------
elif page == "🗺️ Smart Map":
    
    st.markdown("""
    <div class="main-header">
        <h1 class="gradient-text" style="font-size: 3rem; text-align: center; margin: 0;">
            🗺️ Delhi Smart AQI Routes
        </h1>
        <p style="text-align: center; color: #666; font-size: 1.2rem; margin-top: 0.5rem;">
            Find the cleanest air routes between locations
        </p>
    </div>
    """, unsafe_allow_html=True)

    suggestions = {
        "Connaught Place, Delhi": "India Gate, Delhi",
        "Qutub Minar": "India Gate",
        "Delhi Airport": "Red Fort"
    }

    st.markdown("""
    <div class="metric-card" style="margin-bottom: 2rem;">
        <h3 style="color: #667eea; margin: 0;">💡 Pro Tip</h3>
        <p style="color: #333; margin-top: 0.5rem;">For best visualization, try: <strong>Connaught Place → India Gate</strong></p>
        <p style="color: #666; margin-top: 0.5rem; font-size: 0.9rem;">Our AI analyzes real-time AQI data to suggest the healthiest routes for your journey.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h4 style='color: white;'>🏁 Start Location</h4>", unsafe_allow_html=True)
        start = st.selectbox("", list(suggestions.keys()), key="start_field", label_visibility="collapsed")
    
    with col2:
        st.markdown("<h4 style='color: white;'>🎯 Destination</h4>", unsafe_allow_html=True)
        dest = st.selectbox("", list(suggestions.values()), key="dest_field", label_visibility="collapsed")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Generate Smart AQI Map", key="map_button", use_container_width=True):
            with st.spinner("🌍 Analyzing air quality along routes... This may take a few moments..."):
                time.sleep(1.5)
                try:
                    map_file = generate_map(start, dest)
                    if not map_file or not Path(map_file).exists():
                        st.error("❌ Error generating map: Map file not found or invalid path.")
                    else:
                        st.success("✅ Map generated successfully!")
                        with open(map_file, "r", encoding="utf-8") as f:
                            map_html = f.read()
                        
                        st.markdown("""
                        <div style="background: white; padding: 1rem; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); margin-top: 1rem;">
                            <h3 style="color: #333; text-align: center;">Interactive AQI Route Map</h3>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.components.v1.html(map_html, height=650)
                except Exception as e:
                    st.error(f"❌ Error generating map: {e}")