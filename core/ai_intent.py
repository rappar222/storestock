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

# Cosmetics / Beauty words that should never match drinking milk or groceries
COSMETIC_WORDS: Set[str] = {
    "de corp", "corp", "demachiant", "demachiere", "lotiune", "lotion", "crema", "cream",
    "hidratant", "hidratanta", "solar", "solara", "bronzare", "plaja",
    "gel de dus", "sampon", "cosmetic", "cosmetice", "parfum", "antirid", "scrub",
    "exfoliant", "cleanser", "serum", "masca ten", "lapte corp",
    "curatare", "curățare", "nettoyant", "cleansing", "toaleta", "balsam",
    "bebe", "bebelus", "bebelusi"
}

CHEESE_WORDS: Set[str] = {
    "cascaval", "telemea", "branza", "mozzarella", "parmezan", "cheddar", "brie", "camembert"
}

# Cross-language vocabulary bridges for localized retailer searches
RO_LOCAL_TRANSLATIONS: Dict[str, str] = {
    "milk": "lapte",
    "bread": "paine",
    "butter": "unt",
    "eggs": "oua",
    "coffee": "cafea",
    "water": "apa",
    "cheese": "cascaval",
    "meat": "carne",
    "chicken": "pui",
    "oil": "ulei",
    "sugar": "zahar",
    "flour": "faina",
    "beer": "bere",
    "wine": "vin",
    "graphics card": "placa video",
    "motherboard": "placa de baza",
    "power supply": "sursa alimentare",
    "headphones": "casti"
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

GROCERY_INTENTS: Dict[str, Dict] = {
    "milk": {
        "canonical_name": "Milk / Lapte (Drinking & Dairy Milk)",
        "category_intent": "GROCERIES_MILK",
        "search_synonyms": ["lapte", "lapte uht", "lapte bio", "lapte 3.5%", "whole milk"],
        "description": "Prioritizing fresh, organic and UHT drinking milk. Filtering body lotions, cleansing lotions & cheese.",
        "is_component": False,
        "ro_translation": "lapte"
    },
    "lapte": {
        "canonical_name": "Lapte (Consum, UHT & Lactate)",
        "category_intent": "GROCERIES_MILK",
        "search_synonyms": ["lapte uht", "lapte bio", "lapte 3.5%", "lapte vegetal"],
        "description": "Prioritizing fresh, UHT & dairy drinking milk. Demoting cosmetics (lapte de corp, curatare) and cheeses.",
        "is_component": False,
        "ro_translation": "lapte"
    },
    "bread": {
        "canonical_name": "Bread / Pâine (Bakery)",
        "category_intent": "GROCERIES_BAKERY",
        "search_synonyms": ["paine", "paine feliata", "paine integrala"],
        "description": "Prioritizing fresh bakery loaves & sliced bread.",
        "is_component": False,
        "ro_translation": "paine"
    },
    "paine": {
        "canonical_name": "Pâine & Produse de Brutărie",
        "category_intent": "GROCERIES_BAKERY",
        "search_synonyms": ["paine feliata", "paine secara", "paine integrala"],
        "description": "Prioritizing fresh bakery loaves & sliced bread.",
        "is_component": False,
        "ro_translation": "paine"
    },
    "butter": {
        "canonical_name": "Butter / Unt (Dairy)",
        "category_intent": "GROCERIES_DAIRY",
        "search_synonyms": ["unt", "unt 82%", "unt 65%"],
        "description": "Prioritizing dairy butter for cooking and spreading.",
        "is_component": False,
        "ro_translation": "unt"
    },
    "unt": {
        "canonical_name": "Unt de Masă (Lactate)",
        "category_intent": "GROCERIES_DAIRY",
        "search_synonyms": ["unt 82%", "unt 65%", "unt bio"],
        "description": "Prioritizing dairy butter for cooking and spreading.",
        "is_component": False,
        "ro_translation": "unt"
    },
    "eggs": {
        "canonical_name": "Eggs / Ouă Proaspete",
        "category_intent": "GROCERIES_EGGS",
        "search_synonyms": ["oua", "oua ecologice", "oua marimea l"],
        "description": "Prioritizing fresh farm & organic eggs.",
        "is_component": False,
        "ro_translation": "oua"
    },
    "oua": {
        "canonical_name": "Ouă Proaspete",
        "category_intent": "GROCERIES_EGGS",
        "search_synonyms": ["oua ecologice", "oua marimea l", "oua prepelita"],
        "description": "Prioritizing fresh farm & organic eggs.",
        "is_component": False,
        "ro_translation": "oua"
    },
    "coffee": {
        "canonical_name": "Coffee / Cafea (Beans & Ground)",
        "category_intent": "GROCERIES_COFFEE",
        "search_synonyms": ["cafea", "cafea boabe", "cafea macinata"],
        "description": "Prioritizing genuine coffee beans, ground blends & capsules over machines.",
        "is_component": False,
        "ro_translation": "cafea"
    },
    "cafea": {
        "canonical_name": "Cafea (Boabe / Măcinată / Capsule)",
        "category_intent": "GROCERIES_COFFEE",
        "search_synonyms": ["cafea boabe", "cafea macinata", "capsule cafea"],
        "description": "Prioritizing genuine coffee beans, ground blends & capsules over machines.",
        "is_component": False,
        "ro_translation": "cafea"
    },
    "iphone": {
        "canonical_name": "Apple iPhone Smartphone",
        "category_intent": "PHONE_DEVICE",
        "search_synonyms": ["iphone 16 pro", "iphone 16", "iphone 15 pro", "iphone 15"],
        "description": "Prioritizing standalone iPhone devices over phone cases, adapters and cables.",
        "is_component": False
    },
    "ps5": {
        "canonical_name": "Sony PlayStation 5 Console",
        "category_intent": "CONSOLE_DEVICE",
        "search_synonyms": ["playstation 5 slim", "ps5 slim", "consola ps5"],
        "description": "Prioritizing PlayStation 5 consoles over accessories and skins.",
        "is_component": False
    }
}

def analyze_user_intent(query: str, country_code: str = "RO") -> Dict:
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

    # Check hardware
    matched_entry = None
    for key, data in HARDWARE_SYNONYMS.items():
        if re.search(r"\b" + re.escape(key) + r"\b", q_clean):
            matched_entry = data
            break

    # Check groceries & tech
    if not matched_entry:
        for key, data in GROCERY_INTENTS.items():
            if re.search(r"\b" + re.escape(key) + r"\b", q_clean):
                matched_entry = data
                break

    # Dynamic fallback: guarantee an intelligent intent banner for ANY search!
    if not matched_entry:
        matched_entry = {
            "canonical_name": f"{query.strip().title()}",
            "category_intent": "GENERAL_SMART",
            "search_synonyms": [query.strip()],
            "description": f"Searching real-time inventory for '{query.strip()}'. Prioritizing direct product matches and verified store stock.",
            "is_component": False
        }

    user_wants_system = any(term in q_clean for term in ["desktop", "server", "sistem", "workstation", "laptop", "pc complet"])
    user_wants_accessory = any(acc in q_clean for acc in ACCESSORY_AND_PART_KEYWORDS)
    user_wants_cosmetic = any(c in q_clean for c in ["corp", "demachiant", "crema", "lotiune", "cosmetice", "curatare", "cleansing"])

    local_query = None
    if country_code.upper() == "RO":
        if matched_entry.get("ro_translation"):
            local_query = matched_entry["ro_translation"]
        elif q_clean in RO_LOCAL_TRANSLATIONS:
            local_query = RO_LOCAL_TRANSLATIONS[q_clean]

    return {
        "original_query": query,
        "detected_intent": matched_entry["category_intent"],
        "canonical_name": matched_entry["canonical_name"],
        "description": matched_entry["description"],
        "is_component": matched_entry.get("is_component", False),
        "user_wants_system": user_wants_system,
        "user_wants_accessory": user_wants_accessory,
        "user_wants_cosmetic": user_wants_cosmetic,
        "local_query": local_query,
        "synonyms": matched_entry.get("search_synonyms", [query])
    }

def score_with_ai_intent(query: str, title: str, price: float, in_stock: bool, intent_info: Optional[Dict] = None) -> float:
    """
    Strict hierarchical AI relevance:
    Actual Milk >>> Out-of-Stock Milk >>> Cheese >>> Body Lotion / Cosmetics
    Actual GPU Card >>> Out-of-Stock Card >>> Prebuilt Server >>> Power Cable / NVLink Bridge
    """
    if not intent_info:
        intent_info = analyze_user_intent(query)

    t_clean = title.lower().strip()
    q_clean = query.lower().strip()
    q_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", q_clean) if len(w) > 1]

    score = 0.0

    user_asked_acc = intent_info.get("user_wants_accessory", False)
    user_asked_sys = intent_info.get("user_wants_system", False)
    user_asked_cosmetic = intent_info.get("user_wants_cosmetic", False)
    detected_intent = intent_info.get("detected_intent", "GENERAL")

    # 1. Milk / Dairy Intent Disambiguation
    if detected_intent == "GROCERIES_MILK":
        # Severe penalty for cosmetics (lapte de corp, crema, demachiant)
        is_cosmetic = any(c in t_clean for c in COSMETIC_WORDS)
        if is_cosmetic and not user_asked_cosmetic:
            score -= 600.0

        # Severe penalty for cheese (cascaval, telemea, mozzarella)
        is_cheese = any(re.search(r"\b" + re.escape(ch) + r"\b", t_clean) for ch in CHEESE_WORDS)
        if is_cheese and "lapte" not in q_clean.replace("lapte", ""):
            score -= 400.0

        # Dominant boost for actual dairy drinking milk
        has_milk_word = re.search(r"\blapte\b|\bmilk\b", t_clean) is not None
        if has_milk_word and not is_cosmetic:
            score += 300.0
            if t_clean.startswith("lapte") or t_clean.startswith("milk"):
                score += 150.0
            if any(k in t_clean for k in ["uht", "3.5%", "1.5%", "bio", "vaca", "capra", "zuzu", "napolact", "albalact", "olympus"]):
                score += 100.0
        elif not has_milk_word:
            # If title doesn't even contain the word 'lapte', severely demote it
            score -= 500.0

    # 2. Accessory Demotion (Cables, NVLink Bridges, Brackets, Stands)
    is_accessory = any(re.search(r"\b" + re.escape(acc) + r"\b", t_clean) for acc in ACCESSORY_AND_PART_KEYWORDS)
    if is_accessory and not user_asked_acc:
        score -= 500.0

    # 3. Prebuilt System Demotion (Server racks, 280,000 RON desktop towers)
    is_prebuilt = any(p in t_clean for p in PREBUILT_SERVER_KEYWORDS)
    if is_prebuilt and not user_asked_sys:
        score -= 400.0

    # 4. Discrete Graphics Card Component Detection
    is_discrete_card = any(d in t_clean for d in DISCRETE_GPU_INDICATORS) or "rtx a6000" in t_clean or "rtx 6000" in t_clean
    if detected_intent == "STANDALONE_GPU" and is_discrete_card and not is_accessory and not is_prebuilt:
        score += 350.0

    # 5. Token Matching & Coverage
    matched_tokens = [t for t in q_tokens if re.search(r"\b" + re.escape(t) + r"\b", t_clean)]
    if q_tokens:
        coverage = len(matched_tokens) / len(q_tokens)
        score += coverage * 120.0
        if coverage < 1.0:
            score -= 80.0 * (1.0 - coverage)

    # 6. In-Stock Priority
    if in_stock:
        score += 50.0

    return score
