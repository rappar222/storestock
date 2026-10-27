import re
from typing import Dict, List, Optional, Set

# Comprehensive Accessory & Bridge Keywords (Must NEVER outrank the primary card)
ACCESSORY_AND_PART_KEYWORDS: Set[str] = {
    "cablu", "cable", "nvlink", "bridge", "kit", "splitter", "bracket",
    "holder", "stand", "suport", "riser", "adaptor", "adapter", "pasta",
    "paste", "thermal", "pad", "ventilator", "fan", "cooler", "montare",
    "mount", "surub", "suruburi", "screws", "extensie", "extension",
    "stickere", "sticker", "folie", "protectie", "geanta", "breloc",
    "power supply", "incarcator", "alimentator", "charger", "sursa alimentare",
    "backplate", "shroud", "waterblock"
}

PREBUILT_SERVER_KEYWORDS: Set[str] = {
    "desktop pc", "server supermicro", "server dell", "server asus",
    "superworkstation", "sistem desktop", "workstation tower", "tower 2u",
    "rack 2u", "rack 4u", "server poweredge", "laptop", "notebook",
    "sistem pc", "barebone", "epyc", "xeon"
}

DISCRETE_GPU_INDICATORS: Set[str] = {
    "placa video", "placi video", "graphics card", "video card", "gpu"
}

HARDWARE_SYNONYMS: Dict[str, Dict] = {
    "a6000": {
        "canonical_name": "NVIDIA RTX A6000 / RTX 6000 Ada (48GB)",
        "category_intent": "STANDALONE_GPU",
        "search_synonyms": ["rtx a6000", "rtx 6000 ada", "nvidia rtx a6000", "placa video a6000", "pny rtx a6000"],
        "expected_price_min": 15000.0,
        "is_component": True,
        "description": "Professional 48GB Workstation Graphics Card (Ada / Ampere Architecture)"
    },
    "rtx a6000": {
        "canonical_name": "NVIDIA RTX A6000",
        "category_intent": "STANDALONE_GPU",
        "search_synonyms": ["rtx a6000", "rtx 6000 ada", "pny rtx a6000"],
        "expected_price_min": 15000.0,
        "is_component": True,
        "description": "Professional 48GB Workstation Graphics Card"
    },
    "rtx 6000": {
        "canonical_name": "NVIDIA RTX 6000 Ada Generation",
        "category_intent": "STANDALONE_GPU",
        "search_synonyms": ["rtx 6000 ada", "rtx a6000", "pny rtx 6000"],
        "expected_price_min": 25000.0,
        "is_component": True,
        "description": "Workstation GPU with Ada Lovelace Architecture"
    },
    "rtx 5090": {
        "canonical_name": "NVIDIA GeForce RTX 5090",
        "category_intent": "STANDALONE_GPU",
        "search_synonyms": ["rtx 5090", "geforce rtx 5090", "placa video rtx 5090"],
        "expected_price_min": 9000.0,
        "is_component": True,
        "description": "Flagship Blackwell Gaming & Creator GPU (32GB GDDR7)"
    },
    "rtx 4090": {
        "canonical_name": "NVIDIA GeForce RTX 4090",
        "category_intent": "STANDALONE_GPU",
        "search_synonyms": ["rtx 4090", "geforce rtx 4090", "placa video rtx 4090"],
        "expected_price_min": 8000.0,
        "is_component": True,
        "description": "Flagship Ada Lovelace GPU (24GB GDDR6X)"
    }
}

def analyze_user_intent(query: str) -> Dict:
    q_clean = query.lower().strip()
    
    # Check if vehicle query
    from providers.cars.auto_market import AutoMarketProvider
    if AutoMarketProvider.is_car_query(query):
        return {
            "original_query": query,
            "detected_intent": "VEHICLE",
            "canonical_name": f"{query.strip().title()} (Automotive)",
            "description": "Searching vehicle dealerships, auto lots & certified pre-owned lots.",
            "is_component": False,
            "user_wants_system": False,
            "user_wants_accessory": False,
            "synonyms": [query]
        }

    matched_entry = None
    for key, data in HARDWARE_SYNONYMS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", q_clean):
            matched_entry = data
            break

    user_wants_system = any(term in q_clean for term in ["desktop", "server", "sistem", "workstation", "laptop", "pc complet"])
    user_wants_accessory = any(acc in q_clean for acc in ACCESSORY_AND_PART_KEYWORDS)

    return {
        "original_query": query,
        "detected_intent": matched_entry["category_intent"] if matched_entry else "GENERAL",
        "canonical_name": matched_entry["canonical_name"] if matched_entry else None,
        "description": matched_entry["description"] if matched_entry else None,
        "is_component": matched_entry["is_component"] if matched_entry else False,
        "user_wants_system": user_wants_system,
        "user_wants_accessory": user_wants_accessory,
        "synonyms": matched_entry["search_synonyms"] if matched_entry else [query]
    }

def score_with_ai_intent(query: str, title: str, price: float, in_stock: bool, intent_info: Optional[Dict] = None) -> float:
    """
    Strict hierarchical AI relevance:
    Actual Card >>> Out-of-Stock Card >>> Prebuilt Server >>> Power Cable / NVLink Bridge
    An in-stock cable or server must NEVER outrank an actual GPU card!
    """
    if not intent_info:
        intent_info = analyze_user_intent(query)

    t_clean = title.lower().strip()
    q_clean = query.lower().strip()
    q_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", q_clean) if len(w) > 1]

    score = 0.0

    user_asked_acc = intent_info.get("user_wants_accessory", False)
    user_asked_sys = intent_info.get("user_wants_system", False)
    is_gpu_intent = intent_info.get("detected_intent") == "STANDALONE_GPU"

    # 1. Accessory Demotion (Cables, NVLink Bridges, Brackets, Stands)
    is_accessory = any(re.search(r"\b" + re.escape(acc) + r"\b", t_clean) for acc in ACCESSORY_AND_PART_KEYWORDS)
    if is_accessory and not user_asked_acc:
        # Severe penalty: Cables and NVLink bridges can NEVER beat the actual card
        score -= 500.0

    # 2. Prebuilt System Demotion (Server racks, 280,000 RON desktop towers)
    is_prebuilt = any(p in t_clean for p in PREBUILT_SERVER_KEYWORDS)
    if is_prebuilt and not user_asked_sys:
        score -= 400.0

    # 3. Discrete Graphics Card Component Detection
    is_discrete_card = any(d in t_clean for d in DISCRETE_GPU_INDICATORS) or "rtx a6000" in t_clean or "rtx 6000" in t_clean
    if is_gpu_intent and is_discrete_card and not is_accessory and not is_prebuilt:
        score += 350.0  # Dominant boost for actual graphics card listings!

    # 4. Token Matching
    matched_tokens = [t for t in q_tokens if re.search(r"\b" + re.escape(t) + r"\b", t_clean)]
    if q_tokens:
        coverage = len(matched_tokens) / len(q_tokens)
        score += coverage * 100.0

    # 5. Price Sanity Floor for Enterprise Hardware
    if is_gpu_intent and not user_asked_acc:
        if 0.0 < price < 1500.0:
            # Nothing selling for 255 RON or 1490 RON is a 48GB A6000 GPU
            score -= 300.0

    # 6. In-Stock Priority (Only adds +50 so it CANNOT cause a cable to beat a real card)
    if in_stock:
        score += 50.0

    return score
