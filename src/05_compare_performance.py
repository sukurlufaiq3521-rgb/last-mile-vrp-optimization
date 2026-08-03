import numpy as np
import pandas as pd
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# ============================================
# 1. DATA HAZIRLIĞI
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
# 2. "NAIVE" (SADƏ) MARŞRUT — HEÇ OPTİMALLAŞDIRMA YOXDUR
# ============================================
def calculate_naive_route_distance(data):
    """
    Sadə üsul: bütün nöqtələri sıra ilə (0, 1, 2, 3...) 5 maşın arasında
    bərabər bölür, hər maşın öz payını sıra ilə gəzir.
    Bu, 'əgər heç kim optimallaşdırma etməsəydi' ssenarisidir.
    """
    distance_matrix = data['distance_matrix']
    n_points = len(distance_matrix) - 1  # depot xaric
    num_vehicles = data['num_vehicles']
    
    # Nöqtələri sıra ilə maşınlara bölürük (1-ci nöqtədən başlayaraq)
    points = list(range(1, n_points + 1))
    points_per_vehicle = len(points) // num_vehicles
    
    total_distance = 0
    
    for v in range(num_vehicles):
        start_idx = v * points_per_vehicle
        end_idx = start_idx + points_per_vehicle if v < num_vehicles - 1 else len(points)
        vehicle_points = points[start_idx:end_idx]
        
        # Marşrut: depot -> nöqtələr sıra ilə -> depot
        route = [0] + vehicle_points + [0]
        
        for i in range(len(route) - 1):
            total_distance += distance_matrix[route[i]][route[i+1]]
    
    return total_distance

# ============================================
# 3. OR-TOOLS İLƏ OPTİMALLAŞDIRILMIŞ HƏLL
# ============================================
def solve_vrp_optimized(data):
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
    
    if solution:
        return solution.ObjectiveValue()
    return None

# ============================================
# 4. MÜQAYİSƏ VƏ NƏTİCƏ
# ============================================
def main():
    data, df = create_data_model()
    
    print("Hesablanır...\n")
    
    # Naive marşrut
    naive_distance = calculate_naive_route_distance(data)
    
    # Optimallaşdırılmış marşrut
    optimized_distance = solve_vrp_optimized(data)
    
    # Faiz fərqini hesablayırıq
    improvement_pct = ((naive_distance - optimized_distance) / naive_distance) * 100
    
    print("=" * 50)
    print("BEFORE / AFTER MÜQAYİSƏSİ")
    print("=" * 50)
    print(f"\n📍 NAIVE (optimallaşdırma yoxdur):")
    print(f"   Ümumi məsafə: {naive_distance} metr ({naive_distance/1000:.2f} km)")
    
    print(f"\n✅ OPTİMALLAŞDIRILMIŞ (OR-Tools, capacity constraint ilə):")
    print(f"   Ümumi məsafə: {optimized_distance} metr ({optimized_distance/1000:.2f} km)")
    
    print(f"\n🎯 NƏTİCƏ:")
    print(f"   Məsafə azalması: {naive_distance - optimized_distance} metr")
    print(f"   Yaxşılaşma faizi: {improvement_pct:.1f}%")
    print("=" * 50)
    
    # Nəticələri CSV-yə yazaq (README və LinkedIn üçün istifadə edəcəyik)
    results = pd.DataFrame({
        'Metod': ['Naive (sıra ilə)', 'OR-Tools (optimallaşdırılmış)'],
        'Məsafə (metr)': [naive_distance, optimized_distance],
        'Məsafə (km)': [naive_distance/1000, optimized_distance/1000]
    })
    results.to_csv('outputs/performance_comparison.csv', index=False)
    print("\nNəticələr saxlandı: outputs/performance_comparison.csv")

if __name__ == '__main__':
    main()
    