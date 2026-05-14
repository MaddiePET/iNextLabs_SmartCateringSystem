import re
from typing import List


def extract_budget_per_head(text: str) -> float:
    match = re.search(r"Budget:\s*RM\s*(\d+(?:\.\d+)?)", text, re.I)
    return float(match.group(1)) if match else 120.0  # Fallback to 120 if not found

def extract_guest_count(text: str) -> int:
    match = re.search(r"Guest count:\s*(\d+)", text, re.I)
    return int(match.group(1)) if match else 0

def extract_currency_values(text: str) -> List[float]:
    matches = re.findall(r"RM\s?(\d+(?:\.\d+)?)", text or "", re.I)
    return [float(x) for x in matches]

def is_supported_west_malaysia_location(text: str) -> bool:
    supported = [
        "kuala lumpur", "selangor", "penang", "johor", "perak",
        "negeri sembilan", "melaka", "malacca", "kedah", "perlis",
        "kelantan", "terengganu", "pahang", "putrajaya", "kl"
    ]
    unsupported = ["sabah", "sarawak", "labuan", "singapore", "london", "thailand"]
    normalized = text.lower()
    if any(place in normalized for place in unsupported):
        return False
    return any(place in normalized for place in supported)
