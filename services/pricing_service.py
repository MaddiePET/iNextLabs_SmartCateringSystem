from typing import List


THEME_PRICE_RANGES = {
    "Japanese Fusion": {"min": 80.0, "target": 98.0, "max": 110.0},
    "Traditional Malay": {"min": 70.0, "target": 88.0, "max": 95.0},
    "Western Corporate": {"min": 85.0, "target": 105.0, "max": 120.0},
    "Chinese Fusion": {"min": 75.0, "target": 92.0, "max": 105.0},
}

CATEGORY_WEIGHTS = {
    "Main": 0.24,
    "Side": 0.10,
    "Soup": 0.08,
    "Dessert": 0.08,
}

PREMIUM_KEYWORDS = {
    "salmon": 8.0,
    "beef": 7.0,
    "steak": 8.0,
    "sushi": 5.0,
    "matcha": 3.0,
    "mochi": 3.0,
    "quiche": 4.0,
    "croissant": 4.0,
}

DIETARY_SURCHARGE = {
    "vegan": 4.0,
    "gluten free": 5.0,
    "dairy free": 3.0,
    "nut allergy": 3.0,
}

ADD_ONS = {
    "eco_packaging": 5.0,
    "standard_beverage": 3.0,
    "licensed_bar_min": 10.0,
}

BUDGET_OPTIMIZATION_STRATEGIES = {
    "avocado": {
        "replacement": ["cucumber", "carrot", "edamame"],
        "strategy": "Reduce avocado usage by 50% and increase cucumber/carrot portions in sushi platters.",
    },

    "matcha": {
        "replacement": ["green tea powder", "pandan flavoring"],
        "strategy": "Lower matcha quantity per dessert or replace with pandan-based dessert for local sourcing.",
    },

    "vegan mochi": {
        "replacement": ["coconut pudding", "fruit jelly cup", "traditional kuih"],
        "strategy": "Replace imported vegan mochi with locally prepared desserts.",
    },

    "salmon": {
        "replacement": ["fish fillet", "chicken", "mushroom"],
        "strategy": "Substitute salmon with locally sourced fish fillet or grilled chicken.",
    },

    "smoked salmon": {
        "replacement": ["grilled chicken slices", "egg mayo filling", "tuna spread"],
        "strategy": "Use lower-cost protein fillings for croissants and sandwiches.",
    },

    "asparagus": {
        "replacement": ["broccoli", "long beans", "bok choy"],
        "strategy": "Replace imported asparagus with locally available vegetables.",
    },

    "gluten-free croutons": {
        "replacement": ["roasted potatoes", "rice crisps"],
        "strategy": "Use naturally gluten-free sides instead of specialty imported products.",
    },

    "parmesan": {
        "replacement": ["local cheddar", "reduced cheese portion"],
        "strategy": "Reduce imported cheese usage or blend with local cheese.",
    },

    "quinoa": {
        "replacement": ["rice", "couscous", "barley"],
        "strategy": "Replace quinoa with lower-cost grains while maintaining portion volume.",
    },

    "gluten-free chili sauce": {
        "replacement": ["house-made chili sauce"],
        "strategy": "Prepare in-house gluten-free chili sauce instead of imported brands.",
    },

    "gluten-free soy sauce": {
        "replacement": ["tamari in smaller portions"],
        "strategy": "Reduce sauce serving size or bulk-purchase tamari.",
    },

    "gluten-free teriyaki sauce": {
        "replacement": ["house-made teriyaki sauce"],
        "strategy": "Produce sauce internally using certified gluten-free ingredients.",
    },

    "gluten-free tamari": {
        "replacement": ["low-sodium tamari"],
        "strategy": "Use locally sourced tamari alternatives in smaller quantities.",
    },

    "vegetarian quiche": {
        "replacement": ["vegetable pasta", "vegetable fried rice"],
        "strategy": "Replace bakery-intensive dishes with easier bulk-cooked vegetarian mains.",
    },

    "beef steak": {
        "replacement": ["chicken breast", "grilled fish", "mushroom steak"],
        "strategy": "Substitute premium beef cuts with lower-cost proteins.",
    },

    "prawn": {
        "replacement": ["fish fillet", "chicken", "tofu"],
        "strategy": "Avoid volatile seafood pricing by using stable protein alternatives.",
    },

    "eco-packaging": {
        "replacement": ["standard biodegradable packaging"],
        "strategy": "Use simpler eco-packaging designs or bulk packaging for buffet service.",
    },
}

def get_theme_price_range(theme: str):
    return THEME_PRICE_RANGES.get(theme, THEME_PRICE_RANGES["Japanese Fusion"])


def get_dietary_surcharge(user_request: str) -> float:
    text = user_request.lower()
    total = 0.0

    for key, value in DIETARY_SURCHARGE.items():
        if key in text:
            total += value

    return total


def get_premium_adjustment(menu_json: List[dict]) -> float:
    text = " ".join(
        [item["name"] + " " + " ".join(item.get("ingredients", [])) for item in menu_json]
    ).lower()

    adjustment = 0.0

    for keyword, value in PREMIUM_KEYWORDS.items():
        if keyword in text:
            adjustment += value

    return adjustment


def calculate_pricing_from_json(
    menu_json: List[dict],
    guest_count: int,
    budget_per_head: float,
    selected_theme: str = "Japanese Fusion",
    user_request: str = "",
) -> str:
    price_range = get_theme_price_range(selected_theme)

    base_target = min(price_range["target"], budget_per_head - 5)
    dietary_adjustment = get_dietary_surcharge(user_request)
    premium_adjustment = get_premium_adjustment(menu_json)

    guest_discount = 0.0
    if guest_count >= 200:
        guest_discount = 5.0
    elif guest_count >= 100:
        guest_discount = 2.0

    total_per_head = base_target + dietary_adjustment + premium_adjustment - guest_discount

    # Keep quote within package range
    total_per_head = max(price_range["min"], min(total_per_head, price_range["max"]))

    if "eco-friendly" in user_request.lower() or "eco packaging" in user_request.lower():
        total_per_head += ADD_ONS["eco_packaging"]

    if "wine" in user_request.lower() or "bar service" in user_request.lower():
        total_per_head += ADD_ONS["licensed_bar_min"]

    items = []
    weighted_total = sum(CATEGORY_WEIGHTS.get(item["category"], 0.1) for item in menu_json)

    for item in menu_json:
        weight = CATEGORY_WEIGHTS.get(item["category"], 0.1)
        item_price = (weight / weighted_total) * (total_per_head - 15.0)
        items.append((item["name"], item["category"], item_price))

    items.append(("Service Fee", "Fixed Fee", 10.0))
    items.append(("Standard Beverage Service", "Included Add-on", 3.0))
    total_per_head += ADD_ONS["standard_beverage"]

    if "eco-friendly" in user_request.lower() or "eco packaging" in user_request.lower():
        items.append(("Eco-Packaging", "Fixed Fee", 5.0))

    if (
        "wine" in user_request.lower()
        or "bar service" in user_request.lower()
        or "beer" in user_request.lower()
        or "whiskey" in user_request.lower()
        or "whisky" in user_request.lower()
        or "rum" in user_request.lower()
        or "gin" in user_request.lower()
        or "tequila" in user_request.lower()
        or "vodka" in user_request.lower()
    ):
        total_per_head += ADD_ONS["licensed_bar_min"]
        items.append(("Licensed Bar Service", "Add-on", 50.0))

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

    table += f"\nPackage Range: RM {price_range['min']:.2f} - RM {price_range['max']:.2f}"
    table += f"\nSubtotal Per Head: RM {total_per_head:.2f}"
    table += f"\nTotal Event Cost: RM {total_event_cost:.2f}"
    table += f"\nStatus: {status}"
    table += f"\n[FINAL QUOTE]: RM {total_per_head:.2f}"
    
    optimization_report = optimize_budget(
        menu_items=menu_json,
        final_quote=total_per_head,
        budget_per_head=budget_per_head,
        user_request=user_request,
    )

    table += f"\n\n{optimization_report}"

    return table

def optimize_budget(menu_items, final_quote, budget_per_head, user_request=""):
    if final_quote <= budget_per_head:
        return "Budget Optimization:\n- Budget is acceptable. No optimization needed."

    used_ingredients = set()

    for item in menu_items:
        for ingredient in item.get("ingredient_portions", []):
            used_ingredients.add(ingredient["name"].lower())

    if "eco-friendly" in user_request.lower() or "eco packaging" in user_request.lower():
        used_ingredients.add("eco-packaging")

    suggestions = ["Budget Optimization Suggestions:"]

    for ingredient in used_ingredients:
        optimization = BUDGET_OPTIMIZATION_STRATEGIES.get(ingredient)

        if optimization:
            suggestions.append(
                f"- {ingredient}: replace with {', '.join(optimization['replacement'])}. "
                f"{optimization['strategy']}"
            )

    if len(suggestions) == 1:
        suggestions.append("- Reduce premium ingredients, simplify packaging, or adjust dessert portions.")

    suggestions.append(f"- Current quote: RM {final_quote:.2f} per pax")
    suggestions.append(f"- Target budget: RM {budget_per_head:.2f} per pax")

    return "\n".join(suggestions)