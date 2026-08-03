import pandas as pd
import numpy as np

# Əvvəlki addımda yaratdığımız datanı oxuyuruq
df = pd.read_csv('data/delivery_points.csv')

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    İki koordinat arasındakı real Yer kürəsi məsafəsini (km) hesablayır.
    Bu, 'quş uçuşu' məsafəsidir (düz xətt), real yol deyil.
    """
    R = 6371  # Yer kürəsinin radiusu (km)
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    distance = R * c
    return distance

n = len(df)
distance_matrix = np.zeros((n, n))

# Hər cütlük nöqtə üçün məsafəni hesablayırıq
for i in range(n):
    for j in range(n):
        if i != j:
            distance_matrix[i][j] = haversine_distance(
                df.loc[i, 'latitude'], df.loc[i, 'longitude'],
                df.loc[j, 'latitude'], df.loc[j, 'longitude']
            )

# Matrisi km-dən metrə çeviririk (OR-Tools tam ədədlərlə işləməyi sevir)
distance_matrix_m = (distance_matrix * 1000).astype(int)

# Nəticəni saxlayırıq
np.save('data/distance_matrix.npy', distance_matrix_m)

print("Distance matrix uğurla yaradıldı!")
print(f"Matris ölçüsü: {distance_matrix_m.shape}")
print(f"\nNümunə: 0-cı nöqtədən (depot) 1-ci nöqtəyə məsafə: {distance_matrix_m[0][1]} metr")
print(f"Nümunə: 5-ci nöqtədən 10-cu nöqtəyə məsafə: {distance_matrix_m[5][10]} metr")