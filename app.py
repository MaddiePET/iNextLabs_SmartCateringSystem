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
    """Strictly checks for pork which is forbidden in this model."""
    forbidden = ["pork", "ham", "bacon", "lard", "char siu"]
    return any(item in text.lower() for item in forbidden)

def contains_alcohol_request(text: str) -> bool:
    """Checks for alcohol which is permitted but requires logistical handling."""
    alcohol_items = ["wine", "beer", "whiskey", "sake", "alcohol", "vodka", "champagne"]
    return any(item in text.lower() for item in alcohol_items)

def validate_plan(plan: CateringPlan, user_request: str) -> str:
    issues = []
    req_lower = user_request.lower()
    menu_lower = plan.menu.lower()
    
    # 1. Check Menu and Request for Pork 
    if contains_forbidden_pork(req_lower) or contains_forbidden_pork(menu_lower):
        # We check if the Chef actually put it in the menu
        issues.append("RISK: HIGH - Pork detected in the menu or request.")
        
    # 2. DIETARY CONFLICT CHECK (Using Regex for precision)
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
  
    # 3. Location Check
    if not is_supported_west_malaysia_location(user_request):
        issues.append("RISK: HIGH - Location is outside West Malaysia.")
    
    # 4. Budget Check
    budget_limit = plan.budget_per_head 
    quote_match = re.search(r"\[FINAL QUOTE\]:?\s*RM\s*(\d+(?:\.\d+)?)", plan.pricing_breakdown, re.I)
    if quote_match:
        final_per_head = float(quote_match.group(1))
        if final_per_head > budget_limit:
            issues.append(f"RISK: HIGH - Final quote RM{final_per_head} exceeds budget of RM{budget_limit} per head.")
    else:
        all_prices = extract_currency_values(plan.pricing_breakdown)
        violations = [p for p in all_prices if p > budget_limit and p < 500]
        if violations:
            issues.append(f"RISK: HIGH - Pricing violation: RM{max(violations)} exceeds RM{budget_limit} limit.")
       
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
    plan.budget_per_head = 120.0  # Default budget
    plan.total_budget = plan.guest_count * plan.budget_per_head
    
    print(f"\nStarting Catering Workflow for: {user_request[:500]}...")
    
    # --- 2. INITIALIZE AGENTS ---    
    receptionist = OllamaAgent(model, "Receptionist", "Extract event details: Type, Count, Budget, Theme, Diet.")
    
    chef = OllamaAgent(model, "Chef", """
        You are the Executive Chef. Create a halal menu based on dietary needs.
        STRICT RULES:
        1. Focus ONLY on the food dishes and descriptions. 
        2. NEVER mention prices or total costs (the Accountant will handle that).
        3. ALCOHOL: Do NOT cook with alcohol (no mirin/sake in sauces). Use Halal-certified soy and ginger for flavor.
        
        STRICT SUBSTITUTION RULES:
        1. VEGAN: No animal products. Use Tofu, Tempeh, or Mushrooms.
        2. NUT ALLERGY: Zero tolerance for peanuts/tree nuts. Use Sunflower seeds or omit nuts entirely.
        3. DAIRY FREE: Use Coconut milk or Soy milk instead of cream/milk.
        4. GLUTEN FREE: Use Rice, Quinoa, or Glass Noodles. If using Soy Sauce, specify "Tamari (Gluten-Free Soy Sauce)". 
        5. No Pork under any circumstances.
        6. VEGETARIAN: Use Tofu, Mushrooms, or Edamame. 
        
        Output ONLY the menu items and descriptions, and estimated portion sizes per guest (e.g., 200g protein, 150g sides)..
        CRITICAL RULE: Output ONLY the numbered dish names and descriptions. DO NOT add any concluding notes, summaries, or disclaimers at the bottom. Never use the words 'meat' or 'seafood' in your output for vegetarian menus.
    """)
    
    inv_agent = OllamaAgent(model, "Inventory_Manager", """
        1. Check food ingredients against shortages.
        2. After identifying shortages, generate a clear Procurement List of exactly what needs to be ordered from suppliers.
        3. Check packaging requirements. If 'eco-friendly' is requested, verify stock for Sugarcane pulp boxes and Cornstarch cutlery.
        4. Note the 72-hour lead time for eco-packaging. If the event is sooner than 72 hours, flag this as a shortage/delay.
    """)
    
    comp_agent = OllamaAgent(model, "Compliance", """
        Verify rules. State: 'This proposal is prepared for Halal-compliant food with Licensed Bar Service.'
        - Flag RISK: HIGH if Pork is requested.
        - Alcohol is PERMITTED for service but must be handled separately from food.
        - Cross-check Vegetarian needs vs Menu.
    """)
    
    log_agent = OllamaAgent(model, "Logistics", """
        Create an operational timeline. Do NOT calculate exact calendar dates. Structure your response strictly using these headers:
        [PHASE 1: PROCUREMENT] (Lead time for ingredients and eco-packaging)
        [PHASE 2: PREPARATION] (Kitchen prep and Halal-certified cleaning)
        [PHASE 3: EXECUTION] (Day of event, delivery 2 hours before start)
        Focus on transport rules: Alcohol must be separate from food.
    """)
        
    mon_agent = OllamaAgent(model, "Monitor", """
       You are the Safety Auditor. Perform a 'Negative Scan' for dietary safety.
        Flag RISK: HIGH if Vegetarian/Vegan request contains animal products.
        Flag RISK: HIGH if Nut Allergy request contains nuts/satay.
        Flag RISK: HIGH if Gluten Free request contains tempura/wheat/soy sauce.
        Assume basic flour is unsafe for Gluten-Free unless specified otherwise.
        NOTE: Do NOT check budget or math (Python handles this). Focus ONLY on ingredients.
    """)
    
    acc_agent = OllamaAgent(model, "Accountant", """
        You are the Financial Controller. Create a SINGLE Markdown table.
        RULES:
        1. The TOTAL sum of the 'Price Per Head' column MUST be strictly less than or equal to the budget provided.
        2. Since this is a small model, keep individual dish prices low (e.g. RM 10 - RM 25) to ensure the total stays under budget.
        3. Output ONLY one table. Do not split food and fees into separate tables.
        4. At the very end, below the table, write: [FINAL QUOTE]: RM (Total Sum)
    """)
    
    rev_agent = OllamaAgent(model, "Reviewer", """
        Rate the proposal. 
        Check if the Japanese theme is authentic and Halal-certified (mirin-free).
        IMPORTANT: Do not use the word 'p/o/r/k' in your response. If religious rules are followed, say 'All religious dietary restrictions met'.
    """)
    
    # --- 3. START WORKFLOW ---
    # 3.1. Receptionist
    await send_progress("Running Receptionist Agent...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    # 3.2. Search and Temp Menu
    await send_progress("Loading knowledge Azure AI Search...")
    knowledge = search_knowledge(user_request)

    # 3.3. Chef
    await send_progress("Planning initial menu...")
    res = await chef.run(f"Request: {plan.event_details}\nKnowledge: {knowledge}")
    current_menu = res.text #Temp menu
    
    # 3.4. Inventory
    await send_progress("Checking inventory...")
    res = await inv_agent.run(f"Proposed Menu: {current_menu}\nContext: {user_request}")
    plan.inventory_report = res.text
    await send_progress("Revising menu based on inventory feedback...")
    # Chef talks to Inventory
    res = await chef.run(f"Inventory Feedback: {plan.inventory_report}\nOriginal Menu: {current_menu}\nTask: Update the menu ONLY if there are shortages or substitution needs.")
    current_menu = res.text 

    # 3.5. Compliance
    await send_progress("Checking compliance...")
    res = await comp_agent.run(f"Menu: {current_menu}\nKnowledge: {knowledge}")
    plan.compliance_report = res.text
    await send_progress("Revising menu based on compliance feedback...")
    res = await chef.run(f"Compliance Feedback: {plan.compliance_report}\nMenu: {current_menu}\nTask: Fix any Halal or Vegetarian violations.")
    plan.menu = res.text # Final menu assigned here
    
    # 3.6. Logistics
    await send_progress("Planning logistics...")
    today = datetime.now().strftime("%Y-%m-%d")
    res = await log_agent.run(f"Today is {today}. Client Request: {user_request}\nMenu: {plan.menu}")
    plan.logistics_timeline = res.text

    # 3.7. Monitor
    await send_progress("Auditing risks...")
    res = await mon_agent.run(f"Request: {user_request}\nMenu: {plan.menu}")
    plan.risk_assessment = res.text

    # 3.8. Accountant
    await send_progress("Optimizing pricing...")
    res = await acc_agent.run(f"Menu: {plan.menu}\nGuests: {plan.guest_count}\nBudget: RM{plan.total_budget}")
    plan.pricing_breakdown = res.text

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