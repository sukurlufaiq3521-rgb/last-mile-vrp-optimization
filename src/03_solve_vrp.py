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
    
    distance_matrix = np.load('data/distance_matrix.npy')
    data['distance_matrix'] = distance_matrix.tolist()
    
    # Çatdırılma nöqtələrinin demand (tələb) dəyərlərini oxuyuruq
    df = pd.read_csv('data/delivery_points.csv')
    data['demands'] = df['demand'].tolist()
    
    data['num_vehicles'] = 5
    data['depot'] = 0
    
    # HƏR MAŞININ MAKSIMUM YÜK TUTUMU
    # Ümumi tələbi hesablayaq və məntiqli tutum təyin edək
    total_demand = sum(data['demands'])
    data['vehicle_capacities'] = [total_demand // data['num_vehicles'] + 20] * data['num_vehicles']
    
    return data

# ============================================
# 2. NƏTİCƏNİ GÖZƏL FORMATDA ÇAP ETMƏK
# ============================================
def print_solution(data, manager, routing, solution):
    print(f"\nÜmumi qət olunan məsafə: {solution.ObjectiveValue()} metr\n")
    
    total_distance = 0
    total_load = 0
    
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = f"--- Maşın {vehicle_id} üçün marşrut ---\n"
        route_distance = 0
        route_load = 0
        route_points = []
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_points.append(node_index)
            route_load += data['demands'][node_index]
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        
        route_points.append(manager.IndexToNode(index))
        
        plan_output += " -> ".join(map(str, route_points))
        plan_output += f"\nMəsafə: {route_distance} metr | Yük: {route_load}/{data['vehicle_capacities'][vehicle_id]}\n"
        print(plan_output)
        
        total_distance += route_distance
        total_load += route_load
    
    print(f"\n=== ÜMUMİ NƏTİCƏ ===")
    print(f"Bütün maşınların ümumi məsafəsi: {total_distance} metr ({total_distance/1000:.2f} km)")
    print(f"Bütün maşınların ümumi yükü: {total_load}")

# ============================================
# 3. ƏSAS PROQRAM
# ============================================
def main():
    data = create_data_model()
    
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']), 
        data['num_vehicles'], 
        data['depot']
    )
    
    routing = pywrapcp.RoutingModel(manager)
    
    # --- Məsafə callback (əvvəlki kimi) ---
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # --- YENİ: Demand (tələb) callback ---
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    
    # --- YENİ: Capacity Dimension əlavə edirik ---
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # slack (əlavə buffer) - 0 saxlayırıq
        data['vehicle_capacities'],  # hər maşının maksimum tutumu
        True,  # start cumul to zero - hər maşın 0 yüklə başlayır
        'Capacity'
    )
    
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
    
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        print_solution(data, manager, routing, solution)
    else:
        print("Həll tapılmadı!")

if __name__ == '__main__':
    main()