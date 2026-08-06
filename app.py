import streamlit as st
import pandas as pd
import numpy as np
import folium
import sys
sys.path.append('src')
from osrm_helper import load_cache, save_cache, get_full_route_geometry
from streamlit_folium import st_folium
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# SƏHİFƏ TƏNZİMLƏMƏLƏRİ
# ============================================
st.set_page_config(
    page_title="Last-Mile Delivery VRP Optimizer",
    page_icon="🚚",
    layout="wide"
)

# ============================================
# DATA YÜKLƏMƏ
# ============================================
@st.cache_data
def load_data():
    df = pd.read_csv('data/delivery_points.csv')
    distance_matrix = np.load('data/distance_matrix.npy')
    return df, distance_matrix

df, distance_matrix = load_data()

# ============================================
# VRP HƏLLİ FUNKSİYASI
# ============================================
def solve_vrp(num_vehicles, demands, dist_matrix, depot=0):
    total_demand = sum(demands)
    vehicle_capacities = [total_demand // num_vehicles + 20] * num_vehicles

    manager = pywrapcp.RoutingIndexManager(len(dist_matrix), num_vehicles, depot)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(dist_matrix[from_node][to_node])

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return int(demands[from_node])

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, vehicle_capacities, True, 'Capacity')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    routes_info = []
    if solution:
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            route_load = 0

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route.append(node_index)
                route_load += demands[node_index]
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            route.append(manager.IndexToNode(index))

            routes_info.append({
                'vehicle_id': vehicle_id,
                'route': route,
                'distance': route_distance,
                'load': route_load,
                'stops': len(route) - 2
            })

    return routes_info

# ============================================
# XƏRİTƏ YARATMA FUNKSİYASI (OSRM İLƏ)
# ============================================
def create_map(df, routes_info, active_vehicles):
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')

    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
              '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5']

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
        color = colors[vehicle_id % len(colors)]

        real_route_coords = get_full_route_geometry(route, df, cache)

        for point_id in route:
            if point_id != 0:
                lat = df.loc[point_id, 'latitude']
                lon = df.loc[point_id, 'longitude']
                folium.CircleMarker(
                    [lat, lon],
                    radius=5,
                    popup=f"Nöqtə {point_id} | Maşın {vehicle_id}",
                    color=color,
                    fill=True,
                    fillColor=color
                ).add_to(m)

        folium.PolyLine(
            real_route_coords, color=color, weight=3, opacity=0.8
        ).add_to(m)

    save_cache(cache)

    return m

# ============================================
# BAŞLIQ
# ============================================
st.title("Last-Mile Delivery Route Optimizer")
st.markdown("**Vehicle Routing Problem (VRP)** - Python & Google OR-Tools ilə interaktiv marşrut optimallaşdırması")

# ============================================
# YAN PANEL - PARAMETRLƏR
# ============================================
st.sidebar.header("Parametrlər")

num_vehicles = st.sidebar.slider(
    "Nəqliyyat vasitəsi sayı",
    min_value=2, max_value=10, value=5, step=1
)

st.sidebar.markdown("---")
st.sidebar.markdown(f"**Ümumi çatdırılma nöqtəsi:** {len(df) - 1}")
st.sidebar.markdown(f"**Ümumi sifariş həcmi:** {df['demand'].sum()}")

# ============================================
# VRP HƏLLİNİ HESABLA
# ============================================
with st.spinner("Marşrutlar hesablanır..."):
    routes_info = solve_vrp(num_vehicles, df['demand'].tolist(), distance_matrix)

# ============================================
# MAŞIN SEÇİMİ
# ============================================
st.sidebar.markdown("---")
st.sidebar.subheader("Görünən Maşınlar")

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

col1, col2, col3, col4 = st.columns(4)
col1.metric("Aktiv Maşınlar", f"{active_count}")
col2.metric("Ümumi Məsafə", f"{total_distance/1000:.2f} km")
col3.metric("Ümumi Yük", f"{total_load} vahid")
col4.metric("Orta Məsafə/Maşın", f"{(total_distance/1000/active_count if active_count > 0 else 0):.2f} km")

# ============================================
# XƏRİTƏ
# ============================================
st.subheader("Marşrut Xəritəsi (Real Yol Şəbəkəsi)")
with st.spinner("Real yol marşrutları yüklənir (OSRM)..."):
    m = create_map(df, routes_info, active_vehicles)
st_folium(m, width=1400, height=550)

# ============================================
# MARŞRUT CƏDVƏLİ
# ============================================
st.subheader("Marşrut Detalları")
table_data = []
for info in routes_info:
    table_data.append({
        'Maşın': info['vehicle_id'],
        'Dayanacaq Sayı': info['stops'],
        'Məsafə (km)': round(info['distance']/1000, 2),
        'Yük': info['load'],
        'Aktiv': 'Bəli' if info['vehicle_id'] in active_vehicles else 'Xeyr'
    })

results_df = pd.DataFrame(table_data)
st.dataframe(results_df, use_container_width=True)

# ============================================
# CSV YÜKLƏMƏ DÜYMƏSİ
# ============================================
csv = results_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Nəticələri CSV kimi endir",
    data=csv,
    file_name='vrp_results.csv',
    mime='text/csv'
)

st.markdown("---")
st.markdown("*Layihə: [GitHub-da bax](https://github.com/sukurlufaiq3521-rgb/last-mile-vrp-optimization)*")
# ============================================
# SENSİTİVİTY ANALİZ PANELİ
# ============================================
st.markdown("---")
st.subheader("📊 Sensitivity Analiz: Maşın Sayının Təsiri")
st.markdown("Bu bölmə, nəqliyyat vasitəsi sayının ümumi məsafəyə təsirini göstərir — filo ölçüsü qərarları üçün analitik dəstək.")

run_sensitivity = st.button("Sensitivity Analizini İşə Sal (2-10 maşın)")

if run_sensitivity:
    with st.spinner("Fərqli ssenarilər hesablanır, bu bir neçə saniyə çəkə bilər..."):
        sensitivity_results = []
        demands_list = df['demand'].tolist()

        for v in range(2, 11):
            result = solve_vrp(v, demands_list, distance_matrix)
            total_dist = sum(r['distance'] for r in result)
            sensitivity_results.append({
                'Maşın Sayı': v,
                'Ümumi Məsafə (km)': round(total_dist / 1000, 2)
            })

        sens_df = pd.DataFrame(sensitivity_results)

        # Marginal qənaəti hesablayaq (hər əlavə maşının gətirdiyi fayda)
        sens_df['Əvvəlki ilə fərq (km)'] = sens_df['Ümumi Məsafə (km)'].diff().fillna(0)
        sens_df['Marginal Qənaət (%)'] = (
            -sens_df['Əvvəlki ilə fərq (km)'] / sens_df['Ümumi Məsafə (km)'].shift(1) * 100
        ).fillna(0).round(1)

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            st.line_chart(sens_df.set_index('Maşın Sayı')['Ümumi Məsafə (km)'])

        with col_table:
            st.dataframe(sens_df, use_container_width=True, hide_index=True)

        # Optimal nöqtəni tapaq (marginal qənaət 5%-dən aşağı düşdüyü ilk nöqtə)
        optimal_candidates = sens_df[sens_df['Marginal Qənaət (%)'] < 5]
        if not optimal_candidates.empty and len(optimal_candidates) > 0:
            optimal_row = optimal_candidates.iloc[0]
            st.info(
                f"💡 **Analitik Tövsiyə:** {int(optimal_row['Maşın Sayı'])} maşından sonra, "
                f"əlavə hər maşın ümumi məsafəyə 5%-dən az təsir edir (diminishing returns). "
                f"Bu, filo ölçüsü qərarları üçün maya dəyəri/fayda balansını göstərir."
            )