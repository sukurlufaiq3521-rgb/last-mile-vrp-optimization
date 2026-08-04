import numpy as np
import pandas as pd
import folium
from folium.plugins import DualMap
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# 1. DATA VƏ VRP HƏLLİ
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

def get_naive_routes(data):
    """Naive marşrutları (sıra ilə bölgü) siyahı kimi qaytarır"""
    n_points = len(data['distance_matrix']) - 1
    num_vehicles = data['num_vehicles']
    points = list(range(1, n_points + 1))
    points_per_vehicle = len(points) // num_vehicles
    
    routes = []
    for v in range(num_vehicles):
        start_idx = v * points_per_vehicle
        end_idx = start_idx + points_per_vehicle if v < num_vehicles - 1 else len(points)
        vehicle_points = points[start_idx:end_idx]
        route = [0] + vehicle_points + [0]
        routes.append(route)
    return routes

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
    
    routes = []
    if solution:
        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))
            routes.append(route)
    return routes

# ============================================
# 2. DUAL MAP (YAN-YANA İKİ XƏRİTƏ) YARATMAQ
# ============================================
def add_routes_to_map(map_obj, df, routes, colors):
    for vehicle_id, route in enumerate(routes):
        color = colors[vehicle_id % len(colors)]
        route_coords = []
        
        for point_id in route:
            lat = df.loc[point_id, 'latitude']
            lon = df.loc[point_id, 'longitude']
            route_coords.append([lat, lon])
            
            if point_id != 0:
                folium.CircleMarker(
                    [lat, lon], radius=4, color=color, fill=True, fillColor=color
                ).add_to(map_obj)
            else:
                folium.Marker(
                    [lat, lon],
                    icon=folium.Icon(color='black', icon='home', prefix='fa')
                ).add_to(map_obj)
        
        folium.PolyLine(route_coords, color=color, weight=2.5, opacity=0.8).add_to(map_obj)

def main():
    data, df = create_data_model()
    
    naive_routes = get_naive_routes(data)
    optimized_routes = solve_vrp(data)
    
    # Naive məsafəni hesablayaq
    naive_distance = 0
    for route in naive_routes:
        for i in range(len(route) - 1):
            naive_distance += data['distance_matrix'][route[i]][route[i+1]]
    
    optimized_distance = 0
    for route in optimized_routes:
        for i in range(len(route) - 1):
            optimized_distance += data['distance_matrix'][route[i]][route[i+1]]
    
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']
    
    # DualMap - yan-yana iki sinxron xəritə
    dual_map = DualMap(location=[depot_lat, depot_lon], zoom_start=12, tiles='CartoDB positron')
    
    colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']
    
    # Sol xəritə - Naive
    add_routes_to_map(dual_map.m1, df, naive_routes, colors)
    
    # Sağ xəritə - Optimallaşdırılmış
    add_routes_to_map(dual_map.m2, df, optimized_routes, colors)
    
    # Başlıqlar əlavə edirik
    title_html = f'''
        <div style="position: fixed; top: 10px; left: 50%; transform: translateX(-50%); z-index: 9999;">
            <table style="background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.3);">
                <tr>
                    <td style="padding: 10px 40px; border-right: 2px solid #ccc; text-align: center;">
                        <b style="color: #c0392b;">❌ NAIVE (Optimallaşdırma yoxdur)</b><br>
                        <span style="font-size: 18px; font-weight: bold;">{naive_distance/1000:.2f} km</span>
                    </td>
                    <td style="padding: 10px 40px; text-align: center;">
                        <b style="color: #27ae60;">✅ OPTİMALLAŞDIRILMIŞ (OR-Tools)</b><br>
                        <span style="font-size: 18px; font-weight: bold;">{optimized_distance/1000:.2f} km</span>
                    </td>
                </tr>
            </table>
        </div>
    '''
    dual_map.get_root().html.add_child(folium.Element(title_html))
    
    dual_map.save('outputs/before_after_map.html')
    
    print("Əvvəl/Sonra müqayisə xəritəsi yaradıldı!")
    print(f"Naive: {naive_distance/1000:.2f} km")
    print(f"Optimallaşdırılmış: {optimized_distance/1000:.2f} km")
    print("Fayl: outputs/before_after_map.html")

if __name__ == '__main__':
    main()