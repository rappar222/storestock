import re
from typing import Set

ACCESSORY_WORDS: Set[str] = {
    "stand", "suport", "holder", "bracket", "riser", "cablu", "cable",
    "husa", "case", "adaptor", "adapter", "pasta", "paste", "thermal",
    "pad", "ventilator", "fan", "cooler", "montare", "mount", "surub", "suruburi",
    "screws", "splitter", "extensie", "extension", "stickere", "sticker",
    "folie", "protectie", "geanta", "breloc", "jucarie", "macheta",
    "power supply", "incarcator", "alimentator", "charger", "mouse pad"
}

HARDWARE_INDICATORS: Set[str] = {
    "placa video", "placi video", "graphics card", "gpu", "laptop",
    "placa de baza", "procesor", "workstation"
}

def calculate_relevance(query: str, title: str, price: float = 0.0, in_stock: bool = True) -> float:
    """
    Computes a smart relevance score for StoreStock search results.
    Prevents accessories (e.g. GPU stands, brackets, cables) from outranking the actual primary product.
    """
    q_clean = query.lower().strip()
    t_clean = title.lower().strip()
    
    q_tokens = [w for w in re.findall(r"\b[a-zA-Z0-9]+\b", q_clean) if len(w) > 1]
    if not q_tokens:
        return 0.0

    score = 0.0

    # 1. Exact full phrase match
    if q_clean in t_clean:
        score += 100.0

    # 2. Token match & coverage
    matched_tokens = [t for t in q_tokens if re.search(r"\b" + re.escape(t) + r"\b", t_clean)]
    coverage = len(matched_tokens) / len(q_tokens)
    score += coverage * 120.0

    # Severe penalty if core query tokens are completely missing
    if coverage < 1.0:
        score -= 60.0 * (1.0 - coverage)

    # 3. Accessory vs Primary Product Detection
    # Did the user explicitly ask for an accessory? (e.g. "gpu stand" or "hdmi cable")
    query_has_accessory = any(acc in q_clean for acc in ACCESSORY_WORDS)
    title_has_accessory = any(re.search(r"\b" + re.escape(acc) + r"\b", t_clean) for acc in ACCESSORY_WORDS)

    if title_has_accessory and not query_has_accessory:
        score -= 250.0  # Heavy demotion for unwanted accessories

    # 4. Hardware Intent & Price Floor Sanity Check
    is_gpu_query = any(k in q_clean for k in ["rtx", "gtx", "radeon", "a6000", "blackwell", "geforce", "gpu"])
    if is_gpu_query:
        # Boost actual graphics card products
        if any(h in t_clean for h in HARDWARE_INDICATORS):
            score += 50.0

        # An item claiming to be a modern GPU that costs under 250 RON is definitely an accessory/fake
        if 0.0 < price < 250.0 and not query_has_accessory:
            score -= 150.0

    # 5. Position bonus: product title starts with or features query near the beginning
    first_token = q_tokens[0]
    token_idx = t_clean.find(first_token)
    if token_idx != -1 and token_idx < 30:
        score += 25.0

    # 6. In-Stock Priority
    if in_stock:
        score += 150.0

    return score
