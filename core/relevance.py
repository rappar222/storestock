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

from core.ai_intent import score_with_ai_intent, analyze_user_intent

def calculate_relevance(query: str, title: str, price: float = 0.0, in_stock: bool = True) -> float:
    """
    Computes hierarchical relevance using AI Intent detection.
    Guarantees that actual milk beats body lotion & cheese, and actual GPUs beat cables and servers.
    """
    intent = analyze_user_intent(query)
    return score_with_ai_intent(query, title, price, in_stock, intent)
