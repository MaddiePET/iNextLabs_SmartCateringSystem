import re
import json
from typing import List

MIN_GUESTS = 20
MAX_GUESTS = 500
MIN_BUDGET = 70.0  # Quality floor
MAX_BUDGET = 500.0 # Upper ceiling


PRICE_RULES = {
    "main": 22.0,
    "side": 10.0,
    "soup": 8.0,
    "dessert": 7.0,
    "service": 10.0,
    "eco_packaging": 5.0,
}

def calculate_pricing_from_json(
    menu_json: List[dict],
    guest_count: int,
    budget_per_head: float
) -> str:
    items = []

    for item in menu_json:
        category = item["category"]

        if category == "Main":
            price = PRICE_RULES["main"]
        elif category == "Side":
            price = PRICE_RULES["side"]
        elif category == "Soup":
            price = PRICE_RULES["soup"]
        else:
            price = PRICE_RULES["dessert"]

        items.append((item["name"], category, price))

    items.append(("Service Fee", "Fixed Fee", PRICE_RULES["service"]))
    items.append(("Eco-Packaging", "Fixed Fee", PRICE_RULES["eco_packaging"]))

    total_per_head = sum(item[2] for item in items)

    if any("sushi" in item["name"].lower() or "teriyaki" in item["name"].lower() for item in menu_json):
        total_per_head = max(total_per_head, 80.0)

    total_event_cost = total_per_head * guest_count

    status = (
        "RISK: HIGH - Quote exceeds client budget."
        if total_per_head > budget_per_head
        else "Quote is within client budget."
    )

    table = "| Item | Category | Price Per Head |\n"
    table += "|---|---|---|\n"

    for name, category, price in items:
        table += f"| {name} | {category} | RM {price:.2f} |\n"

    table += f"\nSubtotal Per Head: RM {total_per_head:.2f}"
    table += f"\nTotal Event Cost: RM {total_event_cost:.2f}"
    table += f"\nStatus: {status}"
    table += f"\n[FINAL QUOTE]: RM {total_per_head:.2f}"

    return table

