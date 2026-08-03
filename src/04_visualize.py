import numpy as np
import pandas as pd
import folium
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# 1. DATA HAZIRLIĞI (əvvəlki addımdan eyni)
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

# ============================================
# 2. HƏR MAŞININ MARŞRUTUNU SİYAHIYA YIĞMAQ
# ============================================
def get_routes(data, manager, routing, solution):
    """Hər maşının marşrutunu (nöqtə nömrələri siyahısı kimi) qaytarır"""
    routes = []
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
# 3. VRP-Nİ HƏLL ETMƏK (əvvəlki addımdan eyni)
# ============================================
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

# ============================================
# 4. XƏRİTƏ YARATMAQ
# ============================================
def create_map(df, routes):
    """Folium ilə interaktiv xəritə yaradır"""
    
    # Xəritənin mərkəzini depo koordinatlarına qoyuruq
    depot_lat = df.loc[0, 'latitude']
    depot_lon = df.loc[0, 'longitude']
    
    m = folium.Map(location=[depot_lat, depot_lon], zoom_start=12)
    
    # Hər maşın üçün fərqli rəng
    colors = ['red', 'blue', 'green', 'purple', 'orange']
    
    # Depot-u xüsusi işarə ilə göstəririk
    folium.Marker(
        [depot_lat, depot_lon],
        popup='ANBAR (Depot)',
        icon=folium.Icon(color='black', icon='home')
    ).add_to(m)
    
    # Hər maşının marşrutunu çəkirik
    for vehicle_id, route in enumerate(routes):
        color = colors[vehicle_id % len(colors)]
        
        # Marşrutun bütün nöqtələrinin koordinatlarını toplayırıq
        route_coords = []
        for point_id in route:
            lat = df.loc[point_id, 'latitude']
            lon = df.loc[point_id, 'longitude']
            route_coords.append([lat, lon])
            
            # Çatdırılma nöqtələrini kiçik dairə ilə göstəririk (depot xaric)
            if point_id != 0:
                folium.CircleMarker(
                    [lat, lon],
                    radius=5,
                    popup=f'Nöqtə {point_id} (Maşın {vehicle_id})',
                    color=color,
                    fill=True,
                    fillColor=color
                ).add_to(m)
        
        # Marşrutu xətt kimi çəkirik
        folium.PolyLine(
            route_coords,
            color=color,
            weight=3,
            opacity=0.7,
            popup=f'Maşın {vehicle_id} marşrutu'
        ).add_to(m)
    
    return m

# ============================================
# 5. ƏSAS PROQRAM
# ============================================
def main():
    data, df = create_data_model()
    manager, routing, solution = solve_vrp(data)
    
    if solution:
        routes = get_routes(data, manager, routing, solution)
        
        # Xəritəni yaradırıq
        m = create_map(df, routes)
        
        # HTML faylına saxlayırıq
        m.save('outputs/route_map.html')
        
        print("Xəritə uğurla yaradıldı!")
        print("Fayl: outputs/route_map.html")
        print("Bu faylı brauzerdə açaraq interaktiv xəritəni görə bilərsən.")
    else:
        print("Həll tapılmadı!")

if __name__ == '__main__':
    main()