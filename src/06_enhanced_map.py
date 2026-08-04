import numpy as np
import pandas as pd
import folium
from folium import plugins
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# 1. DATA VƏ VRP HƏLLİ (əvvəlki addımlardan)
# ============================================
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
    return manager, routing, solution

def get_routes_with_details(data, manager, routing, solution, distance_matrix):
    """Hər maşının marşrutunu, məsafəsini və yükünü qaytarır"""
    routes_info = []
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
            'load': route_load
        })
    return routes_info

# ============================================
# 2. ZƏNGİNLƏŞDİRİLMİŞ XƏRİTƏ YARATMAQ
# ============================================
def create_enhanced_map(df, routes_info, total_distance, improvement_pct):
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']
    
    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')
    
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']
    color_names = ['Qırmızı', 'Mavi', 'Yaşıl', 'Bənövşəyi', 'Narıncı']
    
    # --- Depot (Anbar) ---
    folium.Marker(
        [depot_lat, depot_lon],
        popup='<b>🏠 ANBAR (Depot)</b><br>Bütün marşrutların başlanğıc/bitiş nöqtəsi',
        icon=folium.Icon(color='black', icon='home', prefix='fa')
    ).add_to(m)
    
    # --- Hər maşının marşrutu ---
    for info in routes_info:
        vehicle_id = info['vehicle_id']
        route = info['route']
        color = colors[vehicle_id % len(colors)]
        
        route_coords = []
        stop_number = 0
        
        for point_id in route:
            lat = df.loc[point_id, 'latitude']
            lon = df.loc[point_id, 'longitude']
            route_coords.append([lat, lon])
            
            if point_id != 0:
                stop_number += 1
                demand = df.loc[point_id, 'demand']
                
                # Nömrələnmiş dairə - DivIcon ilə rəqəm yazırıq
                folium.Marker(
                    [lat, lon],
                    icon=folium.DivIcon(html=f"""
                        <div style="
                            background-color: {color};
                            color: white;
                            border-radius: 50%;
                            width: 24px;
                            height: 24px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 11px;
                            font-weight: bold;
                            border: 2px solid white;
                            box-shadow: 0 0 3px rgba(0,0,0,0.5);
                        ">{stop_number}</div>
                    """),
                    popup=f"""
                        <b>📍 Çatdırılma Nöqtəsi #{point_id}</b><br>
                        Maşın: {color_names[vehicle_id]}<br>
                        Ardıcıllıq: {stop_number}-ci dayanacaq<br>
                        Sifariş həcmi: {demand} vahid
                    """
                ).add_to(m)
        
        # Marşrut xətti
        folium.PolyLine(
            route_coords,
            color=color,
            weight=3,
            opacity=0.8,
            popup=f"<b>Maşın {vehicle_id} ({color_names[vehicle_id]})</b><br>Məsafə: {info['distance']/1000:.2f} km<br>Yük: {info['load']} vahid"
        ).add_to(m)
    
    # --- Statistika qutusu (yuxarı sol) ---
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
        <b>📦 Last-Mile Delivery Optimization</b><br>
        <hr style="margin: 6px 0;">
        80 çatdırılma nöqtəsi | 5 nəqliyyat vasitəsi<br>
        <b>Ümumi məsafə: {total_distance/1000:.2f} km</b><br>
        <span style="color: green;"><b>Naive-ə nisbətən: {improvement_pct:.0f}% qənaət</b></span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(stats_html))
    
    # --- Legend (yuxarı sağ) ---
    legend_html = '<div style="position: fixed; top: 10px; right: 10px; width: 220px; background-color: white; border: 2px solid #333; border-radius: 8px; padding: 12px; font-family: Arial, sans-serif; font-size: 12px; z-index: 9999; box-shadow: 0 2px 8px rgba(0,0,0,0.3);"><b>🗺️ Marşrutlar</b><br><hr style="margin: 6px 0;">'
    legend_html += '🏠 Anbar (Depot)<br>'
    for info in routes_info:
        vid = info['vehicle_id']
        legend_html += f'<span style="color:{colors[vid]};">●</span> Maşın {vid} — {len(info["route"])-2} nöqtə, {info["distance"]/1000:.1f} km<br>'
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    return m

# ============================================
# 3. ƏSAS PROQRAM
# ============================================
def main():
    data, df = create_data_model()
    manager, routing, solution = solve_vrp(data)
    
    if solution:
        routes_info = get_routes_with_details(data, manager, routing, solution, data['distance_matrix'])
        total_distance = sum(r['distance'] for r in routes_info)
        
        # Naive məsafəni yenidən hesablayırıq (improvement % üçün)
        naive_distance = 427741  # əvvəlki addımdan bilinən dəyər
        improvement_pct = ((naive_distance - total_distance) / naive_distance) * 100
        
        m = create_enhanced_map(df, routes_info, total_distance, improvement_pct)
        m.save('outputs/enhanced_route_map.html')
        
        print("Zənginləşdirilmiş xəritə yaradıldı!")
        print("Fayl: outputs/enhanced_route_map.html")
    else:
        print("Həll tapılmadı!")

if __name__ == '__main__':
    main()