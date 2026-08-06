import pandas as pd
import numpy as np

np.random.seed(42)

# Hər rayon üçün: (mərkəz_lat, mərkəz_lon, lat_sərhəd, lon_sərhəd)
# Sərhədlər ehtiyatla seçilib ki, heç bir nöqtə dənizə düşməsin
districts = {
    'Yasamal':    {'center': (40.3950, 49.8300), 'lat_range': 0.010, 'lon_range': 0.012},
    'Nesimi':     {'center': (40.3870, 49.8420), 'lat_range': 0.008, 'lon_range': 0.010},
    'Xetai':      {'center': (40.3750, 49.8550), 'lat_range': 0.008, 'lon_range': 0.010},
    'Nerimanov':  {'center': (40.4080, 49.8650), 'lat_range': 0.010, 'lon_range': 0.012},
    'Sebail':     {'center': (40.3720, 49.8280), 'lat_range': 0.006, 'lon_range': 0.008},
}

n_points_total = 80
n_districts = len(districts)
points_per_district = n_points_total // n_districts

all_lats = []
all_lons = []
all_demands = []

for district_name, info in districts.items():
    center_lat, center_lon = info['center']
    lat_range = info['lat_range']
    lon_range = info['lon_range']

    # UNIFORM (bərabər) paylanma - sərt sərhədlər daxilində, normal-dan fərqli olaraq
    # heç bir nöqtə bu sərhədləri keçə bilməz
    lats = np.random.uniform(center_lat - lat_range, center_lat + lat_range, points_per_district)
    lons = np.random.uniform(center_lon - lon_range, center_lon + lon_range, points_per_district)
    demands = np.random.randint(1, 10, points_per_district)

    all_lats.extend(lats)
    all_lons.extend(lons)
    all_demands.extend(demands)

# Anbar (depot) - şəhərin quru mərkəzində, təhlükəsiz zonada
depot_lat = 40.3870
depot_lon = 49.8420

data = {
    'point_id': list(range(len(all_lats) + 1)),
    'latitude': [depot_lat] + list(all_lats),
    'longitude': [depot_lon] + list(all_lons),
    'demand': [0] + list(all_demands)
}

df = pd.DataFrame(data)
df.to_csv('data/delivery_points.csv', index=False)

print("Sintetik data uğurla yeniləndi (sərhədli, təhlükəsiz zonalarla)!")
print(f"Ümumi nöqtə sayı: {len(df)} (1 depot + {len(all_lats)} çatdırılma nöqtəsi)")
print(f"Rayonlar: {list(districts.keys())}")