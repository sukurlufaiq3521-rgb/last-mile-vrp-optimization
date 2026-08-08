import numpy as np
import pandas as pd
import folium
from folium.plugins import TimestampedGeoJson
import sys
sys.path.append('src')
from osrm_helper import load_cache, save_cache, get_full_route_geometry
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from datetime import datetime, timedelta


def create_data_model():
    data = {}
    distance_matrix = np.load('data/distance_matrix.npy')
    data['distance_matrix'] = distance_matrix.tolist()

    df = pd.read_csv('data/delivery_points.csv')
    data['demands'] = df['demand'].tolist()

    data['num_vehicles'] = 5
    data['depot'] = 0

    total_demand = sum(data['demands'])
    data['vehicle_capacities'] = [total_demand // data['num_vehicles'] + 20] * data['num_vehicles']

    return data, df


def solve_vrp(data):
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index, 0, data['vehicle_capacities'], True, 'Capacity')

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)

    routes_info = []
    if solution:
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            route_distance = 0
            route_load = 0
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route.append(node_index)
                route_load += data['demands'][node_index]
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


def create_animated_features(df, routes_info, cache, colors):
    features = []
    base_time = datetime(2026, 1, 1, 8, 0, 0)

    for info in routes_info:
        vehicle_id = info['vehicle_id']
        route = info['route']
        color = colors[vehicle_id % len(colors)]

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
            'geometry': {
                'type': 'LineString',
                'coordinates': coordinates
            },
            'properties': {
                'times': times,
                'style': {
                    'color': color,
                    'weight': 4,
                    'opacity': 0.8
                },
                'icon': 'circle',
                'iconstyle': {
                    'fillColor': color,
                    'fillOpacity': 0.9,
                    'stroke': 'true',
                    'radius': 7
                }
            }
        }
        features.append(feature)

    return features


def main():
    data, df = create_data_model()
    routes_info = solve_vrp(data)

    cache = load_cache()

    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']
    color_names = ['Qirmizi', 'Mavi', 'Yasil', 'Benovseyi', 'Narinci']

    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']

    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')

    # Depot marker
    folium.Marker(
        [depot_lat, depot_lon],
        popup='Anbar (Depot)',
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)

    # Statik dayanacaq nöqtələri (nömrələnmiş) - animasiyanın arxa planında görünsün
    for info in routes_info:
        vehicle_id = info['vehicle_id']
        color = colors[vehicle_id % len(colors)]
        stop_number = 0

        for point_id in info['route']:
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
                    popup=f"Noqte #{point_id} | Masin {vehicle_id} | {stop_number}-ci dayanacaq | Sifaris: {demand}"
                ).add_to(m)

    print("Animasiya ucun marsrut hendeseleri hazirlanir...")
    features = create_animated_features(df, routes_info, cache, colors)
    save_cache(cache)

    TimestampedGeoJson(
        {
            'type': 'FeatureCollection',
            'features': features
        },
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

    total_distance = sum(r['distance'] for r in routes_info)
    naive_distance = 164470  # bilinen deyerdi
    improvement_pct = ((naive_distance - total_distance) / naive_distance) * 100

    # Statistika qutusu
    stats_html = f"""
    <div style="
        position: fixed;
        top: 10px; left: 50px;
        width: 260px;
        background-color: white;
        border: 2px solid #333;
        border-radius: 8px;
        padding: 12px;
        font-family: Arial, sans-serif;
        font-size: 13px;
        z-index: 9999;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    ">
        <b>Last-Mile Delivery Optimization</b><br>
        <hr style="margin: 6px 0;">
        80 catdirilma noqtesi | 5 neqliyyat vasitesi<br>
        <b>Umumi mesafe: {total_distance/1000:.2f} km</b><br>
        <span style="color: green;"><b>Naive-e nisbeten: {improvement_pct:.0f}% qenaet</b></span><br>
        <hr style="margin: 6px 0;">
        <span style="font-size: 11px; color: #666;">Asagidaki Play dugmesine basaraq animasiyaya baxin</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(stats_html))

    # Legend
    legend_html = '<div style="position: fixed; top: 10px; right: 10px; width: 230px; background-color: white; border: 2px solid #333; border-radius: 8px; padding: 12px; font-family: Arial, sans-serif; font-size: 12px; z-index: 9999; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"><b>Marsrutlar</b><br><hr style="margin: 6px 0;">'
    legend_html += 'Anbar (Depot)<br>'
    for info in routes_info:
        vid = info['vehicle_id']
        legend_html += f'<span style="color:{colors[vid]};">&#9679;</span> Masin {vid} ({color_names[vid]}) - {info["stops"]} noqte, {info["distance"]/1000:.1f} km<br>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))

    m.save('outputs/animated_map.html')
    print("Tam sintez edilmis animasiyali xerite yaradildi!")
    print(f"Umumi mesafe: {total_distance/1000:.2f} km")
    print("Fayl: outputs/animated_map.html")


if __name__ == '__main__':
    main()