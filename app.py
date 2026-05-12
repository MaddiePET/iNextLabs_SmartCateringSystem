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

def extract_guest_count(text: str) -> int:
    match = re.search(r"Guest count:\s*(\d+)", text, re.I)

    if match:
        return int(match.group(1))

    return 0

def extract_currency_values(text: str) -> List[float]:
    matches = re.findall(r"RM\s?(\d+(?:\.\d+)?)", text or "", re.I)
    return [float(x) for x in matches]


def is_supported_west_malaysia_location(text: str) -> bool:
    supported = [
        "kuala lumpur", "selangor", "penang", "johor", "perak",
        "negeri sembilan", "melaka", "malacca", "kedah", "perlis",
        "kelantan", "terengganu", "pahang", "putrajaya"
    ]

    unsupported = [
        "sabah", "sarawak", "labuan", "london", "singapore",
        "thailand", "indonesia", "japan", "australia", "uk"
    ]

    normalized = text.lower()

    if any(place in normalized for place in unsupported):
        return False

    return any(place in normalized for place in supported)


def contains_non_halal_request(text: str) -> bool:
    forbidden = ["pork", "wine", "alcohol", "beer", "whiskey", "ham", "bacon"]
    normalized = text.lower()
    return any(item in normalized for item in forbidden)


def validate_plan(plan: CateringPlan, user_request: str) -> str:
    issues = []
    date_match = re.search(r"Event date:\s*(\d{4}-\d{2}-\d{2})", user_request, re.I)

    issues.extend(
        validate_dietary_conflicts(user_request, plan.menu)
    )
    if date_match:
        event_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()
        today = datetime.now().date()
        days_until_event = (event_date - today).days

        if days_until_event <= 0:
            issues.append("RISK: HIGH - Same-day or past-date event request is not feasible.")
        elif plan.guest_count > 200 and days_until_event < 7:
            issues.append(
                f"RISK: HIGH - Events above 200 pax require at least 7 days preparation time. Only {days_until_event} day(s) available."
            )
        elif days_until_event < 3:
            issues.append(
                f"RISK: HIGH - Minimum booking notice is 3 days. Only {days_until_event} day(s) available."
            )

    if contains_non_halal_request(user_request):
        issues.append(
            "RISK: HIGH - Customer requested pork, wine, alcohol, or non-halal items. This business is halal-compliant only."
        )

    if not is_supported_west_malaysia_location(user_request):
        issues.append(
            "RISK: HIGH - Event location is outside supported West Malaysia service areas."
        )

    quote_values = extract_currency_values(plan.pricing_breakdown)
    if quote_values:
        highest_quote = max(quote_values)
        if highest_quote > plan.total_budget:
            issues.append(
                f"RISK: HIGH - Pricing appears to exceed budget. Highest detected quote RM{highest_quote:.2f}, budget RM{plan.total_budget:.2f}."
            )

    if "CRITICAL SHORTAGE" in plan.menu.upper() and "substitute" not in plan.menu.lower():
        issues.append(
            "RISK: HIGH - Menu references a critical shortage ingredient without clear substitution."
        )

    if not issues:
        return "SYSTEM VALIDATION: No hard-rule violations detected."

    return "\n".join(issues)

def validate_dietary_conflicts(user_request: str, menu: str):
    issues = []

    request = user_request.lower()
    menu_text = menu.lower()
    
    if "dietary needs: none" in request:
        return issues
    
    if "vegetarian" in request or "vegan" in request:
        meat = ["chicken", "beef", "duck", "lamb", "meat"]
        for item in meat:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains {item} despite vegetarian/vegan request."
                )

    if "vegan" in request:
        animal_products = ["milk", "cheese", "butter", "cream", "yogurt", "egg", "chicken", "beef", "fish", "seafood"]
        for item in animal_products:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains animal product '{item}' despite vegan request."
                )

    if "nut allergy" in request:
        nuts = ["peanut", "almond", "cashew", "walnut"]
        for nut in nuts:
            if nut in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains {nut} despite nut allergy request."
                )

    if "dairy-free" in request:
        dairy = ["milk", "cheese", "butter", "cream", "yogurt"]
        for item in dairy:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains dairy item '{item}' despite dairy-free request."
                )

    if "gluten-free" in request:
        gluten = ["bread", "pasta", "wheat", "flour"]
        for item in gluten:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains gluten item '{item}' despite gluten-free request."
                )
                
    if "seafood allergy" in request:
        seafood = [
            "fish", "prawn", "shrimp",
            "crab", "squid", "mussel",
            "salmon", "tuna"
        ]

        for item in seafood:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains seafood item '{item}' despite seafood allergy request."
                )
                
    if "egg-free" in request:
        eggs = ["egg", "mayonnaise", "mayo", "egg noodles"]
        for item in eggs:
            if item in menu_text:
                issues.append(
                    f"RISK: HIGH - Menu contains egg item '{item}' despite egg-free request."
                )
                
    return issues

def load_knowledge_file(filename: str) -> str:
        path = os.path.join("knowledge", filename)

        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return f"{filename} not found."
        
def create_search_client():
    endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    key = os.getenv("AZURE_SEARCH_KEY")
    index = os.getenv("AZURE_SEARCH_INDEX")

    if not endpoint or not key or not index:
        return None

    return SearchClient(
        endpoint=endpoint,
        index_name=index,
        credential=AzureKeyCredential(key),
    )


def search_knowledge(query: str, top: int = 5) -> str:
    client = create_search_client()

    if client is None:
        return "Azure AI Search is not configured yet."

    results = client.search(search_text=query, top=top)

    docs = []
    for result in results:
        docs.append(json.dumps(dict(result), indent=2, default=str))

    return "\n\n".join(docs) if docs else "No matching knowledge found."

def save_feedback(feedback_data):
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = "feedback"

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client(container_name)

    try:
        container_client.create_container()
    except Exception:
        pass

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    plan_id = feedback_data.get("customer_feedback", {}).get("plan_id", timestamp)
    blob_name = f"feedback_{plan_id}.json"
    
    container_client.upload_blob(
        name=blob_name,
        data=json.dumps(feedback_data, indent=2),
        overwrite=True,
    )

    return {
        "message": "Feedback saved",
        "blob": blob_name,
    }
    
def save_plan_to_blob(plan: CateringPlan) -> str:
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER", "plans")

    if not connection_string:
        return "Azure Blob Storage is not configured."

    blob_service = BlobServiceClient.from_connection_string(connection_string)
    container_client = blob_service.get_container_client(container_name)

    try:
        container_client.create_container()
    except Exception:
        pass

    blob_name = f"{plan.plan_id}.json"

    data = json.dumps(plan.model_dump(), indent=2)

    container_client.upload_blob(
        name=blob_name,
        data=data,
        overwrite=True,
    )

    return blob_name

class OllamaAgent:
    def __init__(self, model: str, name: str, instructions: str):
        self.model = model
        self.name = name
        self.instructions = instructions

    async def run(self, message: str):
        prompt = f"""
You are {self.name}.

Instructions:
{self.instructions}

Task:
{message}
"""
        response = await asyncio.to_thread(
            ollama.chat,
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        class Result:
            text = response["message"]["content"]

        return Result()
        
async def generate_catering_plan(user_request: str, progress_callback=None):
    async def send_progress(step: str):
        if progress_callback:
            await progress_callback(step)

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    print("Using Ollama model:", model_name)
    
    supplier_knowledge = load_knowledge_file("supplier_data.txt")
    menu_catalog = load_knowledge_file("menu_catalog.txt")
    inventory_rules = load_knowledge_file("inventory_rules.txt")
    compliance_standards = load_knowledge_file("compliance_standards.txt")
    logistics_rules = load_knowledge_file("logistics_rules.txt")
    risk_rulebook = load_knowledge_file("risk_rulebook.txt")
    feedback_criteria = load_knowledge_file("feedback_criteria.txt")

    # create ALL agents first
    receptionist = OllamaAgent(
        model_name,
        "Receptionist",
        """
        Extract structured event requirements.

        Return:
        - Event type
        - Guest count
        - Budget per head
        - Total budget if possible
        - Dietary needs
        - Theme
        - Event date
        - Location
        - Special notes

        Also flag if the user requests pork, wine, alcohol, non-halal items, or a location outside West Malaysia.
        """
    )
    
    chef = OllamaAgent(
        model_name,
        "Menu_Planning_Agent",
        """
        - Plan a halal-compliant menu STRICTLY within the customer's budget per head.
        - NEVER exceed the budget per head.
        - If requested theme is too expensive, downgrade menu complexity.
        - Prefer affordable ingredients when budget is low.
        - Vegetarian menus should prioritize cost-efficient ingredients.

        IMPORTANT:
        - This business is halal-only.
        - Never include pork, wine, alcohol, or non-halal ingredients.
        - If customer requests wine or alcohol, suggest halal alternatives instead.
        - Avoid ingredients with CRITICAL SHORTAGE.
        - Respect ALL dietary restrictions and allergies.
        - Never include restricted ingredients.
        - Nut allergy -> avoid all nuts and nut sauces.
        - Dairy-free -> avoid cheese, butter, cream, milk.
        - Gluten-free -> avoid bread, pasta, wheat flour.
        - Seafood allergy -> avoid seafood ingredients and sauces.
        - If dietary needs are "None", follow halal-only business rules but do not apply extra allergy restrictions.
        - Suggest safe substitutes when needed.
        """
    )
    
    inventory_manager = OllamaAgent(
        model_name,
        "Inventory_Procurement_Agent",
        """
        Check the proposed menu against supplier availability and inventory rules.

        IMPORTANT:
        - Identify ingredients required.
        - Identify shortages.
        - Avoid ingredients marked CRITICAL SHORTAGE.
        - Suggest substitutions using supplier recommendations.
        - Check supplier lead times.
        - Add buffer quantities based on guest count.
        - Produce a procurement action list.
        """
    )
    
    compliance_officer = OllamaAgent(
        model_name,
        "Compliance_Agent",
        """
        Check Halal and sustainability compliance.

        IMPORTANT:
        - This business provides halal-compliant catering only.
        - Pork, wine, alcohol, non-halal meat, and alcohol-based sauces are NOT supported.
        - If requested, classify the request as RISK: HIGH.
        - Clearly explain WHY the request violates halal policy.
        - Suggest halal alternatives such as mocktails, fruit punch, sparkling juice, or non-alcoholic beverages.
        - Every final proposal must clearly state:
            "This proposal is prepared for halal-compliant catering."
        - Verify allergy compliance.
        - Detect dangerous allergen conflicts.
        - If allergen conflict exists, classify as RISK: HIGH.
        - Explain which ingredient violates dietary restrictions.
        """
    )
    
    logistics_expert = OllamaAgent(
        model_name,
        "Logistics_Planning_Agent",
        """
        Create a detailed operational logistics timeline.

        Return sections:
        - Procurement Timeline
        - Preparation Timeline
        - Staffing Plan
        - Packaging Plan
        - Delivery Timeline
        - Logistics Risks

        IMPORTANT RULES:
        - Catering operations only support West Malaysia.
        - If location is outside West Malaysia, classify as RISK: HIGH.
        - Events above 200 pax require at least 7 days preparation.
        - Same-day bookings are HIGH RISK.
        - Delivery must arrive 2 hours before event.
        - Include supplier lead times.
        - Do NOT ask questions.
        - Do NOT provide generic consulting advice.
        - Produce operational logistics output only.
        """
    )
    
    monitor = OllamaAgent(
        model_name,
        "Monitoring_Agent",
        """
        Audit the full catering plan.

        IMPORTANT CHECKS:
        - Budget violations
        - Supplier shortages
        - Unsupported logistics
        - Non-halal compliance issues
        - Only flag ingredients as non-halal if explicitly stated in provided knowledge.
        - Do not invent halal violations.
        - Do not assume ingredients are non-halal without evidence.
        - Halal-only business rule violations
        - Pork, wine, alcohol, or non-halal menu requests
        - Requests violating halal-only catering policy
        - Unsupported event locations outside West Malaysia
        - Final quote is greater than total budget.

        Start with:
        RISK: LOW
        RISK: MEDIUM
        or
        RISK: HIGH
        
        IMPORTANT:
        If the customer requests wine or alcohol, always classify as RISK: HIGH.
        If the event location is outside West Malaysia, always classify as RISK: HIGH.
        If the final quote is within budget, do NOT say the budget was exceeded.
        Always provide clear explanations for any risks identified.
        """
    )
    
    accountant = OllamaAgent(
        model_name,
        "Pricing_Optimization_Agent",
        """
        Create MYR pricing for the catering plan.

        IMPORTANT:
        - Use guest count and budget per head.
        - Calculate total client budget.
        - Estimate internal cost.
        - Add 15% profit margin.
        - Final quote must NOT exceed total client budget.
        - If cost exceeds budget, revise the proposal to fit the budget.
        - Do not say over budget if final quote <= total budget.
        - NEVER violate dietary requirements.
        - If customer requested vegetarian, do not recommend chicken or meat.
        - Maintain halal compliance and dietary restrictions during optimization.

        OUTPUT FORMAT:

    [FINAL QUOTE]
    RMXXXX

    [COST BREAKDOWN]

    | Item | Price Per Head | Quantity | Total |
    |---|---:|---:|---:|
    | Example Item | RM10 | 100 | RM1000 |

    [BUDGET STATUS]
    - Within Budget / Over Budget

    [OPTIMIZATION NOTES]
    - Explain any substitutions or optimizations used.

    IMPORTANT TABLE RULES:
    - ALWAYS return the cost breakdown as a markdown table.
    - ALWAYS include the table header.
    - Use RM currency formatting.
    - Do NOT skip the table even if pricing is simple.
        """
    )
    
    proposal_review_agent = OllamaAgent(
        model_name,
        "Proposal_Review_Agent",
        """
        Review the catering proposal from a professional corporate client perspective.

        Evaluate:
        - professionalism
        - clarity
        - feasibility
        - value for money
        - menu suitability

        Provide constructive recommendations.
        """
    )
    
    plan = CateringPlan()
    plan.plan_id = datetime.now().strftime("plan_%Y%m%d_%H%M%S")

    await send_progress("Running Receptionist Agent...")
    print("[Receptionist] Extracting requirements...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    plan.guest_count = extract_guest_count(user_request)
    
    budget_match = re.search(r"RM\s*(\d+)", user_request, re.I)
    plan.budget_per_head = float(budget_match.group(1)) if budget_match else 120.0
    plan.total_budget = plan.guest_count * plan.budget_per_head

    await send_progress("Loading knowledge Azure AI Search...")
    print("[Knowledge Azure AI Search] Loading menu, supplier, and rule files...")
    azure_knowledge = search_knowledge(user_request)
    if "not configured" in azure_knowledge.lower():
        # Log the error but provide a clean instruction to the agent
        knowledge_context = "Note: Azure Search unavailable. Use local knowledge only."
    else:
        knowledge_context = azure_knowledge

    knowledge = f"""
    Azure AI Search Results:
    {knowledge_context}

    Local Knowledge Base:
    Supplier data:
    {supplier_knowledge}

    Menu catalog:
    {menu_catalog}

    Inventory rules:
    {inventory_rules}

    Compliance standards:
    {compliance_standards}

    Logistics rules:
    {logistics_rules}

    Risk rulebook:
    {risk_rulebook}

    Feedback criteria:
    {feedback_criteria}
    """
    
    await send_progress("Planning menu...")
    print("[Chef] Planning menu...")
    res = await chef.run(f"""
    Customer request: {plan.event_details}
    Guest count: {plan.guest_count}
    Budget per head: RM{plan.budget_per_head}
    Total budget: RM{plan.total_budget}
    Supplier knowledge: {knowledge}
    Menu catalog: {menu_catalog}
    """)
    plan.menu = res.text

    await send_progress("Checking inventory...")
    print("[Inventory] Checking ingredients and shortages...")
    res = await inventory_manager.run(f"""
    Menu: {plan.menu}
    Supplier knowledge: {knowledge}
    Inventory rules: {inventory_rules}
    """)
    plan.inventory_report = res.text

    await send_progress("Checking compliance...")
    print("[Compliance] Checking Halal and sustainability...")
    res = await compliance_officer.run(f"""
    Menu: {plan.menu}
    Supplier knowledge: {knowledge}
    Compliance standards: {compliance_standards}
    """)
    plan.compliance_report = res.text
    

    await send_progress("Planning logistics...")
    print("[Logistics] Creating execution timeline...")
    res = await logistics_expert.run(f"""
    Original customer request:
    {user_request}

    Extracted event details:
    {plan.event_details}

    Menu:
    {plan.menu}

    Inventory report:
    {plan.inventory_report}

    Supplier knowledge:
    {knowledge}

    Logistics rules:
    {logistics_rules}

    IMPORTANT:
    - Check the event location from the original customer request.
    - If location is London, Sabah, Sarawak, Singapore, or outside West Malaysia, classify logistics as RISK: HIGH.
    - Check event date and guest count.
    - Events above 200 pax require at least 7 days preparation time.
    """)
    plan.logistics_timeline = res.text
    

    await send_progress("Auditing risks...")
    print("[Monitor] Auditing full plan...")
    res = await monitor.run(f"""
    Original customer request:
    {user_request}

    Risk rulebook:
    {risk_rulebook}

    Full catering plan:
    {plan.model_dump_json(indent=2)}

    IMPORTANT:
    - If location is outside West Malaysia, final risk must be RISK: HIGH.
    - If guest count is above 200 and preparation time is under 7 days, final risk must be RISK: HIGH.
    - Do not classify overall risk as LOW if any HIGH risk exists.
    """)
    plan.risk_assessment = res.text

    await send_progress("Optimizing pricing...")
    print("[Pricing] Creating quote...")
    res = await accountant.run(f"""
    Total client budget: RM{plan.total_budget}
    Guest count: {plan.guest_count}
    Budget per head: RM{plan.budget_per_head}

    STRICT RULE:
    Final quote must be <= RM{plan.total_budget}.

    Menu:
    {plan.menu}

    Inventory report:
    {plan.inventory_report}
    """)
    plan.pricing_breakdown = res.text

    await send_progress("Reviewing proposal...")
    print("[Proposal Review] Reviewing final proposal...")
    res = await proposal_review_agent.run(f"""
    Client feedback criteria: {feedback_criteria}
    Final catering plan: {plan.model_dump_json(indent=2)}
    """)
    plan.proposal_review = res.text
    
    plan.system_validation = validate_plan(plan, user_request)

    if "RISK: HIGH" in plan.system_validation:
        plan.risk_assessment = f"{plan.risk_assessment}\n\n{plan.system_validation}"

    await send_progress("Saving plan to Azure Blob...")
    print("[Azure Blob Storage] Saving final plan...")
    blob_name = save_plan_to_blob(plan)
    
    print(f"\n[SAVED TO AZURE BLOB]\n{blob_name}")



    return plan.model_dump()

async def analyze_feedback(feedback_data):

    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")

    feedback_analysis_agent = OllamaAgent(
        model_name,
        "Feedback_Analysis_Agent",
        """
        Analyze real customer feedback.

        Return:
        - Sentiment
        - Key Issues
        - Improvement Suggestions
        """
    )

    res = await feedback_analysis_agent.run(
        json.dumps(feedback_data, indent=2)
    )

    return res.text

if __name__ == "__main__":
    asyncio.run(
        generate_catering_plan(
            "Swinburne Gala Dinner, 100 pax. Budget RM150/head. High-end seafood theme preferred."
        )
    )