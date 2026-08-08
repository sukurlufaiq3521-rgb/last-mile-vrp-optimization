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

st.set_page_config(
    page_title="Last-Mile Delivery VRP Optimizer",
    page_icon="🚚",
    layout="wide"
)


@st.cache_data
def load_data():
    df = pd.read_csv('data/delivery_points.csv')
    distance_matrix = np.load('data/distance_matrix.npy')
    return df, distance_matrix


df, distance_matrix = load_data()

COLORS = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
          '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5']


def solve_vrp(num_vehicles, demands, dist_matrix, depot=0, balance_weight=0):
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

    if balance_weight > 0:
        capacity_dimension = routing.GetDimensionOrDie('Capacity')
        for vehicle_id in range(num_vehicles):
            capacity_dimension.SetSpanCostCoefficientForVehicle(
                int(balance_weight), vehicle_id)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.FromSeconds(10)

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
                    'fillColor': color, 'fillOpacity': 0.9,
                    'stroke': 'true', 'radius': 7
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


st.title("🚚 Last-Mile Delivery Route Optimizer")
st.markdown("**Vehicle Routing Problem (VRP)** — Python & Google OR-Tools ilə interaktiv marşrut optimallaşdırması")

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

with st.spinner("Marşrutlar hesablanır (Guided Local Search optimallaşdırması, ~10 saniyə)..."):
    routes_info = solve_vrp(num_vehicles, df['demand'].tolist(), distance_matrix, balance_weight=balance_priority)

st.sidebar.markdown("---")
st.sidebar.subheader("🚛 Görünən Maşınlar")

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

total_distance = sum(r['distance'] for r in routes_info if r['vehicle_id'] in active_vehicles)
total_load = sum(r['load'] for r in routes_info if r['vehicle_id'] in active_vehicles)
active_count = len(active_vehicles)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Aktiv Maşınlar", f"{active_count}")
col2.metric("Ümumi Məsafə", f"{total_distance/1000:.2f} km")
col3.metric("Ümumi Yük", f"{total_load} vahid")
col4.metric("Orta Məsafə/Maşın", f"{(total_distance/1000/active_count if active_count > 0 else 0):.2f} km")

st.subheader("🗺️ Marşrut Xəritəsi")

map_type = st.radio(
    "Xəritə növü:",
    ["Statik (nömrələnmiş dayanacaqlar)", "Animasiyalı (canlı hərəkət)"],
    horizontal=True
)

with st.spinner("Real yol marşrutları yüklənir (OSRM)..."):
    if map_type == "Statik (nömrələnmiş dayanacaqlar)":
        m = create_static_map(df, routes_info, active_vehicles)
    else:
        m = create_animated_map(df, routes_info, active_vehicles)

st_folium(m, width=1400, height=550)

st.subheader("📋 Marşrut Detalları")
table_data = []
for info in routes_info:
    table_data.append({
        'Maşın': info['vehicle_id'],
        'Dayanacaq Sayı': info['stops'],
        'Məsafə (km)': round(info['distance']/1000, 2),
        'Yük': info['load'],
        'Aktiv': '✅' if info['vehicle_id'] in active_vehicles else '❌'
    })

results_df = pd.DataFrame(table_data)
st.dataframe(results_df, use_container_width=True)

csv = results_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Nəticələri CSV kimi endir",
    data=csv,
    file_name='vrp_results.csv',
    mime='text/csv'
)

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

                def haversine(lat1, lon1, lat2, lon2):
                    R = 6371000
                    phi1, phi2 = np.radians(lat1), np.radians(lat2)
                    dphi = np.radians(lat2 - lat1)
                    dlambda = np.radians(lon2 - lon1)
                    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
                    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

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
                f"əlavə məsafə ilə həll edildi — tam yenidən optimallaşdırmaya nisbətən çox daha sürətli yanaşma."
            )
        else:
            st.warning("Uyğun maşın tapılmadı — bütün maşınlar seçilməyib və ya kapasitet dolu ola bilər.")

st.markdown("---")
st.subheader("📊 Sensitivity Analiz: Maşın Sayının Təsiri")
st.markdown("Bu bölmə, nəqliyyat vasitəsi sayının ümumi məsafəyə təsirini göstərir — filo ölçüsü qərarları üçün analitik dəstək.")

run_sensitivity = st.button("Sensitivity Analizini İşə Sal (2-10 maşın)")

if run_sensitivity:
    with st.spinner("Fərqli ssenarilər hesablanır, hər biri GLS ilə optimallaşdırılır..."):
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
        sens_df['Əvvəlki ilə fərq (km)'] = sens_df['Ümumi Məsafə (km)'].diff().fillna(0)
        sens_df['Marginal Qənaət (%)'] = (
            -sens_df['Əvvəlki ilə fərq (km)'] / sens_df['Ümumi Məsafə (km)'].shift(1) * 100
        ).fillna(0).round(1)

        col_chart, col_table = st.columns([2, 1])

        with col_chart:
            st.line_chart(sens_df.set_index('Maşın Sayı')['Ümumi Məsafə (km)'])

        with col_table:
            st.dataframe(sens_df, use_container_width=True, hide_index=True)

        optimal_candidates = sens_df[sens_df['Marginal Qənaət (%)'] < 5]
        if not optimal_candidates.empty:
            optimal_row = optimal_candidates.iloc[0]
            st.info(
                f"💡 **Analitik Tövsiyə:** {int(optimal_row['Maşın Sayı'])} maşından sonra, "
                f"əlavə hər maşın ümumi məsafəyə 5%-dən az təsir edir (diminishing returns). "
                f"Bu, filo ölçüsü qərarları üçün maya dəyəri/fayda balansını göstərir."
            )

st.markdown("---")
st.markdown("*Layihə: [GitHub-da bax](https://github.com/sukurlufaiq3521-rgb/last-mile-vrp-optimization)*")