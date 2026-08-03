import pandas as pd
import numpy as np

# Təsadüfi ədədlərin hər dəfə eyni çıxması üçün "toxum" təyin edirik
np.random.seed(42)

# Neçə çatdırılma nöqtəsi yaradacağıq
n_points = 80

# Bakı şəhərinin təxmini enlik/uzunluq (latitude/longitude) sərhədləri
# Bu, koordinatların Bakı ərazisində "düşməsini" təmin edir
latitudes = np.random.uniform(40.35, 40.45, n_points)
longitudes = np.random.uniform(49.80, 49.90, n_points)

# Hər ünvanın sifariş həcmi (demand) - 1 ilə 10 arasında təsadüfi ədəd
demands = np.random.randint(1, 10, n_points)

# Anbar (depot) əlavə edirik - bu, 0-cı nöqtə olacaq, bütün marşrutlar buradan başlayır
depot_lat = 40.40
depot_lon = 49.85

# Bütün datanı bir cədvələ (DataFrame) yığırıq
data = {
    'point_id': list(range(n_points + 1)),  # 0 = depot, 1-80 = çatdırılma nöqtələri
    'latitude': [depot_lat] + list(latitudes),
    'longitude': [depot_lon] + list(longitudes),
    'demand': [0] + list(demands)  # depot-un tələbi 0-dır
}

df = pd.DataFrame(data)

# Nəticəni CSV faylına yazırıq
df.to_csv('data/delivery_points.csv', index=False)

print("Sintetik data uğurla yaradıldı!")
print(f"Ümumi nöqtə sayı: {len(df)} (1 depot + {n_points} çatdırılma nöqtəsi)")
print("\nİlk 5 sətir:")
print(df.head())