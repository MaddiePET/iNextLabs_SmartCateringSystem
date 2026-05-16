import asyncio
import os
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from agents.chef_agent import CHEF_PROMPT
from agents.inventory_agent import INV_PROMPT
from agents.review_agent import REV_PROMPT
from agents.pricing_agent import PRICING_PROMPT
from agents.compliance_agent import COMP_PROMPT
from agents.logistics_agent import LOG_PROMPT
from agents.monitor_agent import MON_PROMPT
from models.catering_plan import CateringPlan

from services.menu_service import (
    build_menu_json,
    format_menu_text,
)

from services.inventory_service import (
    calculate_inventory_from_json,
)

from services.pricing_service import (
    calculate_pricing_from_json,
)

from services.validation_service import (
    validate_plan,
)

from services.azure_service import (
    search_knowledge,
    save_plan_to_blob,
)

from utils.helpers import (
    extract_budget_per_head,
    extract_guest_count,
    is_supported_west_malaysia_location,
)

load_dotenv()

def load_knowledge_file(filename: str) -> str:
    path = os.path.join("knowledge", filename)
    try:
        with open(path, "r", encoding="utf-8") as file: return file.read()
    except FileNotFoundError: return f"{filename} not found."

class AutoGenAgent:
    def __init__(self, model_client, name: str, instructions: str):
        self.agent = AssistantAgent(
            name=name,
            model_client=model_client,
            system_message=instructions,
        )

    async def run(self, message: str):
        response = await self.agent.run(task=message)

        class Result:
            text = response.messages[-1].content

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

    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=os.getenv("FOUNDRY_DEPLOYMENT"),
        model=os.getenv("FOUNDRY_MODEL"),
        azure_endpoint=os.getenv("FOUNDRY_ENDPOINT"),
        api_key=os.getenv("FOUNDRY_API_KEY"),
        api_version="2024-10-21",
)
    
    # -- 1. INITIALIZE THE PLAN OBJECT ---
    plan = CateringPlan()
    plan.plan_id = datetime.now().strftime("catering_plan_%Y%m%d_%H%M%S")
    plan.guest_count = extract_guest_count(user_request)
    plan.budget_per_head = extract_budget_per_head(user_request)
    plan.total_budget = plan.guest_count * plan.budget_per_head
    
    print(f"\nStarting Catering Workflow for: {user_request[:500]}...")
    
    # --- 2. INITIALIZE AGENTS ---    
    receptionist = AutoGenAgent(model_client, "Receptionist", "Extract event details: Type, Count, Budget, Theme, Diet.")
    chef = AutoGenAgent(model_client, "Chef", CHEF_PROMPT)
    inv_agent = AutoGenAgent(model_client, "Inventory_Agent", INV_PROMPT)
    comp_agent = AutoGenAgent(model_client, "Compliance_Agent", COMP_PROMPT)
    log_agent = AutoGenAgent(model_client, "Logistics_Agent", LOG_PROMPT)
    pricing_agent = AutoGenAgent(model_client, "Pricing_Agent", PRICING_PROMPT)
    mon_agent = AutoGenAgent(model_client, "Monitor_Agent", MON_PROMPT)
    rev_agent = AutoGenAgent(model_client, "Review_Agent", REV_PROMPT)
    
    # --- 3. START WORKFLOW ---
    # 3.1. Receptionist
    await send_progress("Running Receptionist Agent...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    # 3.2. Search and Temp Menu
    await asyncio.sleep(0.3)  
    themes = ["Japanese Fusion", "Traditional Malay", "Western Corporate", "Chinese Fusion", "International Buffet"]
    selected_theme = next((t for t in themes if t.lower() in user_request.lower()), "International Buffet")
    knowledge = search_knowledge(f"{selected_theme} {user_request}")

    # 3.3. Chef
    await send_progress(f"Planning menu...")
    menu_json = build_menu_json(selected_theme, user_request)
    current_menu = format_menu_text(menu_json)
    plan.menu = current_menu
    plan.structured_menu = menu_json
    workflow_context = {
        "theme": selected_theme,
        "guest_count": plan.guest_count,
        "budget_per_head": plan.budget_per_head,
        "dietary_request": user_request,
        "location_supported": is_supported_west_malaysia_location(user_request),
        "inventory_status": "PENDING",
        "compliance_status": "PENDING",
    }
        
    # 3.4. Inventory
    await send_progress("Checking inventory...")
    plan.inventory_report = calculate_inventory_from_json(
        menu_json=plan.structured_menu,
        guest_count=plan.guest_count
    )
    inventory_review = await inv_agent.run(
        f"""
    You are the Inventory & Procurement Agent.

    The system has already calculated the procurement quantities deterministically.

    Your task:
    1. Review the JSON menu and inventory report.
    2. Do NOT change quantities.
    3. Do NOT add new menu items.
    4. Confirm whether the procurement list is operationally clear.
    5. Mention supplier risks only if shown in the report.

    JSON MENU:
    {json.dumps(plan.structured_menu, indent=2)}

    INVENTORY REPORT:
    {plan.inventory_report}

    Return a short procurement review only.
    """
    )

    plan.inventory_report += "\n\nINVENTORY AGENT REVIEW:\n" + inventory_review.text
    
    # Only trigger revision if a REAL shortage exists
    if re.search(r"FINAL_STATUS:\s*SHORTAGE_DETECTED", plan.inventory_report, re.I):
        await send_progress("Revising menu based on inventory review...")
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
        await send_progress("Inventory validation completed...")
    
    workflow_context["inventory_status"] = (
        "SHORTAGE_DETECTED"
        if "SHORTAGE_DETECTED" in plan.inventory_report
        else "NO_SHORTAGE_OR_UNKNOWN"
    )

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
    if "HIGH RISK" in plan.compliance_report.upper():
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
        plan.menu = res.text
    else:
        await send_progress("Compliance validation completed...")
        plan.menu = current_menu
        
    # Do NOT rebuild JSON from text
    plan.structured_menu = menu_json
    # Recalculate inventory using JSON source
    base_inventory_report = calculate_inventory_from_json(
        menu_json=plan.structured_menu,
        guest_count=plan.guest_count
    )

    plan.inventory_report = base_inventory_report + "\n\nINVENTORY AGENT REVIEW:\n" + inventory_review.text
    
    workflow_context["compliance_status"] = (
        "HIGH_RISK"
        if "HIGH RISK" in plan.compliance_report.upper()
        else "LOW_RISK"
    )
    
    # 3.6. Logistics
    await send_progress("Planning logistics...")
    today = datetime.now().strftime("%Y-%m-%d")
    res = await log_agent.run(
        f"Shared Workflow Context:\n{json.dumps(workflow_context, indent=2)}\n\n"
        f"Today is {today}. Client Request: {user_request}\nMenu: {plan.menu}"
    )
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
    pricing_table = calculate_pricing_from_json(
        menu_json=plan.structured_menu,
        guest_count=plan.guest_count,
        budget_per_head=plan.budget_per_head,
        selected_theme=selected_theme,
        user_request=user_request,
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

    # 3.9. Validation and Review
    plan.system_validation = validate_plan(plan, user_request)
    plan.risk_assessment += "\n\nEXECUTION MONITORING:\n"

    plan.risk_assessment += "- Customer Intake: COMPLETED\n"
    plan.risk_assessment += "- Menu Planning: COMPLETED\n"

    if "FINAL_STATUS: SHORTAGE_DETECTED" in plan.inventory_report:
        plan.risk_assessment += "- Inventory Check: HIGH_RISK - Confirmed shortage detected.\n"
    elif "LIMITED" in plan.inventory_report:
        plan.risk_assessment += "- Inventory Check: WARNING - Limited supplier availability detected.\n"
    else:
        plan.risk_assessment += "- Inventory Check: PASSED - No confirmed shortages.\n"

    if "HIGH RISK" in plan.compliance_report.upper():
        plan.risk_assessment += "- Compliance: HIGH_RISK - Compliance issue detected.\n"
    else:
        plan.risk_assessment += "- Compliance: PASSED - No hard dietary violation.\n"

    if "exceeds client budget" in plan.system_validation.lower():
        plan.risk_assessment += "- Pricing: HIGH_RISK - Quote exceeds client budget.\n"
    else:
        plan.risk_assessment += "- Pricing: PASSED - Quote is within budget.\n"

    plan.risk_assessment += "- Logistics: READY - Timeline generated.\n"
    await send_progress("Reviewing proposal...")
    res = await rev_agent.run(
        f"""
    Client Request:
    {user_request}

    Menu:
    {plan.menu}

    Compliance Report:
    {plan.compliance_report}

    Final System Validation:
    {plan.system_validation}
    """
    )
    plan.proposal_review = res.text

    # --- 4. SAVE ---
    await send_progress("Saving plan to Azure Blob...")
    save_plan_to_blob(plan)
    print("\nWORKFLOW COMPLETE\n")
    return plan.model_dump()


def generate_monitoring_status(
    inventory_result,
    final_quote,
    budget_per_head,
    shortages,
    unknown_items,
    compliance_risk
):
    monitoring_status = {
        "customer_intake": "COMPLETED",
        "menu_planning": "COMPLETED",
        "inventory_check": "COMPLETED",
        "pricing": "COMPLETED",
        "logistics": "READY",
        "compliance": "PASSED",
    }

    # Inventory warnings
    if shortages > 0 or unknown_items > 0:
        monitoring_status["inventory_check"] = "HIGH_RISK"

    elif inventory_result.get("limited_items", 0) > 0:
        monitoring_status["inventory_check"] = "WARNING"

    # Pricing warnings
    if final_quote > budget_per_head:
        monitoring_status["pricing"] = "HIGH_RISK"

    # Compliance warnings
    if compliance_risk.upper() != "LOW":
        monitoring_status["compliance"] = "WARNING"

    return monitoring_status

async def analyze_feedback(feedback_data):
    model_client = AzureOpenAIChatCompletionClient(
        azure_deployment=os.getenv("FOUNDRY_DEPLOYMENT"),
        model=os.getenv("FOUNDRY_MODEL"),
        azure_endpoint=os.getenv("FOUNDRY_ENDPOINT"),
        api_key=os.getenv("FOUNDRY_API_KEY"),
        api_version="2024-10-21",
    )

    feedback_agent = AutoGenAgent(
        model_client,
        "Feedback_Agent",
        "Analyze feedback sentiment."
    )

    res = await feedback_agent.run(json.dumps(feedback_data))
    return res.text