

SUPPLIER_AVAILABILITY = {
    "mushroom": ("AVAILABLE", "Cameron Highlands Organic Cooperative", "48 hours"),
    "vegetable": ("AVAILABLE", "Cameron Highlands Organic Cooperative", "48 hours"),
    "tofu": ("AVAILABLE", "Cameron Highlands Organic Cooperative", "48 hours"),
    "rice": ("AVAILABLE", "Local Grain Supplier", "48 hours"),
    "sushi": ("AVAILABLE", "Local Japanese Ingredients Supplier", "48 hours"),
    "seaweed": ("AVAILABLE", "Local Japanese Ingredients Supplier", "48 hours"),
    "wakame": ("AVAILABLE", "Local Japanese Ingredients Supplier", "48 hours"),
    "edamame": ("AVAILABLE", "Frozen Produce Supplier", "48 hours"),
    "avocado": ("LIMITED", "Fresh Produce Supplier", "72 hours"),
    "cucumber": ("AVAILABLE", "Cameron Highlands Organic Cooperative", "48 hours"),
    "sauce": ("AVAILABLE", "Kitchen Prepared", "24 hours"),
    "soup": ("AVAILABLE", "Kitchen Prepared", "24 hours"),
    "prawn": ("CRITICAL SHORTAGE", "Port Klang Daily Catch", "12 hours"),
    "crab": ("CRITICAL SHORTAGE", "Port Klang Daily Catch", "12 hours"),
    "vegetable sushi platter": ("AVAILABLE", "Japanese Ingredients Supplier", "48 hours"),
    "grilled mushroom teriyaki": ("AVAILABLE", "Organic Mushroom Supplier", "48 hours"),
    "agedashi tofu": ("AVAILABLE", "Tofu Supplier", "48 hours"),
    "edamame": ("AVAILABLE", "Frozen Produce Supplier", "48 hours"),
    "matcha mochi dessert": ("LIMITED", "Japanese Dessert Supplier", "72 hours"),
    "matcha": ("AVAILABLE", "Japanese Dessert Supplier", "72 hours"),
    "coconut panna cotta": ("AVAILABLE", "Dessert Prep Kitchen", "48 hours"),
    "panna cotta": ("AVAILABLE", "Dessert Prep Kitchen", "48 hours"),
    "chicken": ("AVAILABLE", "KL Central Poultry Farm", "24 hours"),
"beef": ("LIMITED", "KL Central Poultry Farm", "48 hours"),
"fish": ("AVAILABLE", "Port Klang Daily Catch", "12 hours"),
"dessert": ("AVAILABLE", "Dessert Prep Kitchen", "48 hours"),
"kuih": ("AVAILABLE", "Malay Dessert Supplier", "48 hours"),
}

def get_supplier_status(item_name: str):
    text = item_name.lower()

    for keyword, data in SUPPLIER_AVAILABILITY.items():
        if keyword in text:
            return data

    return ("UNKNOWN", "No mapped supplier", "Unknown")
