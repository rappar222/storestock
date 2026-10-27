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
    ],
    "Amazon Australia": [
        {"name": "Amazon Hub & Fulfilment Sydney (BWU2)", "address": "Kemps Creek, Sydney NSW", "lat": -33.8760, "lon": 150.7760},
        {"name": "Amazon Fulfilment Centre Melbourne (MEL1)", "address": "Dandenong South, Melbourne VIC", "lat": -38.0300, "lon": 145.2100},
        {"name": "Amazon Fulfilment Centre Brisbane (BNE1)", "address": "Lytton, Brisbane QLD", "lat": -27.4200, "lon": 153.1500},
        {"name": "Amazon Fulfilment Centre Perth (PER1)", "address": "Jandakot, Perth WA", "lat": -32.1100, "lon": 115.8600}
    ],
    "Micro Center": [
        {"name": "Micro Center Brooklyn", "address": "850 3rd Ave, Brooklyn, NY 11232", "lat": 40.6582, "lon": -74.0041},
        {"name": "Micro Center Queens", "address": "34-40 48th St, Long Island City, NY 11104", "lat": 40.7516, "lon": -73.9142},
        {"name": "Micro Center Boston / Cambridge", "address": "730 Memorial Dr, Cambridge, MA 02139", "lat": 42.3575, "lon": -71.1118},
        {"name": "Micro Center Chicago", "address": "2645 N Elston Ave, Chicago, IL 60647", "lat": 41.9298, "lon": -87.6836},
        {"name": "Micro Center Tustin (LA)", "address": "1100 E Edinger Ave, Tustin, CA 92780", "lat": 33.7277, "lon": -117.8427},
        {"name": "Micro Center Dallas", "address": "13929 N Central Expy, Dallas, TX 75243", "lat": 32.9372, "lon": -96.7512}
    ],
    "Best Buy": [
        {"name": "Best Buy Union Square (NYC)", "address": "One Union Square S, New York, NY 10003", "lat": 40.7350, "lon": -73.9910},
        {"name": "Best Buy West LA", "address": "11301 W Pico Blvd, Los Angeles, CA 90064", "lat": 34.0326, "lon": -118.4419},
        {"name": "Best Buy Chicago Michigan Ave", "address": "875 N Michigan Ave, Chicago, IL 60611", "lat": 41.8988, "lon": -87.6241}
    ],
    "Walmart": [
        {"name": "Walmart Supercenter Secaucus", "address": "400 Park Pl, Secaucus, NJ 07094", "lat": 40.7963, "lon": -74.0538},
        {"name": "Walmart Supercenter Burbank", "address": "1301 N Victory Pl, Burbank, CA 91502", "lat": 34.1852, "lon": -118.3242}
    ],
    "Scorptec Computers": [
        {"name": "Scorptec Auburn (Sydney)", "address": "Unit 2, 264-272 Parramatta Rd, Auburn NSW 2144", "lat": -33.8500, "lon": 151.0330},
        {"name": "Scorptec Clayton (Melbourne)", "address": "Unit 6, 20 Duerdin St, Clayton VIC 3168", "lat": -37.9120, "lon": 145.1430},
        {"name": "Scorptec Macquarie Park", "address": "10 Julius Ave, North Ryde NSW 2113", "lat": -33.7850, "lon": 151.1350}
    ],
    "JB Hi-Fi": [
        {"name": "JB Hi-Fi The Galeries Sydney CBD", "address": "500 George St, Sydney NSW 2000", "lat": -33.8728, "lon": 151.2075},
        {"name": "JB Hi-Fi Bourke St Melbourne", "address": "206 Bourke St, Melbourne VIC 3000", "lat": -37.8124, "lon": 144.9671},
        {"name": "JB Hi-Fi Brisbane City", "address": "Queen St Mall, Brisbane QLD 4000", "lat": -27.4695, "lon": 153.0255}
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
