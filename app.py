import asyncio
import os
import re
import json
from datetime import datetime
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel
import ollama
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient

load_dotenv()

MIN_GUESTS = 20
MAX_GUESTS = 500
MIN_BUDGET = 70.0  # Quality floor
MAX_BUDGET = 500.0 # Upper ceiling

class CateringPlan(BaseModel):
    plan_id: str = ""
    event_details: str = ""
    guest_count: int = 0
    budget_per_head: float = 0.0
    total_budget: float = 0.0
    menu: str = ""
    inventory_report: str = ""
    shortages_identified: List[str] = []
    logistics_timeline: str = ""
    pricing_breakdown: str = ""
    risk_assessment: str = ""
    compliance_report: str = ""
    proposal_review: str = ""
    system_validation: str = ""

# --- HELPER FUNCTIONS ---
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

def validate_dietary_conflicts(user_request: str, menu: str):
    issues = []
    req, menu_txt = user_request.lower(), menu.lower()
    if "vegetarian" in req or "vegan" in req:
        for item in ["chicken", "beef", "duck", "lamb", "meat", "fish", "seafood", "prawn", "crab"]:
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
        "pork is not present",
        "does not contain pork",
    ]

    for phrase in safe_phrases:
        normalized = normalized.replace(phrase, "")

    forbidden = ["pork", "ham", "bacon", "lard", "char siu"]
    return any(item in normalized for item in forbidden)

def contains_alcohol_request(text: str) -> bool:
    """Checks for alcohol which is permitted but requires logistical handling."""
    alcohol_items = ["wine", "beer", "whiskey", "sake", "alcohol", "vodka", "champagne"]
    return any(item in text.lower() for item in alcohol_items)

THEME_KEYWORDS = {
        "Japanese Fusion": ["sushi", "teriyaki", "miso", "tofu", "edamame", "tempura", "ramen"],
        "Traditional Malay": ["satay", "rendang", "nasi", "sambal", "lemak", "kerabu", "kuih"],
        "Western Corporate": ["pasta", "grilled", "salad", "steak", "roasted", "burger", "sandwich"],
        "Chinese Fusion": ["dim sum", "wok", "stir-fry", "dumpling", "ginger", "soy", "fried rice"]
    }

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

        # Rule: Minimum 3 days notice for any event
        if days_until_event < 3:
            issues.append("RISK: HIGH - Same-day or urgent booking (less than 3 days notice).")

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
    if contains_alcohol_request(req_lower):
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
    
    # Budget Check
    quote_match = re.search(r"\[FINAL QUOTE\]:?\s*RM\s*(\d+(?:\.\d+)?)", plan.pricing_breakdown, re.I)
    budget_limit_user = plan.budget_per_head 
    if quote_match:
        extracted_val = float(quote_match.group(1))
        final_per_head = extracted_val
        # Check against User's own budget
        if final_per_head > budget_limit_user:
            issues.append(f"RISK: HIGH - Final quote RM {final_per_head:.2f} exceeds client budget of RM {budget_limit_user:.2f} per head.")
        # Check against System Minimum (Quality Floor)
        if final_per_head < MIN_BUDGET:
            issues.append(f"RISK: MEDIUM - Final quote RM {final_per_head:.2f} is below our quality floor of RM {MIN_BUDGET:.2f}.")     
        # Check against System Maximum
        if final_per_head > MAX_BUDGET:
            issues.append(f"RISK: HIGH - Final quote RM {final_per_head:.2f} exceeds maximum system allowance.")
        # FALLBACK: If the [FINAL QUOTE] tag or RM symbol was missing/malformed
        all_rm_prices = extract_currency_values(plan.pricing_breakdown) 
        if all_rm_prices:
            # Look for values that represent a single person's cost (filter out Grand Totals)
            per_head_candidates = [p for p in all_rm_prices if p < (budget_limit_user * 2)]
            if per_head_candidates and max(per_head_candidates) > budget_limit_user:
                issues.append(f"RISK: HIGH - Detected pricing item (RM {max(per_head_candidates):.2f}) exceeds budget per head.")
        else:
            issues.append("RISK: HIGH - No valid pricing data found in RM format. Please review the Pricing Agent's breakdown.")
            
    return "\n".join(issues) if issues else "SYSTEM VALIDATION: No hard-rule violations detected."

def load_knowledge_file(filename: str) -> str:
    path = os.path.join("knowledge", filename)
    try:
        with open(path, "r", encoding="utf-8") as file: return file.read()
    except FileNotFoundError: return f"{filename} not found."

def create_search_client():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index = os.getenv("AZURE_SEARCH_INDEX")
    if not endpoint or not key or not index: return None
    return SearchClient(endpoint=endpoint, index_name=index, credential=AzureKeyCredential(key))

def search_knowledge(query: str, top: int = 5) -> str:
    client = create_search_client()
    if client is None: return "Azure AI Search is not configured."
    results = client.search(search_text=query, top=top)
    docs = [json.dumps(dict(result), indent=2, default=str) for result in results]
    return "\n\n".join(docs) if docs else "No matching knowledge found."

def save_feedback(feedback_data):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string: return {"message": "Storage not configured", "blob": "none"}
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client("feedback")
    try: container_client.create_container()
    except: pass
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_id = feedback_data.get("customer_feedback", {}).get("plan_id", timestamp)
    blob_name = f"feedback_{plan_id}.json"
    container_client.upload_blob(name=blob_name, data=json.dumps(feedback_data, indent=2), overwrite=True)
    return {"message": "Feedback saved", "blob": blob_name}

def save_plan_to_blob(plan: CateringPlan) -> str:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string: return "Not Configured"
    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client(os.getenv("AZURE_STORAGE_CONTAINER", "plans"))
    try: container_client.create_container()
    except: pass
    blob_name = f"{plan.plan_id}.json"
    container_client.upload_blob(name=blob_name, data=json.dumps(plan.model_dump(), indent=2), overwrite=True)
    return blob_name

class OllamaAgent:
    def __init__(self, model: str, name: str, instructions: str):
        self.model, self.name, self.instructions = model, name, instructions
    async def run(self, message: str):
        prompt = f"You are {self.name}.\nInstructions:\n{self.instructions}\nTask: {message}"
        response = await asyncio.to_thread(ollama.chat, model=self.model, messages=[{"role": "user", "content": prompt}])
        class Result: text = response["message"]["content"]
        return Result()

PRICE_RULES = {
    "main": 22.0,
    "side": 10.0,
    "soup": 8.0,
    "dessert": 7.0,
    "service": 10.0,
    "eco_packaging": 5.0,
}

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

    if any(k in text for k in ["soup", "miso broth"]):
        return ("Soup Item", "Soup", "soup")

    if any(k in text for k in ["pudding", "kuih", "dessert"]):
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

def format_menu_for_inventory(menu: str) -> str:
    menu_lines = extract_menu_lines(menu)

    clean_items = []
    for line in menu_lines:
        item = re.sub(r"^\d+[\.\)]\s+", "", line).strip()
        clean_items.append(item)

    return "\n".join([f"{i+1}. {item}" for i, item in enumerate(clean_items)])

def calculate_final_quote(menu: str, guest_count: int, budget_per_head: float) -> str:
    items = []
    menu_lines = extract_menu_lines(menu)

    for line in menu_lines:
        item_name, category, price_key = classify_menu_line(line)

        # Remove numbering for display
        display_name = re.sub(r"^\d+[\.\)]\s+", "", line)
        display_name = display_name.split(" - ")[0].strip()

        items.append((display_name, category, PRICE_RULES[price_key]))

    items.append(("Service Fee", "Fixed Fee", PRICE_RULES["service"]))
    items.append(("Eco-Packaging", "Fixed Fee", PRICE_RULES["eco_packaging"]))

    total_per_head = sum(item[2] for item in items)

    if total_per_head < MIN_BUDGET:
        adjustment = MIN_BUDGET - total_per_head
        items.append(("Quality Floor Adjustment", "Adjustment", adjustment))
        total_per_head = MIN_BUDGET

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
   
# --- MAIN WORKFLOW ---
async def generate_catering_plan(user_request: str, progress_callback=None):
    # Define a progress logger
    async def send_progress(step: str):
        # This prints to your VS Code / System Terminal
        print(f"\n[WORKFLOW STEP]: {step}") 
        print("-" * 30)
        
        # This sends to the React Frontend
        if progress_callback: 
            await progress_callback(step)

    model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    
    # -- 1. INITIALIZE THE PLAN OBJECT ---
    plan = CateringPlan()
    plan.plan_id = datetime.now().strftime("plan_%Y%m%d_%H%M%S")
    plan.guest_count = extract_guest_count(user_request)
    plan.budget_per_head = extract_budget_per_head(user_request)
    plan.total_budget = plan.guest_count * plan.budget_per_head
    
    print(f"\nStarting Catering Workflow for: {user_request[:500]}...")
    
    # --- 2. INITIALIZE AGENTS ---    
    receptionist = OllamaAgent(model, "Receptionist", "Extract event details: Type, Count, Budget, Theme, Diet.")
    
    chef = OllamaAgent(model, "Chef", """
        You are the Executive Chef. Create a Halal-certified menu strictly following the THEME and DIETARY needs.

        THEME GUIDELINES:
        - Japanese Fusion: Use sushi, teriyaki, miso, tofu, edamame, tempura, ramen-inspired bowls. Do not use Western dishes unless requested.
        - Traditional Malay: Use nasi, rendang-style spices, lemongrass, turmeric, coconut, sambal, kerabu, kuih. Do not use Japanese or Western dishes unless requested.
        - Western Corporate: Use grilled vegetables, roasted potatoes, pasta, salad, sandwiches, mushroom risotto, herb sauces, garlic, olive oil, roasted textures. Do NOT use miso, teriyaki, tamari, edamame, sushi, lemongrass, turmeric, sambal, nasi, rendang, or Japanese/Malay fusion terms unless requested.
        - Chinese Fusion: Use fried rice, dim sum, stir-fry, ginger, soy-style sauces, dumplings, wok vegetables. Do not use Japanese, Malay, or Western dishes unless requested.

        IMPORTANT THEME RULE:
        Only generate dishes that match the selected theme. Do not mix ingredients from other themes unless the client explicitly requests fusion.

        SUBSTITUTION GUIDE:
        - VEGAN/VEGETARIAN: Use Tofu, Tempeh, Mushrooms, Lentils, Beans, or Chickpeas. Use Edamame only for Japanese Fusion.
        - NUT ALLERGY: Use Sunflower seeds or omit nuts.
        - DAIRY FREE: Use Coconut or Soy milk. 
        - GLUTEN FREE: Use Rice, Quinoa, or Glass Noodles.
        - PORK: Strictly forbidden. 

        OUTPUT FORMAT RULES:
        1. Provide a numbered list of dishes with brief descriptions.
        2. PORTION SIZING: Every dish must include estimated portion sizes (e.g., 150g protein, 100g sides).
        3. NO NOTES/DISCLAIMERS: Output ONLY the menu. Do not add intro text, concluding summaries, or "Revised" notes.
        4. VEGETARIAN WORD-BAN: If the request is Vegetarian/Vegan, NEVER use the words 'meat', 'chicken', 'fish', 'beef', or 'seafood' in your response.
        5. NO CONTEXT SHARING: Do not explain your changes (e.g., do not say 'replaced Edamame' or 'new addition'). Just output the final, polished menu as if it were the only version.
        6. NO PRICING: Absolutely do not mention prices, currency, RM, or $ symbols. 
           The Pricing Agent handles all financial data. You only handle food.
    """)
        
    inv_agent = OllamaAgent(model, "Inventory_Manager", f"""
        You are the Inventory & Procurement Agent.

        CRITICAL RULE:
        The APPROVED MENU ITEMS list is the only source of truth.
        
        INVALID RESPONSE RULE:
        If you mention any dish not present in APPROVED MENU ITEMS,
        your answer is invalid.

        STRICT RULES:
        - Use only the approved menu items.
        - Do not add dishes.
        - Do not replace dishes.
        - Do not use template dishes.
        - Do not mention salmon, chicken, beef, fish, seafood, or any dish unless it appears in APPROVED MENU ITEMS.
        - If supplier data mentions another dish, ignore it.
        - If supplier data is unclear:
            - do not guess
            - do not substitute
            - report availability as UNKNOWN

        TASKS:
        1. Copy the approved menu items EXACTLY as written.
        2. Do not paraphrase item names.
        3. Preserve original wording exactly.
        4. Create a procurement list using only those items.
        5. Calculate total quantities for {plan.guest_count} guests.
        6. Mention shortages only for approved menu items.
        7. Use only RM for currency.
        
        FINAL STATUS RULE:
        At the end of your report, output EXACTLY ONE of these:
        FINAL_STATUS: NO_SHORTAGE
        OR
        FINAL_STATUS: SHORTAGE_DETECTED
        
        MENU LOCK RULE:
        The APPROVED MENU ITEMS are frozen.
        You are NOT allowed to:
        - invent replacement dishes
        - invent unavailable dishes
        - introduce proteins not present in the approved menu
        - reuse old menu examples
        - create generic Western sample menus

        If a shortage exists:
        - mention only the affected approved dish
        - suggest quantity reduction only
        - do not redesign the menu
        
        OUTPUT FORMAT:

        APPROVED MENU:
        - item list

        PROCUREMENT LIST:
        - item list

        AVAILABILITY:
        - AVAILABLE
        - SHORTAGE
        - UNKNOWN

        SHORTAGE DETAILS:
        - item + quantity only

        FINAL STATUS:
        FINAL_STATUS: NO_SHORTAGE
        OR
        FINAL_STATUS: SHORTAGE_DETECTED
    """)
        
    comp_agent = OllamaAgent(model, "Compliance", """
        Verify only the actual menu text provided.

        State: 'This proposal is prepared for Halal-compliant food with Licensed Bar Service.'

        Rules:
        - Do NOT invent ingredients that are not written in the menu.
        - Do NOT assume hidden fish, meat, alcohol, pork, or allergens unless the exact ingredient appears in the menu.
        - Only evaluate restrictions explicitly requested by the client.
            Examples:
            - Nut Allergy -> check only nuts and peanut-related ingredients
            - Vegetarian -> check only animal products
            - Vegan -> check animal and dairy products
            - Gluten Free -> check gluten ingredients
            Never evaluate unrelated restrictions.
        - Alcohol is permitted only as licensed bar service and must be handled separately from food.
        - If the menu does not explicitly contain a forbidden item, say LOW RISK.
        - Keep the report short and evidence-based.
    """)
    
    log_agent = OllamaAgent(model, "Logistics", """
        Create an operational timeline. Do NOT calculate exact calendar dates. Structure your response strictly using these headers:
        [PHASE 1: PROCUREMENT] (Lead time for ingredients and eco-packaging)
        [PHASE 2: PREPARATION] (Kitchen prep and Halal-certified cleaning)
        [PHASE 3: EXECUTION] (Day of event, delivery 2 hours before start)
        Focus on transport rules: Alcohol must be separate from food.
    """)
        
    mon_agent = OllamaAgent(model, "Monitor", """
        You are the Monitoring Agent and Safety Auditor.

        Only evaluate dietary restrictions explicitly requested by the client.

        Rules:
        - If the request says Vegetarian, check only for animal products.
        - If the request says Vegan, check for animal products, egg, milk, cheese, butter, honey, cream, and mayo.
        - If the request says Nut Allergy, check only for peanut, almond, cashew, walnut, satay sauce, and nuts.
        - If the request says Gluten Free, check only for wheat, flour, bread, pasta, soy sauce, tempura, noodles, barley, and rye.
        - If the request says Dairy Free, check only for milk, cheese, butter, cream, yogurt, ghee, and whey.

        Do NOT assess restrictions that were not requested.
        Do NOT invent ingredients.
        Do NOT assume tamari, soy sauce, miso, or ginger contains animal products.
        Do NOT check budget or pricing.

        Output format:
        - Requested restriction checked:
        - Evidence from menu:
        - Risk level:
        - Recommendation:
    """)
    
    pricing_agent = OllamaAgent(model, "Pricing_Optimization_Agent", """
        You are the Pricing & Optimization Agent.

        Your job:
        1. Explain the pricing strategy.
        2. Check whether the quote fits the client budget.
        3. Suggest cost optimization if needed.

        IMPORTANT:
        - Do NOT calculate the final quote yourself.
        - Do NOT invent totals.
        - Python will calculate the exact final quote.
        - Use the pricing data provided to explain the result.
        """)
    
    rev_agent = OllamaAgent(model, "Reviewer", """
        Rate the overall proposal quality.

        Review:
        1. Whether the menu matches the selected theme.
        2. Whether the proposal respects dietary requirements.
        3. Whether the plan is operationally clear.
        4. Whether the proposal sounds professional.

        Do NOT invent non-halal issues.
        Do NOT claim tamari, turmeric, ginger, soy, or miso is non-halal unless alcohol or animal-derived ingredients are explicitly stated.

        If religious rules are followed, say: 'All religious dietary restrictions met.'
    """)
        
    # --- 3. START WORKFLOW ---
    # 3.1. Receptionist
    await send_progress("Running Receptionist Agent...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    # 3.2. Search and Temp Menu
    await send_progress("Loading knowledge Azure AI Search...")
    themes = ["Japanese Fusion", "Traditional Malay", "Western Corporate", "Chinese Fusion", "International Buffet"]
    selected_theme = next((t for t in themes if t.lower() in user_request.lower()), "International Buffet")
    knowledge = search_knowledge(f"{selected_theme} {user_request}")

    # 3.3. Chef
    await send_progress(f"Planning {selected_theme} menu...")
    res = await chef.run(f"SELECTED THEME: {selected_theme}\nRequest: {plan.event_details}\nKnowledge: {knowledge}")
    current_menu = res.text
    
    # 3.4. Inventory
    await send_progress("Checking inventory...")
    inventory_menu = format_menu_for_inventory(current_menu)
    res = await inv_agent.run(
        f"""
    APPROVED MENU ITEMS:
    {inventory_menu}

    GUEST COUNT:
    {plan.guest_count}

    Use only the approved menu items.
    Return the report using the required output format.
    """
    )
    plan.inventory_report = res.text
    
    # Only trigger revision if a REAL shortage exists
    if re.search(r"FINAL_STATUS:\s*SHORTAGE_DETECTED", plan.inventory_report, re.I):
        await send_progress("Revising menu based on inventory shortages...")
        res = await chef.run(
            f"""
    ORIGINAL MENU:
    {current_menu}
    INVENTORY FEEDBACK:
    {plan.inventory_report}
    TASK:
    You may ONLY modify dishes explicitly marked as SHORTAGE in the inventory report.

    STRICT RULES:
    - Keep all unaffected dishes EXACTLY unchanged.
    - Do not rewrite the entire menu.
    - Do not rename dishes.
    - Do not introduce new dishes.
    - Do not introduce new proteins.
    - Do not change the selected theme.
    - If no shortage exists, return the ORIGINAL MENU exactly unchanged.

    Output ONLY the final numbered menu.
    """
        )
        current_menu = res.text
    else:
        await send_progress("No inventory shortages detected. Keeping original menu.")

    # 3.5. Compliance
    await send_progress("Checking compliance...")
    res = await comp_agent.run(
        f"""
    Client Request:
    {user_request}
    Menu Text:
    {current_menu}
    Task:
    Check only the menu text against the client request.
    Do not invent ingredients.
    """
    )
    plan.compliance_report = res.text
    await send_progress("Revising menu based on compliance feedback...")
    res = await chef.run(
        f"""
    ORIGINAL MENU:
    {current_menu}
    COMPLIANCE FEEDBACK:
    {plan.compliance_report}
    TASK:
    Only revise the menu if the compliance report identifies a real HIGH RISK issue in the original menu.
    Rules:
    - Do not add new dishes.
    - Do not introduce dishes from another theme.
    - Keep the selected theme unchanged.
    - If there is no HIGH RISK issue, return the original menu unchanged.
    - Output only the final numbered menu.
    """
    )
    plan.menu = res.text # Final menu assigned here
    
    # 3.6. Logistics
    await send_progress("Planning logistics...")
    today = datetime.now().strftime("%Y-%m-%d")
    res = await log_agent.run(f"Today is {today}. Client Request: {user_request}\nMenu: {plan.menu}")
    plan.logistics_timeline = res.text

    # 3.7. Monitor
    await send_progress("Auditing risks...")
    if "dietary needs: none" in user_request.lower():
        plan.risk_assessment = """
    Requested restriction checked: None
    Evidence from menu: No dietary restriction was explicitly requested by the client.
    Risk level: LOW
    Recommendation: No dietary-specific changes required.
    """
    else:
        res = await mon_agent.run(f"Request: {user_request}\nMenu: {plan.menu}")
        plan.risk_assessment = res.text

    # 3.8. Pricing & Optimization
    await send_progress("Calculating pricing...")
    pricing_table = calculate_final_quote(
        menu=plan.menu,
        guest_count=plan.guest_count,
        budget_per_head=plan.budget_per_head
    )
    res = await pricing_agent.run(
        f"""
    Client Budget Per Head: RM {plan.budget_per_head}
    Guest Count: {plan.guest_count}
    Python-Calculated Pricing:
    {pricing_table}
    Task:
    Explain whether the quote is suitable, whether it is within budget,
    and suggest optimization strategies if required.
    Do not change the final quote.
    """
    )
    plan.pricing_breakdown = pricing_table + "\n\nPricing Strategy:\n" + res.text

    # 3.9. Reviewer
    await send_progress("Reviewing proposal...")
    res = await rev_agent.run(f"Plan: {plan.menu}")
    plan.proposal_review = res.text

    # --- 4. FINAL VALIDATION & SAVE ---
    plan.system_validation = validate_plan(plan, user_request)
    await send_progress("Saving plan to Azure Blob...")
    save_plan_to_blob(plan)
    print("\nWORKFLOW COMPLETE\n")
    return plan.model_dump()

async def analyze_feedback(feedback_data):
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    feedback_agent = OllamaAgent(model_name, "Feedback_Agent", "Analyze feedback sentiment.")
    res = await feedback_agent.run(json.dumps(feedback_data))
    return res.text