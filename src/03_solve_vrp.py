import numpy as np
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# 1. DATA HAZIRLIĞI
# ============================================
def create_data_model():
    """Modelin ehtiyac duyduğu bütün datanı hazırlayır"""
    data = {}
    
    # Əvvəlki addımlarda yaratdığımız faylları oxuyuruq
    distance_matrix = np.load('data/distance_matrix.npy')
    data['distance_matrix'] = distance_matrix.tolist()
    
    data['num_vehicles'] = 5   # 5 maşınımız var
    data['depot'] = 0          # 0-cı nöqtə = anbar (başlanğıc/bitiş nöqtəsi)
    
    return data

# ============================================
# 2. NƏTİCƏNİ GÖZƏL FORMATDA ÇAP ETMƏK ÜÇÜN FUNKSİYA
# ============================================
def print_solution(data, manager, routing, solution):
    """Həll tapılandan sonra, hər maşının marşrutunu göstərir"""
    print(f"\nÜmumi qət olunan məsafə: {solution.ObjectiveValue()} metr\n")
    
    total_distance = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = f"Maşın {vehicle_id} üçün marşrut:\n"
        route_distance = 0
        route_points = []
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_points.append(node_index)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        
        # Son nöqtəni (depota qayıdış) əlavə edirik
        route_points.append(manager.IndexToNode(index))
        
        plan_output += " -> ".join(map(str, route_points))
        plan_output += f"\nBu marşrutun məsafəsi: {route_distance} metr\n"
        print(plan_output)
        
        total_distance += route_distance
    
    print(f"Bütün maşınların ümumi məsafəsi: {total_distance} metr ({total_distance/1000:.2f} km)")

# ============================================
# 3. ƏSAS PROQRAM
# ============================================
def main():
    # Datanı hazırlayırıq
    data = create_data_model()
    
    # Index Manager - nöqtə nömrələri ilə daxili indekslər arasında əlaqə qurur
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']), 
        data['num_vehicles'], 
        data['depot']
    )
    
    # Routing Model - əsas optimallaşdırma "beyni"
    routing = pywrapcp.RoutingModel(manager)
    
    # Distance callback - iki nöqtə arasındakı məsafəni modelə bildirir
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # Həll strategiyası - modelin necə "axtarış" edəcəyini müəyyən edir
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    
    # Modeli işə salırıq və həlli tapırıq
    solution = routing.SolveWithParameters(search_parameters)
    
    # Nəticəni göstəririk
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("Həll tapılmadı!")

if __name__ == '__main__':
    main()