import sys
sys.path.append('src')
from osrm_helper import get_real_route, load_cache, save_cache

cache = load_cache()

lat1, lon1 = 40.40, 49.85
lat2, lon2 = 40.41, 49.86

result = get_real_route(lat1, lon1, lat2, lon2, cache)

print(f"Nəticədə {len(result)} nöqtə var")
print("İlk 3 nöqtə:", result[:3])

save_cache(cache)