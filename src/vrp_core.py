import numpy as np
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def haversine(lat1, lon1, lat2, lon2):
    """İki koordinat arasında düz xətt məsafəsini metrlə qaytarır."""
    R = 6371000
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2) ** 2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


def calculate_vehicle_capacity(total_demand, num_vehicles):
    """Hər maşının tutumunu hesablayır. Solver, UI və testlər eyni bu funksiyadan
    istifadə edir ki, kapasitet rəqəmi hər yerdə sinxron qalsın."""
    return total_demand // num_vehicles + 20


def solve_vrp(num_vehicles, demands, dist_matrix, depot=0, balance_weight=0):
    total_demand = sum(demands)
    vehicle_capacities = [calculate_vehicle_capacity(total_demand, num_vehicles)] * num_vehicles

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
def haversine_distance_matrix(df):
    """
    Verilmiş DataFrame-dəki (latitude, longitude) sütunlarına əsasən,
    bütün nöqtə cütləri arasında Haversine məsafə matrisini (metrlə) hesablayır.
    """
    n = len(df)
    matrix = np.zeros((n, n))

    lats = df['latitude'].values
    lons = df['longitude'].values

    for i in range(n):
        for j in range(n):
            if i != j:
                matrix[i][j] = haversine(lats[i], lons[i], lats[j], lons[j])

    return matrix.astype(int)


def validate_uploaded_data(df):
    """
    İstifadəçinin yüklədiyi CSV-ni yoxlayır. Uğurlu olarsa (None, təmizlənmiş_df) qaytarır,
    xəta olarsa (xəta_mətni, None) qaytarır.
    """
    required_columns = {'latitude', 'longitude', 'demand'}
    actual_columns = set(df.columns.str.lower().str.strip())

    if not required_columns.issubset(actual_columns):
        missing = required_columns - actual_columns
        return f"CSV faylında bu sütunlar çatışmır: {', '.join(missing)}. Tələb olunan sütunlar: latitude, longitude, demand.", None

    df.columns = df.columns.str.lower().str.strip()
    df = df[['latitude', 'longitude', 'demand']].copy()

    if len(df) < 3:
        return "Ən azı 3 sətir (1 depo + minimum 2 çatdırılma nöqtəsi) tələb olunur.", None

    if len(df) > 300:
        return "Maksimum 300 nöqtə dəstəklənir (böyük data üçün hesablama vaxtı həddindən artıq uzun olar).", None

    try:
        df['latitude'] = pd.to_numeric(df['latitude'])
        df['longitude'] = pd.to_numeric(df['longitude'])
        df['demand'] = pd.to_numeric(df['demand']).astype(int)
    except (ValueError, TypeError):
        return "latitude, longitude və demand sütunları rəqəm formatında olmalıdır.", None

    if df['latitude'].isnull().any() or df['longitude'].isnull().any():
        return "Bəzi sətirlərdə latitude/longitude dəyəri boşdur.", None

    if not ((df['latitude'].between(-90, 90)).all() and (df['longitude'].between(-180, 180)).all()):
        return "latitude dəyəri -90/90, longitude dəyəri -180/180 aralığında olmalıdır.", None

    df.loc[0, 'demand'] = 0
    df.reset_index(drop=True, inplace=True)
    df.insert(0, 'point_id', range(len(df)))

    return None, df