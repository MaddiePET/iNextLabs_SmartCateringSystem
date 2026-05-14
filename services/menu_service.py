import re
from typing import List

THEME_KEYWORDS = {
        "Japanese Fusion": ["sushi", "teriyaki", "miso", "tofu", "edamame", "tempura", "ramen"],
        "Traditional Malay": ["satay", "rendang", "nasi", "sambal", "lemak", "kerabu", "kuih"],
        "Western Corporate": ["pasta", "grilled", "salad", "steak", "roasted", "burger", "sandwich"],
        "Chinese Fusion": ["dim sum", "wok", "stir-fry", "dumpling", "ginger", "soy", "fried rice"]
    }

def build_menu_json(selected_theme: str, dietary: str) -> List[dict]:
    dietary_lower = dietary.lower()
    vegetarian = "vegetarian" in dietary_lower or "vegan" in dietary_lower

    if selected_theme == "Japanese Fusion":
        return [
            {"name": "Vegetable Sushi Platter", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["rice", "avocado", "cucumber", "carrot", "tamari"], "supplier_key": "vegetable sushi platter"},
            {"name": "Mushroom Teriyaki Bowl", "category": "Main", "portion_amount": 250, "portion_unit": "g", "ingredients": ["mushroom", "rice", "teriyaki sauce", "vegetables"], "supplier_key": "mushroom"},
            {"name": "Agedashi Tofu", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["tofu", "rice flour", "ginger broth", "nori"], "supplier_key": "tofu"},
            {"name": "Edamame Side Dish", "category": "Side", "portion_amount": 80, "portion_unit": "g", "ingredients": ["edamame", "sea salt"], "supplier_key": "edamame"},
            {"name": "Matcha Mochi Dessert", "category": "Dessert", "portion_amount": 80, "portion_unit": "g", "ingredients": ["matcha", "mochi", "red bean paste"], "supplier_key": "matcha mochi dessert"},
        ]

    if selected_theme == "Traditional Malay":
        if vegetarian:
            return [
                {"name": "Mushroom Satay Skewers", "category": "Main", "portion_amount": 200, "portion_unit": "g", "ingredients": ["mushroom", "satay spices", "chickpea sauce"], "supplier_key": "mushroom"},
                {"name": "Vegetarian Nasi Lemak", "category": "Main", "portion_amount": 300, "portion_unit": "g", "ingredients": ["coconut rice", "cucumber", "sambal", "tofu"], "supplier_key": "rice"},
                {"name": "Tempeh Rendang Bowl", "category": "Main", "portion_amount": 250, "portion_unit": "g", "ingredients": ["tempeh", "coconut milk", "lemongrass", "turmeric"], "supplier_key": "vegetable"},
                {"name": "Sayur Goreng", "category": "Side", "portion_amount": 120, "portion_unit": "g", "ingredients": ["mixed vegetables", "garlic", "soy sauce"], "supplier_key": "vegetable"},
                {"name": "Kuih-Muih Platter", "category": "Dessert", "portion_amount": 100, "portion_unit": "g", "ingredients": ["rice flour", "coconut", "palm sugar"], "supplier_key": "kuih"},
            ]

        return [
            {"name": "Chicken Satay Skewers", "category": "Main", "portion_amount": 200, "portion_unit": "g", "ingredients": ["chicken", "satay spices", "satay sauce"], "supplier_key": "chicken"},
            {"name": "Nasi Lemak with Sambal", "category": "Main", "portion_amount": 300, "portion_unit": "g", "ingredients": ["coconut rice", "sambal", "cucumber", "egg"], "supplier_key": "rice"},
            {"name": "Beef Rendang", "category": "Main", "portion_amount": 200, "portion_unit": "g", "ingredients": ["beef", "coconut milk", "lemongrass", "turmeric"], "supplier_key": "beef"},
            {"name": "Sayur Goreng", "category": "Side", "portion_amount": 120, "portion_unit": "g", "ingredients": ["mixed vegetables", "garlic", "soy sauce"], "supplier_key": "vegetable"},
            {"name": "Kuih-Muih Platter", "category": "Dessert", "portion_amount": 100, "portion_unit": "g", "ingredients": ["rice flour", "coconut", "palm sugar"], "supplier_key": "kuih"},
        ]

    if selected_theme == "Western Corporate":
        if vegetarian:
            return [
                {"name": "Mushroom Risotto", "category": "Main", "portion_amount": 280, "portion_unit": "g", "ingredients": ["mushroom", "arborio rice", "vegetable stock"], "supplier_key": "mushroom"},
                {"name": "Grilled Seasonal Vegetable Platter", "category": "Main", "portion_amount": 220, "portion_unit": "g", "ingredients": ["zucchini", "capsicum", "carrot", "olive oil"], "supplier_key": "vegetable"},
                {"name": "Herb Roasted Potato Bowl", "category": "Main", "portion_amount": 220, "portion_unit": "g", "ingredients": ["potato", "rosemary", "thyme"], "supplier_key": "vegetable"},
                {"name": "Caesar Salad Without Bacon", "category": "Side", "portion_amount": 100, "portion_unit": "g", "ingredients": ["lettuce", "halal dressing", "croutons"], "supplier_key": "vegetable"},
                {"name": "Chocolate Pudding Cup", "category": "Dessert", "portion_amount": 100, "portion_unit": "g", "ingredients": ["cocoa", "milk", "sugar"], "supplier_key": "dessert"},
            ]

        return [
            {"name": "Roasted Herbs Chicken", "category": "Main", "portion_amount": 220, "portion_unit": "g", "ingredients": ["chicken", "rosemary", "thyme"], "supplier_key": "chicken"},
            {"name": "Mushroom Risotto", "category": "Main", "portion_amount": 250, "portion_unit": "g", "ingredients": ["mushroom", "arborio rice", "vegetable stock"], "supplier_key": "mushroom"},
            {"name": "Garlic Mashed Potatoes with Grilled Vegetables", "category": "Main", "portion_amount": 220, "portion_unit": "g", "ingredients": ["potato", "garlic", "seasonal vegetables"], "supplier_key": "vegetable"},
            {"name": "Caesar Salad Without Bacon", "category": "Side", "portion_amount": 100, "portion_unit": "g", "ingredients": ["lettuce", "halal dressing", "croutons"], "supplier_key": "vegetable"},
            {"name": "Chocolate Pudding Cup", "category": "Dessert", "portion_amount": 100, "portion_unit": "g", "ingredients": ["cocoa", "milk", "sugar"], "supplier_key": "dessert"},
        ]

    if selected_theme == "Chinese Fusion":
        if vegetarian:
            return [
                {"name": "Kung Pao Tofu", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["tofu", "dried chilies", "soy sauce"], "supplier_key": "tofu"},
                {"name": "Braised Mixed Mushrooms", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["mushroom", "ginger", "scallions"], "supplier_key": "mushroom"},
                {"name": "Vegetarian Fried Rice", "category": "Main", "portion_amount": 250, "portion_unit": "g", "ingredients": ["rice", "vegetables", "soy sauce"], "supplier_key": "rice"},
                {"name": "Wok-Fried Broccoli with Garlic", "category": "Side", "portion_amount": 100, "portion_unit": "g", "ingredients": ["broccoli", "garlic", "sesame oil"], "supplier_key": "vegetable"},
                {"name": "Mango Sago Dessert", "category": "Dessert", "portion_amount": 120, "portion_unit": "g", "ingredients": ["mango", "sago", "coconut milk"], "supplier_key": "dessert"},
            ]

        return [
            {"name": "Chicken Dim Sum Platter", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["chicken", "dumpling wrapper", "ginger"], "supplier_key": "chicken"},
            {"name": "Sweet and Sour Fish Fillet", "category": "Main", "portion_amount": 180, "portion_unit": "g", "ingredients": ["fish", "sweet sour sauce", "capsicum"], "supplier_key": "fish"},
            {"name": "Yangzhou Fried Rice with Chicken Ham", "category": "Main", "portion_amount": 250, "portion_unit": "g", "ingredients": ["rice", "chicken ham", "vegetables"], "supplier_key": "rice"},
            {"name": "Wok-Fried Broccoli with Garlic", "category": "Side", "portion_amount": 100, "portion_unit": "g", "ingredients": ["broccoli", "garlic", "sesame oil"], "supplier_key": "vegetable"},
            {"name": "Mango Sago Dessert", "category": "Dessert", "portion_amount": 120, "portion_unit": "g", "ingredients": ["mango", "sago", "coconut milk"], "supplier_key": "dessert"},
        ]

    return []

def format_menu_text(menu_json: List[dict]) -> str:
    lines = []

    for i, item in enumerate(menu_json, 1):
        ingredients = ", ".join(item["ingredients"])
        lines.append(
            f"{i}. **{item['name']}** "
            f"({item['portion_amount']}{item['portion_unit']} per pax)\n"
            f"   Category: {item['category']}. Ingredients: {ingredients}."
        )

    return "\n\n".join(lines)


MENU_ITEM_RULES = {

    # JAPANESE
    "sushi": ("Sushi Item", "Main", "main"),
    "teriyaki": ("Teriyaki Item", "Main", "main"),
    "miso": ("Miso Dish", "Soup", "soup"),
    "edamame": ("Edamame", "Side", "side"),
    "ramen": ("Ramen", "Main", "main"),
    "tempura": ("Tempura", "Main", "main"),
    "dumpling": ("Japanese Dumplings", "Main", "main"),

    # MALAY
    "satay": ("Satay", "Main", "main"),
    "rendang": ("Rendang", "Main", "main"),
    "nasi": ("Rice Dish", "Main", "main"),
    "sambal": ("Sambal Side", "Side", "side"),
    "lemak": ("Coconut Rice Dish", "Main", "main"),
    "kuih": ("Traditional Dessert", "Dessert", "dessert"),
    "kerabu": ("Malay Salad", "Side", "side"),

    # CHINESE
    "fried rice": ("Fried Rice", "Main", "main"),
    "dim sum": ("Dim Sum", "Side", "side"),
    "wok": ("Wok Dish", "Main", "main"),
    "stir-fry": ("Stir Fry", "Main", "main"),
    "soy": ("Soy Dish", "Main", "main"),
    "ginger": ("Ginger Dish", "Main", "main"),

    # WESTERN
    "pasta": ("Pasta", "Main", "main"),
    "salad": ("Salad", "Side", "side"),
    "burger": ("Burger", "Main", "main"),
    "sandwich": ("Sandwich", "Main", "main"),
    "steak": ("Steak", "Main", "main"),
    "roasted": ("Roasted Dish", "Main", "main"),
    "grilled": ("Grilled Dish", "Main", "main"),

    # GENERIC
    "soup": ("Soup", "Soup", "soup"),
    "dessert": ("Dessert", "Dessert", "dessert"),
    "pudding": ("Pudding", "Dessert", "dessert"),
    "skewer": ("Skewers", "Main", "main"),
    "rice bowl": ("Rice Bowl", "Main", "main"),
    "spring roll": ("Spring Rolls", "Side", "side"),
    "tofu": ("Tofu Dish", "Main", "main"),
}

def classify_menu_line(line: str):
    text = line.lower()

    if any(k in text for k in ["soup", "broth", "miso broth", "consommé"]):
        return ("Soup Item", "Soup", "soup")

    if any(k in text for k in [
        "pudding",
        "kuih",
        "dessert",
        "mochi",
        "ice cream",
        "cake",
        "sweet",
        "matcha"
    ]):
        return ("Dessert Item", "Dessert", "dessert")

    if any(k in text for k in ["salad", "edamame", "spring roll", "dim sum", "sambal", "kerabu"]):
        return ("Side Item", "Side", "side")

    return ("Main Item", "Main", "main")

def extract_menu_lines(menu: str) -> List[str]:
    lines = []

    for line in menu.splitlines():
        clean = line.strip()

        # Match numbered menu items 
        if re.match(r"^\d+[\.\)]\s+", clean):
            lines.append(clean)

    return lines

def extract_portions_from_item(item: str):
    portions = []

    # Find only explicit quantity declarations
    quantity_match = re.search(
        r"\((\d+(?:\.\d+)?)\s*(g|kg|ml|l|pieces?|rolls?)",
        item,
        re.I,
    )

    if quantity_match:
        amount = float(quantity_match.group(1))
        unit = quantity_match.group(2).lower()

        # Use dish name instead of "per portion"
        dish_name = item.split("(")[0].strip()

        portions.append({
            "amount": amount,
            "unit": unit,
            "ingredient": dish_name
        })

    return portions

def build_structured_menu(menu: str) -> List[dict]:
    structured = []

    menu_lines = extract_menu_lines(menu)

    for line in menu_lines:
        clean = re.sub(r"^\d+[\.\)]\s+", "", line).strip()

        category = classify_menu_line(clean)[1]

        portions = extract_portions_from_item(clean)

        structured.append({
            "name": clean,
            "category": category,
            "portions": portions
        })

    return structured

def format_menu_for_inventory(menu: str) -> str:
    menu_lines = extract_menu_lines(menu)

    clean_items = []
    for line in menu_lines:
        item = re.sub(r"^\d+[\.\)]\s+", "", line).strip()
        clean_items.append(item)

    return "\n".join([f"{i+1}. {item}" for i, item in enumerate(clean_items)])
