import requests
import json
import os

CACHE_FILE = 'data/osrm_cache.json'


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def get_real_route(lat1, lon1, lat2, lon2, cache):
    key = f"{lat1:.6f},{lon1:.6f}_{lat2:.6f},{lon2:.6f}"

    if key in cache:
        return cache[key]

    url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview": "full", "geometries": "geojson"}

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if data.get('code') == 'Ok':
            coords = data['routes'][0]['geometry']['coordinates']
            route_coords = [[c[1], c[0]] for c in coords]
            cache[key] = route_coords
            return route_coords
        else:
            print(f"OSRM CODE ERROR: {data.get('code')}")
            fallback = [[lat1, lon1], [lat2, lon2]]
            return fallback
    except Exception as e:
        print(f"OSRM REQUEST ERROR: {e}")
        fallback = [[lat1, lon1], [lat2, lon2]]
        return fallback


def get_full_route_geometry(route_points, df, cache):
    full_geometry = []

    for i in range(len(route_points) - 1):
        point_a = route_points[i]
        point_b = route_points[i + 1]

        lat1 = df.loc[point_a, 'latitude']
        lon1 = df.loc[point_a, 'longitude']
        lat2 = df.loc[point_b, 'latitude']
        lon2 = df.loc[point_b, 'longitude']

        segment = get_real_route(lat1, lon1, lat2, lon2, cache)
        full_geometry.extend(segment)

    return full_geometry