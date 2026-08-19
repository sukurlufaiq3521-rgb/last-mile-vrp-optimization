import numpy as np
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