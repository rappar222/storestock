from typing import Dict, List, Optional
import math

STORE_BRANCHES: Dict[str, List[Dict]] = {
    "Altex": [
        # București
        {"name": "Altex Mega Mall", "address": "Bulevardul Pierre de Coubertin 3-5, București", "lat": 44.4414, "lon": 26.1522},
        {"name": "Altex Băneasa Shopping City", "address": "Șoseaua București-Ploiești 42D, București", "lat": 44.5065, "lon": 26.0888},
        {"name": "Altex Plaza România", "address": "Bulevardul Timișoara 26, București", "lat": 44.4285, "lon": 26.0354},
        {"name": "Altex Sun Plaza", "address": "Calea Văcărești 391, București", "lat": 44.3976, "lon": 26.1219},
        # Cluj-Napoca
        {"name": "Altex Iulius Mall Cluj", "address": "Strada Alexandru Vaida Voevod 53B, Cluj-Napoca", "lat": 46.7725, "lon": 23.6264},
        {"name": "Altex Vivo! Cluj", "address": "Strada Avram Iancu 492-500, Florești / Cluj", "lat": 46.7511, "lon": 23.5318},
        # Timișoara
        {"name": "Altex Iulius Town Timișoara", "address": "Piața Consiliul Europei 2, Timișoara", "lat": 45.7661, "lon": 21.2295},
        # Iași
        {"name": "Altex Palas Mall Iași", "address": "Strada Palas 7A, Iași", "lat": 47.1572, "lon": 27.5878},
        # Brașov
        {"name": "Altex Coresi Shopping Resort", "address": "Strada Zaharia Stancu 1, Brașov", "lat": 45.6726, "lon": 25.6179}
    ],
    "Media Galaxy": [
        {"name": "Media Galaxy Orhideea", "address": "Calea Giulești 1-3, București", "lat": 44.4447, "lon": 26.0645},
        {"name": "Media Galaxy ParkLake", "address": "Strada Liviu Rebreanu 4, București", "lat": 44.4208, "lon": 26.1506},
        {"name": "Media Galaxy Mall Vitan", "address": "Calea Vitan 55-59, București", "lat": 44.4205, "lon": 26.1278},
        {"name": "Media Galaxy Iulius Mall Cluj", "address": "Strada Alexandru Vaida Voevod 53B, Cluj", "lat": 46.7721, "lon": 23.6261},
        {"name": "Media Galaxy Shopping City Timișoara", "address": "Calea Șagului 100, Timișoara", "lat": 45.7196, "lon": 21.1969}
    ],
    "eMAG": [
        {"name": "eMAG Showroom Crângași", "address": "Șoseaua Virtuții 148, București", "lat": 44.4503, "lon": 26.0378},
        {"name": "eMAG Showroom Titan", "address": "Strada Liviu Rebreanu 6A, București", "lat": 44.4215, "lon": 26.1558},
        {"name": "eMAG Showroom Băneasa", "address": "Bulevardul Aerogării 17, București", "lat": 44.4925, "lon": 26.0881},
        {"name": "eMAG Showroom Cluj-Napoca", "address": "Calea Florești 56, Cluj-Napoca", "lat": 46.7562, "lon": 23.5492},
        {"name": "eMAG Showroom Timișoara", "address": "Bulevardul Liviu Rebreanu 2-4, Timișoara", "lat": 45.7338, "lon": 21.2185},
        {"name": "eMAG Showroom Iași", "address": "Bulevardul Tudor Vladimirescu, Iași", "lat": 47.1593, "lon": 27.5995}
    ],
    "PC Garage": [
        {"name": "PC Garage Hub & Logistica", "address": "Strada Logofăt Tăutu 68A, București", "lat": 44.4172, "lon": 26.1158}
    ],
    "Flanco": [
        {"name": "Flanco Afi Cotroceni", "address": "Bulevardul Vasile Milea 4, București", "lat": 44.4308, "lon": 26.0526},
        {"name": "Flanco Colentina", "address": "Șoseaua Colentina 426, București", "lat": 44.4697, "lon": 26.1534},
        {"name": "Flanco Cluj Vivo", "address": "Strada Avram Iancu 492, Cluj", "lat": 46.7515, "lon": 23.5312},
        {"name": "Flanco Shopping City Timișoara", "address": "Calea Șagului 100, Timișoara", "lat": 45.7191, "lon": 21.1963}
    ],
    "Auchan Hypermarket": [
        {"name": "Auchan Titan", "address": "Bulevardul 1 Decembrie 1918 33A, București", "lat": 44.4158, "lon": 26.1758},
        {"name": "Auchan Cotroceni", "address": "Bulevardul Vasile Milea 4, București", "lat": 44.4312, "lon": 26.0531},
        {"name": "Auchan Militari", "address": "Bulevardul Iuliu Maniu 546-560, București", "lat": 44.4328, "lon": 25.9862},
        {"name": "Auchan Iris Cluj", "address": "Bulevardul Muncii 1-15, Cluj-Napoca", "lat": 46.7972, "lon": 23.6068},
        {"name": "Auchan Iulius Mall Cluj", "address": "Strada Alexandru Vaida Voevod 53B, Cluj", "lat": 46.7728, "lon": 23.6269},
        {"name": "Auchan Timișoara Nord", "address": "Calea Aradului 56A, Timișoara", "lat": 45.7788, "lon": 21.2225}
    ],
    "evoMAG": [
        {"name": "evoMAG Showroom Mihai Bravu", "address": "Șoseaua Mihai Bravu 251-253, București", "lat": 44.4324, "lon": 26.1365}
    ]
}

def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

def attach_branch_info(store_name: str, item_index: int, user_lat: Optional[float] = None, user_lon: Optional[float] = None) -> Dict:
    branches = STORE_BRANCHES.get(store_name, [])
    if not branches:
        return {}

    # If user provided location, ALWAYS find the nearest branch to them!
    if user_lat is not None and user_lon is not None:
        closest = min(branches, key=lambda b: calculate_haversine_distance(user_lat, user_lon, b["lat"], b["lon"]))
        dist = calculate_haversine_distance(user_lat, user_lon, closest["lat"], closest["lon"])
        return {
            "store_branch": closest["name"],
            "store_address": closest["address"],
            "latitude": closest["lat"],
            "longitude": closest["lon"],
            "distance_km": dist
        }
    
    # Fallback to rotation if no coordinates provided
    branch = branches[item_index % len(branches)]
    return {
        "store_branch": branch["name"],
        "store_address": branch["address"],
        "latitude": branch["lat"],
        "longitude": branch["lon"]
    }
