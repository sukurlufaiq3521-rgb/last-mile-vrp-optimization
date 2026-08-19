import streamlit as st
import pandas as pd
import numpy as np
import folium
import sys
sys.path.append('src')
from osrm_helper import load_cache, save_cache, get_full_route_geometry
from streamlit_folium import st_folium
from folium.plugins import TimestampedGeoJson
from datetime import datetime, timedelta
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import plotly.express as px
from vrp_core import haversine, calculate_vehicle_capacity, solve_vrp

st.set_page_config(
    page_title="Last-Mile Delivery VRP Optimizer",
    page_icon="🚚",
    layout="wide"
)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

[data-testid="stSidebar"] {
    background-color: #1a2332;
}

[data-testid="stSidebar"] * {
    color: #e8ecf1 !important;
}

[data-testid="stMetric"] {
    background-color: #f8f9fb;
    border-left: 4px solid #2563eb;
    border-radius: 6px;
    padding: 12px 16px;
}

[data-testid="stMetricLabel"] {
    font-weight: 600;
}

[data-testid="stMetricLabel"] p {
    color: #1a2332 !important;
}

[data-testid="stMetricValue"] {
    color: #1a2332 !important;
    font-weight: 700 !important;
}

[data-testid="stMetricDelta"] {
    color: #1a2332 !important;
}
h1 {
    color: #1a2332;
    font-weight: 700;
}

h2, h3 {
    color: #2563eb;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    df = pd.read_csv('data/delivery_points.csv')
    distance_matrix = np.load('data/distance_matrix.npy')
    return df, distance_matrix


df, distance_matrix = load_data()

COLORS = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
          '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']







@st.cache_data(show_spinner=False)
def solve_vrp_cached(num_vehicles, demands, dist_matrix, depot=0, balance_weight=0):
    return solve_vrp(num_vehicles, demands, dist_matrix, depot=depot, balance_weight=balance_weight)


def create_static_map(df, routes_info, active_vehicles):
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')

    folium.Marker(
        [depot_lat, depot_lon],
        popup='Anbar (Depot)',
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)

    cache = load_cache()

    for info in routes_info:
        vehicle_id = info['vehicle_id']
        if vehicle_id not in active_vehicles:
            continue

        route = info['route']
        color = COLORS[vehicle_id % len(COLORS)]

        real_route_coords = get_full_route_geometry(route, df, cache)

        stop_number = 0
        for point_id in route:
            if point_id != 0:
                stop_number += 1
                lat = df.loc[point_id, 'latitude']
                lon = df.loc[point_id, 'longitude']
                demand = df.loc[point_id, 'demand']

                folium.Marker(
                    [lat, lon],
                    icon=folium.DivIcon(html=f"""
                        <div style="
                            background-color: {color};
                            color: white;
                            border-radius: 50%;
                            width: 22px;
                            height: 22px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 10px;
                            font-weight: bold;
                            border: 2px solid white;
                            box-shadow: 0 0 3px rgba(0,0,0,0.5);
                        ">{stop_number}</div>
                    """),
                    popup=f"Nöqtə #{point_id} | Maşın {vehicle_id} | {stop_number}-ci dayanacaq | Sifariş: {demand}"
                ).add_to(m)

        folium.PolyLine(
            real_route_coords, color=color, weight=3, opacity=0.8
        ).add_to(m)

    save_cache(cache)
    return m


def create_animated_map(df, routes_info, active_vehicles):
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')

    folium.Marker(
        [depot_lat, depot_lon],
        popup='Anbar (Depot)',
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)

    cache = load_cache()
    features = []
    base_time = datetime(2026, 1, 1, 8, 0, 0)

    for info in routes_info:
        vehicle_id = info['vehicle_id']
        if vehicle_id not in active_vehicles:
            continue

        route = info['route']
        color = COLORS[vehicle_id % len(COLORS)]

        real_coords = get_full_route_geometry(route, df, cache)
        total_points = len(real_coords)
        time_step = timedelta(minutes=60 / max(total_points, 1))

        coordinates = []
        times = []
        for i in range(len(real_coords)):
            coord = real_coords[i]
            coordinates.append([coord[1], coord[0]])
            point_time = base_time + (time_step * i)
            times.append(point_time.strftime('%Y-%m-%dT%H:%M:%S'))

        feature = {
            'type': 'Feature',
            'geometry': {'type': 'LineString', 'coordinates': coordinates},
            'properties': {
                'times': times,
                'style': {'color': color, 'weight': 4, 'opacity': 0.8},
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': color,
                    'fillOpacity': 1,
                    'stroke': 'true',
                    'color': 'white',
                    'weight': 2,
                    'radius': 9
                }
            }
        }
        features.append(feature)

    save_cache(cache)

    TimestampedGeoJson(
        {'type': 'FeatureCollection', 'features': features},
        period='PT1M',
        add_last_point=True,
        auto_play=False,
        loop=False,
        max_speed=5,
        loop_button=True,
        date_options='HH:mm',
        time_slider_drag_update=True,
        duration='PT2M'
    ).add_to(m)

    return m
def create_gantt_chart(routes_info, active_vehicles, avg_speed):
    """Hər maşının dayanacaqlara çatma vaxtını üfüqi zolaqlı qrafikdə göstərir."""
    gantt_data = []
    base_time = datetime(2026, 1, 1, 8, 0, 0)

    for info in routes_info:
        if info['vehicle_id'] not in active_vehicles or info['stops'] == 0:
            continue

        cumulative_km = 0
        route_distance_km = info['distance'] / 1000
        num_segments = max(info['stops'], 1)
        avg_segment_km = route_distance_km / num_segments if num_segments > 0 else 0

        for stop_idx in range(1, info['stops'] + 1):
            cumulative_km += avg_segment_km
            hours_elapsed = cumulative_km / avg_speed if avg_speed > 0 else 0
            arrival_time = base_time + timedelta(hours=hours_elapsed)
            departure_time = arrival_time + timedelta(minutes=10)

            gantt_data.append({
                'Maşın': f"Maşın {info['vehicle_id']}",
                'Başlanğıc': arrival_time,
                'Son': departure_time,
                'Dayanacaq': f"#{stop_idx}"
            })

    if not gantt_data:
        return None

    gantt_df = pd.DataFrame(gantt_data)
    fig = px.timeline(
        gantt_df, x_start='Başlanğıc', x_end='Son', y='Maşın', color='Maşın',
        hover_data=['Dayanacaq']
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=350, showlegend=False)
    return fig


# ============================================
# BAŞLIQ
# ============================================
st.markdown("""
<div style="padding: 20px 0 10px 0;">
    <h1 style="margin-bottom: 0;">🚚 RouteOptimizer Pro</h1>
    <p style="font-size: 16px; color: #555; margin-top: 4px;">
        Sənaye səviyyəli Vehicle Routing Problem həlli — Google OR-Tools, real yol şəbəkəsi (OSRM) 
        və çox-meyarlı optimallaşdırma ilə
    </p>
</div>
""", unsafe_allow_html=True)
import base64

def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    bg_image = get_base64_image("assets/truck_bg.jpg")
    st.markdown(f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(10, 15, 25, 0.91), rgba(10, 15, 25, 0.91)),
                           url("data:image/jpeg;base64,{bg_image}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    </style>
    """, unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ============================================
# SIDEBAR — PARAMETRLƏR
# ============================================
st.sidebar.image("assets/truck_bg.jpg", use_container_width=True)
st.sidebar.header("⚙️ Parametrlər")

num_vehicles = st.sidebar.slider(
    "Nəqliyyat vasitəsi sayı",
    min_value=2, max_value=10, value=5, step=1
)

balance_priority = st.sidebar.slider(
    "Yük Balansı Prioriteti",
    min_value=0, max_value=100, value=0, step=10,
    help="0 = yalnız minimum məsafə fokuslanır. 100 = maşınlar arasında bərabər yük bölgüsünə üstünlük verir."
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Ümumi çatdırılma nöqtəsi:** {len(df) - 1}")
st.sidebar.markdown(f"**Ümumi sifariş həcmi:** {df['demand'].sum()}")
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Xərc Parametrləri")
fuel_price = st.sidebar.number_input("Yanacaq qiyməti (₼/km)", min_value=0.0, value=0.35, step=0.05)
driver_wage = st.sidebar.number_input("Sürücü saatlıq maaşı (₼/saat)", min_value=0.0, value=8.0, step=0.5)
avg_speed = st.sidebar.number_input("Orta sürət (km/saat)", min_value=5, value=30, step=5)

progress_placeholder = st.empty()
progress_bar = progress_placeholder.progress(0, text="Başlanğıc marşrut qurulur...")
progress_bar.progress(30, text="Capacity məhdudiyyətləri tətbiq olunur...")
progress_bar.progress(55, text="Guided Local Search ilə optimallaşdırılır (bu addım ən çox vaxt aparır)...")

routes_info = solve_vrp_cached(
    num_vehicles,
    tuple(df['demand'].tolist()),
    tuple(map(tuple, distance_matrix.tolist())),
    balance_weight=balance_priority
)

progress_bar.progress(100, text="Tamamlandı.")
progress_placeholder.empty()

used_vehicles_count = sum(1 for r in routes_info if r['stops'] > 0)

st.sidebar.markdown("---")
st.sidebar.subheader("🚛 Görünən Maşınlar")
st.sidebar.caption(
    f"Solver {used_vehicles_count}/{num_vehicles} maşını faktiki istifadə edir "
    "(ümumi məsafəni minimuma endirmək üçün boş maşın saxlanmır)."
)

active_vehicles = []
for info in routes_info:
    vid = info['vehicle_id']
    checked = st.sidebar.checkbox(
        f"Maşın {vid} ({info['stops']} dayanacaq, {info['distance']/1000:.1f} km)",
        value=True,
        key=f"vehicle_{vid}"
    )
    if checked:
        active_vehicles.append(vid)

# ============================================
# KPI KARTLARI
# ============================================
total_distance = sum(r['distance'] for r in routes_info if r['vehicle_id'] in active_vehicles)
total_load = sum(r['load'] for r in routes_info if r['vehicle_id'] in active_vehicles)
active_count = len(active_vehicles)

active_loads = [r['load'] for r in routes_info if r['vehicle_id'] in active_vehicles and r['stops'] > 0]
load_balance_score = float(np.std(active_loads)) if len(active_loads) > 1 else 0.0

total_distance_km = total_distance / 1000
estimated_hours = total_distance_km / avg_speed if avg_speed > 0 else 0
fuel_cost = total_distance_km * fuel_price
labor_cost = estimated_hours * driver_wage
total_operational_cost = fuel_cost + labor_cost

col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
col1.metric("Aktiv Maşınlar", f"{active_count}")
col2.metric("Ümumi Məsafə", f"{total_distance_km:.2f} km")
col3.metric("Ümumi Yük", f"{total_load} vahid")
col4.metric("Orta Məsafə/Maşın", f"{(total_distance_km/active_count if active_count > 0 else 0):.2f} km")
col5.metric(
    "Yük Balans Göstəricisi (std)", f"{load_balance_score:.1f}",
    help="İstifadə olunan maşınların yükü arasındakı standart sapma. Aşağı dəyər = daha bərabər bölgü."
)
col6.metric(
    "Təxmini Əməliyyat Xərci", f"{total_operational_cost:.2f} ₼",
    help=f"Yanacaq: {fuel_cost:.2f} ₼ + Əməkhaqqı: {labor_cost:.2f} ₼ (təxmini {estimated_hours:.1f} saat)"
)
estimated_co2_kg = total_distance_km * 0.8
col7.metric(
    "Təxmini CO2 Emissiyası", f"{estimated_co2_kg:.1f} kg",
    help="Orta hesabla 0.8 kg CO2/km əmsalı ilə hesablanıb (yüngül yük maşını üçün təxmini dəyər)."
)

# ============================================
# XƏRİTƏ
# ============================================
st.subheader("🗺️ Marşrut Xəritəsi")

map_type = st.radio(
    "Xəritə növü:",
    ["Statik (nömrələnmiş dayanacaqlar)", "Animasiyalı (canlı hərəkət)"],
    horizontal=True
)
try:
    import requests as _req_check
    _test_response = _req_check.get("http://router.project-osrm.org/route/v1/driving/49.85,40.40;49.86,40.41", timeout=4)
    osrm_available = _test_response.status_code == 200
except Exception:
    osrm_available = False

if not osrm_available:
    st.warning("⚠️ OSRM serverinə əlaqə qurulmadı — marşrutlar düz xətt (approximation) ilə göstəriləcək.")
with st.spinner("Real yol marşrutları yüklənir (OSRM)..."):
    if map_type == "Statik (nömrələnmiş dayanacaqlar)":
        m = create_static_map(df, routes_info, active_vehicles)
    else:
        m = create_animated_map(df, routes_info, active_vehicles)

st_folium(m, width=1400, height=550)
st.subheader("⏱️ Çatdırılma Vaxt Qrafiki")
st.caption(f"Bütün marşrutlar saat 08:00-da başlayır, {avg_speed} km/saat orta sürətlə hesablanıb (təxmini).")
gantt_fig = create_gantt_chart(routes_info, active_vehicles, avg_speed)
if gantt_fig:
    st.plotly_chart(gantt_fig, use_container_width=True)
else:
    st.caption("Göstəriləcək aktiv marşrut yoxdur.")

# ============================================
# MARŞRUT DETALLARI (sağlamlıq göstəricisi ilə)
# ============================================
st.subheader("📋 Marşrut Detalları")

vehicle_capacity_estimate = calculate_vehicle_capacity(int(df['demand'].sum()), num_vehicles)

table_data = []
for info in routes_info:
    fill_ratio = info['load'] / vehicle_capacity_estimate if vehicle_capacity_estimate > 0 else 0

    if info['stops'] == 0:
        health = "⚪ İstifadə olunmur"
    elif fill_ratio >= 0.9:
        health = "🔴 Həddə yaxın"
    elif fill_ratio <= 0.3:
        health = "🟡 Az yüklü"
    else:
        health = "🟢 Normal"

    table_data.append({
        'Maşın': info['vehicle_id'],
        'Dayanacaq Sayı': info['stops'],
        'Məsafə (km)': round(info['distance']/1000, 2),
        'Yük': info['load'],
        'Doluluq (%)': round(fill_ratio * 100, 1),
        'Sağlamlıq': health,
        'Aktiv': '✅' if info['vehicle_id'] in active_vehicles else '❌'
    })

results_df = pd.DataFrame(table_data)
st.dataframe(results_df, width='stretch')
st.caption(
    "Doluluq faizi, hər maşının təxmini tutumuna (ümumi tələb / maşın sayı + buffer) nisbətdə hesablanır. "
    "🔴 90%+ = həddə yaxın, 🟡 ≤30% = az yüklü, 🟢 aralıqda = normal, ⚪ = maşın istifadə olunmayıb."
)
with st.expander("🔍 Bu marşrutlar niyə belə seçildi?"):
    for info in routes_info:
        if info['stops'] == 0:
            continue
        fill_pct = (info['load'] / vehicle_capacity_estimate * 100) if vehicle_capacity_estimate > 0 else 0
        st.markdown(
            f"**Maşın {info['vehicle_id']}** — {info['stops']} dayanacaq, "
            f"{info['distance']/1000:.2f} km. Kapasitet doluluğu {fill_pct:.0f}% olduğu üçün "
            f"{'əlavə sifariş qəbul edə bilər' if fill_pct < 70 else 'kapasitetə yaxındır, yeni sifariş üçün uyğun deyil'}. "
            f"Marşrut, Guided Local Search alqoritmi ilə coğrafi yaxınlıq və yük məhdudiyyəti "
            f"əsasında optimallaşdırılıb."
        )

csv = results_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Nəticələri CSV kimi endir",
    data=csv,
    file_name='vrp_results.csv',
    mime='text/csv'
)

# ============================================
# KONFİQURASİYA TARİXÇƏSİ
# ============================================
st.markdown("---")
st.subheader("🗂️ Konfiqurasiya Tarixçəsi")
st.markdown(
    "Sınadığın parametr kombinasiyalarını bura saxlayıb, nəticələri yan-yana müqayisə edə bilərsən."
)

if 'config_history' not in st.session_state:
    st.session_state.config_history = []

col_save, col_clear = st.columns([1, 1])

with col_save:
    if st.button("💾 Cari Nəticəni Tarixçəyə Əlavə Et"):
        st.session_state.config_history.append({
            'Maşın Sayı': num_vehicles,
            'Balans Prioriteti': balance_priority,
            'Ümumi Məsafə (km)': round(total_distance / 1000, 2),
            'Yük Balans (std)': round(load_balance_score, 1),
            'Faktiki İstifadə Olunan Maşın': used_vehicles_count
        })

with col_clear:
    if st.button("🗑️ Tarixçəni Təmizlə"):
        st.session_state.config_history = []

if st.session_state.config_history:
    history_df = pd.DataFrame(st.session_state.config_history)

    if len(history_df) >= 2:
        min_idx = history_df['Ümumi Məsafə (km)'].idxmin()

        def highlight_best(row):
            if row.name == min_idx:
                return ['background-color: #d4f4dd'] * len(row)
            return [''] * len(row)

        st.caption("Ən aşağı məsafəli sətir yaşıl arxa fonla vurğulanır.")
        st.dataframe(history_df.style.apply(highlight_best, axis=1), width='stretch')
    else:
        st.dataframe(history_df, width='stretch')
else:
    st.caption("Hələ heç bir konfiqurasiya saxlanmayıb.")

# ============================================
# DİNAMİK YENİDƏN-OPTİMALLAŞDIRMA
# ============================================
st.markdown("---")
st.subheader("🔄 Dinamik Yenidən-Optimallaşdırma (Real-Time Simulyasiya)")
st.markdown(
    "Bu bölmə, canlı bir sifarişin sistemə necə inteqrasiya olunduğunu simulyasiya edir — "
    "bütün marşrutu sıfırdan hesablamaq əvəzinə, yeni sifarişi ən uyğun mövcud marşruta əlavə edir."
)

if st.button("🆕 Yeni Sifariş Simulyasiya Et"):
    with st.spinner("Yeni sifariş üçün ən yaxşı marşrut axtarılır..."):
        np.random.seed(None)
        new_lat = np.random.uniform(40.37, 40.41)
        new_lon = np.random.uniform(49.83, 49.87)
        new_demand = np.random.randint(1, 8)

        st.info(f"📍 Yeni sifariş daxil oldu: koordinat ({new_lat:.4f}, {new_lon:.4f}), həcm: {new_demand} vahid")

        best_vehicle = None
        best_position = None
        best_extra_cost = float('inf')

        for info in routes_info:
            if info['vehicle_id'] not in active_vehicles:
                continue

            route = info['route']

            for pos in range(1, len(route)):
                prev_point = route[pos - 1]
                next_point = route[pos]

                prev_lat, prev_lon = df.loc[prev_point, 'latitude'], df.loc[prev_point, 'longitude']
                next_lat, next_lon = df.loc[next_point, 'latitude'], df.loc[next_point, 'longitude']

                old_segment = haversine(prev_lat, prev_lon, next_lat, next_lon)
                new_segment_1 = haversine(prev_lat, prev_lon, new_lat, new_lon)
                new_segment_2 = haversine(new_lat, new_lon, next_lat, next_lon)

                extra_cost = (new_segment_1 + new_segment_2) - old_segment

                if extra_cost < best_extra_cost:
                    best_extra_cost = extra_cost
                    best_vehicle = info['vehicle_id']
                    best_position = pos

        if best_vehicle is not None:
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Təyin Edilən Maşın", f"Maşın {best_vehicle}")
            col_b.metric("Əlavə Məsafə", f"{best_extra_cost/1000:.2f} km")
            col_c.metric("Marşrutda Mövqe", f"{best_position}-ci dayanacaqdan sonra")

            st.success(
                f"✅ Yeni sifariş **Maşın {best_vehicle}**-in marşrutuna, "
                f"{best_position}-ci mövqeyə əlavə edildi. "
                f"Bu, bütün sistemi yenidən hesablamaq əvəzinə, yalnız **{best_extra_cost/1000:.2f} km** "
                f"əlavə məsafə ilə həll edildi."
            )
        else:
            st.warning("Uyğun maşın tapılmadı — bütün maşınlar seçilməyib və ya kapasitet dolu ola bilər.")

# ============================================
# SENSİTİVİTY ANALİZ
# ============================================
st.markdown("---")
st.subheader("📊 Sensitivity Analiz: Maşın Sayının Təsiri")
st.markdown(
    f"Bu bölmə, cari Yük Balansı Prioriteti dəyəri ilə ({balance_priority}), "
    "nəqliyyat vasitəsi sayının ümumi məsafəyə təsirini göstərir."
)

run_sensitivity = st.button("Sensitivity Analizini İşə Sal (2-10 maşın)")

if run_sensitivity:
    with st.spinner("Fərqli ssenarilər hesablanır, hər biri GLS ilə optimallaşdırılır..."):
        sensitivity_results = []
        demands_tuple = tuple(df['demand'].tolist())
        dist_tuple = tuple(map(tuple, distance_matrix.tolist()))

        for v in range(2, 11):
            result = solve_vrp_cached(v, demands_tuple, dist_tuple, balance_weight=balance_priority)
            total_dist = sum(r['distance'] for r in result)
            sensitivity_results.append({
                'Maşın Sayı': v,
                'Ümumi Məsafə (km)': round(total_dist / 1000, 2)
            })

        sens_df = pd.DataFrame(sensitivity_results)
        sens_df['Əvvəlki ilə fərq (km)'] = sens_df['Ümumi Məsafə (km)'].diff().fillna(0)
        sens_df['Marginal Qənaət (%)'] = (
            -sens_df['Əvvəlki ilə fərq (km)'] / sens_df['Ümumi Məsafə (km)'].shift(1) * 100
        ).fillna(0).round(1)

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            st.line_chart(sens_df.set_index('Maşın Sayı')['Ümumi Məsafə (km)'])

        with col_table:
            st.dataframe(sens_df, width='stretch', hide_index=True)

        optimal_candidates = sens_df[sens_df['Marginal Qənaət (%)'] < 5]
        if not optimal_candidates.empty:
            optimal_row = optimal_candidates.iloc[0]
            st.info(
                f"💡 **Analitik Tövsiyə:** {int(optimal_row['Maşın Sayı'])} maşından sonra, "
                f"əlavə hər maşın ümumi məsafəyə 5%-dən az təsir edir (diminishing returns)."
            )

st.markdown("---")
st.markdown("*Layihə: [GitHub-da bax](https://github.com/sukurlufaiq3521-rgb/last-mile-vrp-optimization)*")