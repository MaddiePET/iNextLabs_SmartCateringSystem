import re
from typing import List
from services.menus.japanese_fusion import JAPANESE_FUSION_MENUS
from services.menus.traditional_malay import TRADITIONAL_MALAY_MENUS
from services.menus.western_corporate import WESTERN_CORPORATE_MENUS
from services.menus.chinese_fusion import CHINESE_FUSION_MENUS

THEME_KEYWORDS = {
        "Japanese Fusion": ["sushi", "teriyaki", "miso", "tofu", "edamame", "tempura", "ramen"],
        "Traditional Malay": ["satay", "rendang", "nasi", "sambal", "lemak", "kerabu", "kuih"],
        "Western Corporate": ["pasta", "grilled", "salad", "steak", "roasted", "burger", "sandwich"],
        "Chinese Fusion": ["dim sum", "wok", "stir-fry", "dumpling", "ginger", "soy", "fried rice"]
    }

THEME_MENU_MAP = {
    "Japanese Fusion": JAPANESE_FUSION_MENUS,
    "Traditional Malay": TRADITIONAL_MALAY_MENUS,
    "Western Corporate": WESTERN_CORPORATE_MENUS,
    "Chinese Fusion": CHINESE_FUSION_MENUS,
}

def get_diet_key(dietary: str) -> str:
    dietary_lower = dietary.lower()

    if "vegan" in dietary_lower:
        return "vegan"
    if "vegetarian" in dietary_lower:
        return "vegetarian"
    if "gluten free" in dietary_lower:
        return "gluten_free"
    if "dairy free" in dietary_lower:
        return "dairy_free"
    if "nut allergy" in dietary_lower:
        return "nut_allergy"

    return "none"

def build_menu_json(selected_theme: str, dietary: str) -> List[dict]:
    menus = THEME_MENU_MAP.get(selected_theme)
    if not menus:
        menus = JAPANESE_FUSION_MENUS

    diet_key = get_diet_key(dietary)

    return menus.get(diet_key, menus["none"])
    
    

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
