import asyncio
from fileinput import filename
import os
import re
import json
from datetime import datetime
from typing import List

from agent_framework import step
from dotenv import load_dotenv
from pydantic import BaseModel

import ollama

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient

load_dotenv()


class CateringPlan(BaseModel):
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
    client_feedback: str = ""


def extract_number(text: str) -> int:
    nums = re.findall(r"\d+", text or "")
    return int(nums[0]) if nums else 0


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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    blob_name = f"catering_plan_{timestamp}.json"

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
    receptionist = OllamaAgent(model_name, "Receptionist", "Extract event type, guest count, dietary needs, theme, and budget per head.")
    chef = OllamaAgent(model_name, "Menu_Planning_Agent", "Plan a menu within budget using supplier knowledge.")
    inventory_manager = OllamaAgent(model_name, "Inventory_Procurement_Agent", "Check menu against supplier availability and identify shortages.")
    compliance_officer = OllamaAgent(model_name, "Compliance_Agent", "Check Halal and sustainability compliance.")
    logistics_expert = OllamaAgent(model_name, "Logistics_Planning_Agent", "Create preparation, procurement, staffing, packaging, and delivery timeline.")
    monitor = OllamaAgent(model_name, "Monitoring_Agent", "Audit the full catering plan. Start with RISK: LOW, MEDIUM, or HIGH.")
    accountant = OllamaAgent(model_name, "Pricing_Optimization_Agent", "Create MYR pricing. Final quote must not exceed total budget.")
    feedback_specialist = OllamaAgent(model_name, "Feedback_Agent", "Review proposal from corporate client perspective.")

    plan = CateringPlan()

    await send_progress("Running Receptionist Agent...")
    print("[Receptionist] Extracting requirements...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    plan.guest_count = extract_number(user_request)
    
    def load_knowledge_file(filename: str) -> str:
        path = os.path.join("knowledge", filename)

        try:
            with open(path, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return f"{filename} not found."
    
    budget_match = re.search(r"RM\s*(\d+)", user_request, re.I)
    plan.budget_per_head = float(budget_match.group(1)) if budget_match else 120.0
    plan.total_budget = plan.guest_count * plan.budget_per_head

    await send_progress("Loading local knowledge base...")
    print("[Knowledge Base] Loading local menu, supplier, and rule files...")
    knowledge = f"""
    Supplier data:{supplier_knowledge}
    Menu catalog:{menu_catalog}
    Inventory rules:{inventory_rules}
    Compliance standards:{compliance_standards}
    Logistics rules:{logistics_rules}
    Risk rulebook:{risk_rulebook}
    Feedback criteria:{feedback_criteria}
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
    Event: {plan.event_details}
    Menu: {plan.menu}
    Inventory report: {plan.inventory_report}
    Supplier knowledge: {knowledge}
    Logistics rules: {logistics_rules}
    """)
    plan.logistics_timeline = res.text

    await send_progress("Auditing risks...")
    print("[Monitor] Auditing full plan...")
    res = await monitor.run(f"""
    Risk rulebook: {risk_rulebook}
    Full catering plan: {plan.model_dump_json(indent=2)}
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

    await send_progress("Reviewing client feedback...")
    print("[Feedback] Reviewing final proposal...")
    res = await feedback_specialist.run(f"""
    Client feedback criteria: {feedback_criteria}
    Final catering plan: {plan.model_dump_json(indent=2)}
    """)
    plan.client_feedback = res.text

    await send_progress("Saving to Azure Blob...")
    print("[Azure Blob Storage] Saving final plan...")
    blob_name = save_plan_to_blob(plan)

    print(f"\n[SAVED TO AZURE BLOB]\n{blob_name}")

    return plan.model_dump()

if __name__ == "__main__":
    asyncio.run(
        generate_catering_plan(
            "Swinburne Gala Dinner, 100 pax. Budget RM150/head. High-end seafood theme preferred."
        )
    )