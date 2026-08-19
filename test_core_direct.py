import sys
import time
sys.path.append('src')
import numpy as np
import pandas as pd
from vrp_core import solve_vrp

print("Data yüklənir...")
df = pd.read_csv('data/delivery_points.csv')
distance_matrix = np.load('data/distance_matrix.npy')
demands = df['demand'].tolist()

print("solve_vrp çağırılır, vaxt ölçülür...")
start = time.time()
result = solve_vrp(5, demands, distance_matrix.tolist())
elapsed = time.time() - start

print(f"Bitdi! {elapsed:.2f} saniyə çəkdi.")
print(f"Neçə marşrut qaytarıldı: {len(result)}")
print(f"İlk marşrut nümunəsi: {result[0]}")