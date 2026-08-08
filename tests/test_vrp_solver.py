import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


def solve_vrp_for_test(num_vehicles, demands, dist_matrix, depot=0):
    """Test məqsədi üçün sadələşdirilmiş VRP solver (app.py-dakı ilə eyni məntiq)"""
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

    routes = []
    if solution:
        for vehicle_id in range(num_vehicles):
            index = routing.Start(vehicle_id)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))
            routes.append(route)
    return routes


def load_test_data():
    """Data mövcud fayllardan yüklənir"""
    df = pd.read_csv('data/delivery_points.csv')
    distance_matrix = np.load('data/distance_matrix.npy')
    return df, distance_matrix


def test_all_points_visited_exactly_once():
    """Hər çatdırılma nöqtəsi düz bir dəfə ziyarət olunmalıdır (nə çox, nə az)"""
    df, distance_matrix = load_test_data()
    demands = df['demand'].tolist()
    routes = solve_vrp_for_test(5, demands, distance_matrix.tolist())

    visited_points = []
    for route in routes:
        for point in route:
            if point != 0:
                visited_points.append(point)

    expected_points = set(range(1, len(df)))
    actual_points = set(visited_points)

    assert actual_points == expected_points, "Bəzi nöqtələr ziyarət edilməyib və ya təkrarlanıb!"
    assert len(visited_points) == len(set(visited_points)), "Bəzi nöqtələr birdən çox ziyarət edilib!"


def test_capacity_constraint_respected():
    """Heç bir maşının yükü, onun tutumunu keçməməlidir"""
    df, distance_matrix = load_test_data()
    demands = df['demand'].tolist()
    num_vehicles = 5
    routes = solve_vrp_for_test(num_vehicles, demands, distance_matrix.tolist())

    total_demand = sum(demands)
    max_capacity = total_demand // num_vehicles + 20

    for route in routes:
        route_load = sum(demands[point] for point in route if point != 0)
        assert route_load <= max_capacity, f"Maşının yükü ({route_load}) tutumu ({max_capacity}) keçir!"


def test_all_routes_start_and_end_at_depot():
    """Hər marşrut depoda (0-cı nöqtədə) başlamalı və bitməlidir"""
    df, distance_matrix = load_test_data()
    demands = df['demand'].tolist()
    routes = solve_vrp_for_test(5, demands, distance_matrix.tolist())

    for route in routes:
        assert route[0] == 0, "Marşrut depoda başlamır!"
        assert route[-1] == 0, "Marşrut depoda bitmir!"


def test_solution_exists_for_reasonable_vehicle_count():
    """Ağlabatan sayda maşınla, həll həmişə tapılmalıdır"""
    df, distance_matrix = load_test_data()
    demands = df['demand'].tolist()

    for num_vehicles in [2, 5, 8]:
        routes = solve_vrp_for_test(num_vehicles, demands, distance_matrix.tolist())
        assert len(routes) == num_vehicles, f"{num_vehicles} maşın üçün düzgün sayda marşrut qaytarılmadı!"
        assert all(len(r) >= 2 for r in routes), "Bəzi marşrutlar boşdur (yalnız depot)!"