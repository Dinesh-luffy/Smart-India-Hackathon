# map5.py
#!/usr/bin/env python3
import requests
import folium
from folium.plugins import HeatMap
import math
import time
from html import escape
import io
import pandas as pd
import numpy as np

# ========== CONFIG ==========
WAQI_TOKEN = "acadb8bdb1b5c6cb7b5402dc5029a35c68e6c1f8"
OSRM_BASE = "http://router.project-osrm.org/route/v1/driving/"
TOMTOM_KEY = "1KuUTNhJSF7BFGeNHsnAXfHaCDttBCVq"
FIRMS_KEY = "b7a443e02865dfb5cf44a92a73eaaa32"
DELHI_BOUNDS = "28.40,76.90,28.92,77.40"
NUM_ROUTES = 3
HIGH_AQI_THRESHOLD = 150
ALPHA, BETA, GAMMA = 0.4, 0.4, 0.2  # Weights: distance, AQI, traffic/fire contribution
USER_AGENT = "SIH25216_AQI_Router/1.0 (contact: your_email@example.com)"

# ---------- Utility Functions ----------
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def fetch_waqi_stations(bounds=DELHI_BOUNDS, token=WAQI_TOKEN):
    url = f"https://api.waqi.info/map/bounds/?token={token}&latlng={bounds}"
    try:
        r = requests.get(url, timeout=12)
        j = r.json()
        if j.get("status") != "ok": return []
    except Exception:
        return []
    stations = []
    for s in j.get("data", []):
        try:
            aqi = int(s.get("aqi"))
        except: continue
        lat, lon = s.get("lat"), s.get("lon")
        name = s.get("station", {}).get("name","")
        stations.append({"lat": lat, "lon": lon, "aqi": aqi, "name": name})
    return stations

def nearest_station_aqi(lat, lon, stations):
    if not stations: return 0
    best = min(stations, key=lambda s: (s["lat"]-lat)**2 + (s["lon"]-lon)**2)
    return best["aqi"]

def geocode_location(place_name, tries=3, sleep_between=1):
    nom_url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": USER_AGENT}
    params = {"q": place_name.strip() + " , New Delhi, India", "format": "json", "limit":1}
    for _ in range(tries):
        try:
            r = requests.get(nom_url, params=params, headers=headers, timeout=12)
            arr = r.json()
            if arr: return float(arr[0]["lat"]), float(arr[0]["lon"])
        except: time.sleep(sleep_between)
    return None, None

def osrm_get_routes(slat, slon, elat, elon, alternatives=True):
    coords = f"{slon},{slat};{elon},{elat}"
    url = OSRM_BASE + coords
    params = {"alternatives": "true" if alternatives else "false","overview":"full","geometries":"geojson"}
    try:
        r = requests.get(url, params=params, timeout=12)
        j = r.json()
        return j.get("routes", [])
    except: return []

def fetch_traffic_congestion(lat, lon):
    try:
        url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?key={TOMTOM_KEY}&point={lat},{lon}"
        r = requests.get(url, timeout=12).json()
        data = r.get("flowSegmentData",{})
        current = data.get("currentSpeed",0)
        free = data.get("freeFlowSpeed",1)
        congestion = max(0, 100*(1-current/free))
        return congestion
    except: return 0

def fetch_firms_delhi(days=2):
    satellites = ["MODIS_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]
    delhi_lat, delhi_lon = 28.70, 77.20
    FIRE_REGION = {"min_lat": 28.4, "max_lat": 28.9, "min_lon": 76.8, "max_lon": 77.3}
    frp_total = []

    for sat in satellites:
        for day_offset in range(days):
            try:
                bbox = f"{FIRE_REGION['min_lon']},{FIRE_REGION['min_lat']},{FIRE_REGION['max_lon']},{FIRE_REGION['max_lat']}"
                url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_KEY}/{sat}/{bbox}"
                r = requests.get(url, timeout=20)
                r.raise_for_status()
                df = pd.read_csv(io.StringIO(r.content.decode('utf-8')), skiprows=[1,2])
                if 'frp' in df.columns and not df.empty:
                    for _, row in df.iterrows():
                        frp = row['frp']
                        fire_lat, fire_lon = row['latitude'], row['longitude']
                        distance = np.sqrt((fire_lat - delhi_lat)**2 + (fire_lon - delhi_lon)**2) * 111
                        weight = 1 / (distance + 1)
                        frp_total.append({'latitude': fire_lat, 'longitude': fire_lon, 'frp': frp, 'weight': weight})
            except Exception:
                continue
    return frp_total

def score_route_coords(coords, stations, traffic=0, fires=[], industries=[]):
    total_len_km = 0.0
    exposure = 0.0
    for i in range(len(coords)-1):
        lat1, lon1 = coords[i]; lat2, lon2 = coords[i+1]
        seg_km = haversine_km(lat1, lon1, lat2, lon2)
        aqi1 = nearest_station_aqi(lat1, lon1, stations)
        aqi2 = nearest_station_aqi(lat2, lon2, stations)
        seg_aqi = (aqi1+aqi2)/2.0
        fire_aqi = sum(f['frp']/((haversine_km((lat1+lat2)/2,(lon1+lon2)/2,f['latitude'],f['longitude']))**2+0.1) for f in fires)
        ind_aqi = sum(ind['emission']/((haversine_km((lat1+lat2)/2,(lon1+lon2)/2,ind['lat'],ind['lon']))**2+0.1) for ind in industries)
        total_seg_aqi = seg_aqi + fire_aqi*0.05 + ind_aqi*0.03 + traffic*0.1
        exposure += total_seg_aqi * seg_km
        total_len_km += seg_km
    return (exposure/total_len_km) if total_len_km>0 else 0.0, total_len_km

def color_for_aqi(aqi):
    if aqi <= 100: return "#2ECC71"
    if aqi <= 200: return "#FFA500"
    return "#FF3B30"

def build_dashboard_html(scored):
    html = "<div style='font-family:Helvetica,Arial,sans-serif;font-size:13px;background:white;padding:8px;border-radius:8px;box-shadow:0 0 8px rgba(0,0,0,0.2);'>"
    html += "<b style='font-size:15px'>Smart Route Comparison</b><br><small>Distance | ETA | Avg AQI | Score</small><hr style='margin:6px 0'/>"
    html += "<table style='width:100%;border-collapse:collapse;text-align:left'>"
    html += "<tr><th style='padding:4px'>#</th><th style='padding:4px'>Distance</th><th style='padding:4px'>ETA</th><th style='padding:4px'>Avg AQI</th><th style='padding:4px'>Score</th></tr>"
    for i, r in enumerate(scored):
        color = color_for_aqi(r["avg_aqi"])
        html += f"<tr><td style='padding:4px'>{i+1}</td>"
        html += f"<td style='padding:4px'>{r['osrm_distance_km']:.2f} km</td>"
        html += f"<td style='padding:4px'>{r['osrm_duration_min']:.1f}</td>"
        html += f"<td style='padding:4px;color:{color};font-weight:700'>{r['avg_aqi']:.1f}</td>"
        html += f"<td style='padding:4px'>{r['score']:.3f}</td></tr>"
    html += "</table></div>"
    return html

# ---------- Main Wrapped Function ----------
def get_smart_routes(start_address, dest_address):
    stations = fetch_waqi_stations()
    s_lat, s_lon = geocode_location(start_address)
    e_lat, e_lon = geocode_location(dest_address)
    if None in [s_lat,s_lon,e_lat,e_lon]: raise ValueError("Geocoding failed")

    routes = osrm_get_routes(s_lat,s_lon,e_lat,e_lon)
    if not routes: raise ValueError("No routes from OSRM")

    traffic_congestion = fetch_traffic_congestion(s_lat,s_lon)
    fires = fetch_firms_delhi()
    industries = [{"lat":28.58,"lon":77.25,"emission":120},{"lat":28.72,"lon":77.12,"emission":200},{"lat":28.64,"lon":77.22,"emission":150}]
    
    scored = []
    for idx, r in enumerate(routes[:NUM_ROUTES]):
        geom = r.get("geometry",{})
        coords = [(pt[1],pt[0]) for pt in geom.get("coordinates",[])]
        avg_aqi, _ = score_route_coords(coords, stations, traffic_congestion, fires, industries)
        scored.append({
            "idx": idx, "coords": coords, "avg_aqi": avg_aqi,
            "osrm_distance_km": r.get("distance",0)/1000.0,
            "osrm_duration_min": r.get("duration",0)/60.0
        })
    
    dists = [r['osrm_distance_km'] for r in scored]
    aqis = [r['avg_aqi'] for r in scored]
    min_d, max_d = min(dists), max(dists)
    min_a, max_a = min(aqis), max(aqis)
    for r in scored:
        norm_d = (r['osrm_distance_km']-min_d)/(max_d-min_d) if max_d>min_d else 0
        norm_a = (r['avg_aqi']-min_a)/(max_a-min_a) if max_a>min_a else 0
        norm_t = traffic_congestion/100
        r['score'] = ALPHA*norm_d + BETA*norm_a + GAMMA*norm_t

    scored_sorted = sorted(scored,key=lambda x:x['score'])
    recommended = scored_sorted[0]

    center_lat, center_lon = (s_lat+e_lat)/2, (s_lon+e_lon)/2
    m = folium.Map(location=[center_lat,center_lon], zoom_start=13, tiles="OpenStreetMap")

    if stations:
        heat_pts = [[s["lat"],s["lon"],s["aqi"]] for s in stations]
        HeatMap(heat_pts,radius=25,blur=12,max_zoom=12).add_to(m)
        for st in stations:
            folium.CircleMarker([st["lat"],st["lon"]],radius=4,color="#0000FF",fill=True,fill_opacity=0.6,
                tooltip=f"{escape(st.get('name',''))} — AQI: {st['aqi']}").add_to(m)

    for r in scored_sorted:
        coords = r['coords']
        color = color_for_aqi(r['avg_aqi'])
        weight = 9 if r is recommended else 5
        folium.PolyLine(coords,color=color,weight=weight,opacity=0.9,
                        tooltip=(f"Route {r['idx']+1}: {r['osrm_distance_km']:.2f} km | "
                                 f"{r['osrm_duration_min']:.1f} min | AQI {r['avg_aqi']:.1f}")).add_to(m)
        if r is recommended:
            mid = coords[len(coords)//2]
            folium.Marker(mid,popup=f"🏆 Recommended (score {r['score']:.3f})",icon=folium.Icon(color="darkgreen")).add_to(m)
        if r['avg_aqi']>=HIGH_AQI_THRESHOLD:
            mid = coords[len(coords)//2]
            folium.Marker(mid,popup=f"⚠️ High AQI: {r['avg_aqi']:.1f}",icon=folium.Icon(color="red")).add_to(m)

    folium.Marker([s_lat,s_lon],popup="START",icon=folium.Icon(color="green")).add_to(m)
    folium.Marker([e_lat,e_lon],popup="DESTINATION",icon=folium.Icon(color="red")).add_to(m)
    for f in fires:
        folium.CircleMarker([f['latitude'],f['longitude']],radius=6,color='red',fill=True,fill_opacity=0.7,
            tooltip=f"🔥 FRP: {f['frp']}").add_to(m)
    for ind in industries:
        folium.CircleMarker([ind['lat'],ind['lon']],radius=6,color='gray',fill=True,fill_opacity=0.6,
            tooltip=f"🏭 Emission: {ind['emission']}").add_to(m)

    dashboard_html = build_dashboard_html(scored_sorted)
    m.get_root().html.add_child(folium.Element(f"<div style='position:fixed;top:10px;left:10px;z-index:9999;'>{dashboard_html}</div>"))

    legend = """
    <div style="position:fixed;bottom:40px;left:10px;width:220px;z-index:9999;
                background:white;border-radius:8px;box-shadow:0 0 8px rgba(0,0,0,0.2);padding:8px;">
      <b>AQI Legend & Recommended</b><br>
      <div style="margin-top:6px"><span style='background:#2ECC71;padding:6px 8px;border-radius:4px;'></span>&nbsp;Clean (≤100)</div>
      <div style="margin-top:6px"><span style='background:#FFA500;padding:6px 8px;border-radius:4px;'></span>&nbsp;Moderate (101–200)</div>
      <div style="margin-top:6px"><span style='background:#FF3B30;padding:6px 8px;border-radius:4px;'></span>&nbsp;Unhealthy (>200)</div>
      <div style="margin-top:6px"><b>🏆 Recommended route is bolded on map</b></div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend))

    return m
