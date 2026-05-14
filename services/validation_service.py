import re
from datetime import datetime
from utils.helpers import is_supported_west_malaysia_location
from models.catering_plan import CateringPlan
from services.menu_service import THEME_KEYWORDS

MIN_GUESTS = 20
MAX_GUESTS = 500
MIN_BUDGET = 70.0  # Quality floor
MAX_BUDGET = 500.0 # Upper ceiling

def validate_dietary_conflicts(user_request: str, menu: str):
    issues = []
    req, menu_txt = user_request.lower(), menu.lower()
    if "vegetarian" in req or "vegan" in req:
        for item in ["chicken", "beef", "duck", "lamb", "meat", "fish", "seafood", "prawn", "crab", "shrimp", "scallop", "shellfish", "oyster"]:
            if item in menu_txt:
                issues.append(f"RISK: HIGH - Menu contains '{item}' despite vegetarian/vegan request.")
    return issues

def contains_forbidden_pork(text: str) -> bool:
    normalized = text.lower()

    safe_phrases = [
        "pork-free",
        "pork free",
        "no pork",
        "without pork",
        "without bacon",
        "halal bacon",
        "bacon-free",
        "bacon free",
        "pork is not present",
        "does not contain pork",
    ]

    for phrase in safe_phrases:
        normalized = normalized.replace(phrase, "")

    forbidden = ["pork", "ham", "bacon", "lard", "char siu", "pepperoni", "prosciutto"]
    return any(item in normalized for item in forbidden)

def contains_alcohol_request(text: str) -> bool:
    normalized = text.lower()

    false_positive_phrases = [
        "licensed bar service is handled separately",
        "licensed bar service",
        "bar service available",
        "halal food provider with a licensed bar service",
    ]

    for phrase in false_positive_phrases:
        normalized = normalized.replace(phrase, "")

    alcohol_items = [
        "wine",
        "beer",
        "whiskey",
        "whisky",
        "sake",
        "vodka",
        "champagne",
        "cocktail",
        "bar service requested",
        "request alcohol",
        "serve alcohol",
    ]

    return any(item in normalized for item in alcohol_items)

def validate_plan(plan: CateringPlan, user_request: str) -> str:
    issues = []
    req_lower = user_request.lower()
    menu_lower = plan.menu.lower()
    
    # BUDGET LIMIT CHECK
    if plan.budget_per_head < MIN_BUDGET:
        issues.append(f"RISK: MEDIUM - Budget per head ({plan.budget_per_head}) is below the quality floor of RM {MIN_BUDGET}.")
    if plan.budget_per_head > MAX_BUDGET:
        issues.append(f"RISK: HIGH - Budget per head ({plan.budget_per_head}) exceeds the standard corporate ceiling of RM {MAX_BUDGET}.")

    # GUEST COUNT LIMIT CHECK
    if plan.guest_count < MIN_GUESTS:
        issues.append(f"RISK: MEDIUM - Guest count ({plan.guest_count}) is below the operational minimum of {MIN_GUESTS} pax.")
    if plan.guest_count > MAX_GUESTS:
        issues.append(f"RISK: HIGH - Guest count ({plan.guest_count}) exceeds maximum logistical capacity of {MAX_GUESTS} pax.")
        
    # EVENT TIMING 
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", user_request)
    if date_match:
        event_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
        today = datetime.now()
        days_until_event = (event_date - today).days

        # Rule: No Past events or Minimum 3 days notice for any event
        if days_until_event < 0:
            issues.append("RISK: HIGH - Event date is in the past. Booking cannot be accepted.")
        elif days_until_event < 3:
            issues.append("RISK: HIGH - Urgent booking: event date is less than 3 days away.")
          
        # Rule: Events > 200 pax require 7 days prep
        if plan.guest_count > 200 and days_until_event < 7:
            issues.append(f"RISK: HIGH - Large event ({plan.guest_count} pax) requires at least 7 days notice. Only {days_until_event} days provided.")
            
    # THEME AUTHENTICITY CHECK
    selected_theme = next((t for t in THEME_KEYWORDS.keys() if t.lower() in req_lower), None)
    if selected_theme:
        keywords = THEME_KEYWORDS[selected_theme]
        if not any(k in menu_lower for k in keywords):
            issues.append(f"RISK: MEDIUM - Menu does not appear to match the selected theme: {selected_theme}.")
            
    # Check Menu and Request for Pork 
    if contains_forbidden_pork(req_lower) or contains_forbidden_pork(menu_lower):
        issues.append("RISK: HIGH - Pork detected in the menu or request.")
    
    # Alcohol Request Handling
    if contains_alcohol_request(user_request):
        issues.append(
            "NOTICE: Licensed bar service requested. Alcohol must be transported and served separately from food."
        )
    
    # DIETARY CONFLICT CHECK (Using Regex for precision)
    banned_map = {
        "vegetarian": ["chicken", "beef", "duck", "lamb", "meat", "fish", "seafood", "prawn", "crab", "squid", "salmon"],
        "vegan": ["chicken", "beef", "duck", "lamb", "meat", "fish", "seafood", "prawn", "crab", "egg", "milk", "cheese", "butter", "honey", "cream", "mayo"],
        "nut allergy": ["peanut", "almond", "cashew", "walnut", "pecan", "hazelnut", "macadamia", "satay sauce", "nut"],
        "dairy free": ["milk", "cheese", "butter", "cream", "yogurt", "ghee", "whey"],
        "gluten free": ["wheat", "flour", "bread", "pasta", "soy sauce", "tempura", "noodle", "barley", "rye"]
    }
    for restriction, banned_items in banned_map.items():
        if restriction in req_lower:
            for item in banned_items:
                # \b matches word boundaries. Ensures "milk" doesn't trigger on "coconut milk"
                if re.search(rf"\b{re.escape(item)}\b", menu_lower):
                    
                    # Safe Exceptions for Dairy Free / Vegan
                    if item == "milk" and ("coconut milk" in menu_lower or "soy milk" in menu_lower or "almond milk" in menu_lower):
                        continue
                    if item == "mayo" and "vegan mayo" in menu_lower:
                        continue
                        
                    issues.append(f"RISK: HIGH - Menu contains '{item}' despite {restriction} request.")
  
    # Location Check
    if not is_supported_west_malaysia_location(user_request):
        issues.append("RISK: HIGH - Location is outside West Malaysia.")
    
    # Inventory Check
    if "LIMITED" in plan.inventory_report:
        issues.append("RISK: MEDIUM - One or more ingredients have limited supplier availability.")
    
    # Budget Check
    quote_match = re.search(r"\[FINAL QUOTE\]:?\s*RM\s*(\d+(?:\.\d+)?)", plan.pricing_breakdown, re.I)
    budget_limit_user = plan.budget_per_head
    if quote_match:
        final_per_head = float(quote_match.group(1))
        if final_per_head > budget_limit_user:
            issues.append(
                f"RISK: HIGH - Final quote RM {final_per_head:.2f} exceeds client budget of RM {budget_limit_user:.2f} per head."
            )
        if final_per_head < MIN_BUDGET:
            issues.append(
                f"RISK: MEDIUM - Final quote RM {final_per_head:.2f} is below our quality floor of RM {MIN_BUDGET:.2f}."
            )
        if final_per_head > MAX_BUDGET:
            issues.append(
                f"RISK: HIGH - Final quote RM {final_per_head:.2f} exceeds maximum system allowance."
            )
    else:
        issues.append(
            "RISK: HIGH - No valid pricing data found in RM format. Please review the Pricing Agent's breakdown."
        )
        
    if "FINAL_STATUS: SHORTAGE_DETECTED" in plan.inventory_report:
        issues.append("RISK: HIGH - Confirmed supplier shortage detected.")

    elif "UNKNOWN" in plan.inventory_report:
        issues.append("RISK: MEDIUM - Some inventory items have unknown supplier confirmation.")
        
    return "\n".join(issues) if issues else "SYSTEM VALIDATION: No hard-rule violations detected."
