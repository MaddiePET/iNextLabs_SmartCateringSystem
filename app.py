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
    
async def main():
    model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    print("Using Ollama model:", model_name)
    
    client = ollama.Client()

    receptionist = OllamaAgent(
        model_name,
        name="Receptionist",
        instructions="""
        Extract the customer request into structured details.
        Include event type, guest count, dietary needs, theme, and budget per head.
        Return concise text.
        """,
    )

    chef = OllamaAgent(
        model_name,
        name="Menu_Planning_Agent",
        instructions="""
        You are a catering menu planning agent.
        Use retrieved menu and supplier knowledge.
        Recommend a menu that fits guest count, budget, dietary needs, supplier availability, and event theme.
        Avoid unavailable or shortage ingredients.
        """,
    )

    inventory_manager = OllamaAgent(
        model_name,
        name="Inventory_Procurement_Agent",
        instructions="""
        You are an inventory and procurement agent.
        Compare the menu against supplier availability.
        Identify required ingredients, shortages, substitutions, lead times, and procurement actions.
        """,
    )

    logistics_expert = OllamaAgent(
        model_name,
        name="Logistics_Planning_Agent",
        instructions="""
        You are a logistics planning agent.
        Create preparation, procurement, staffing, packaging, and delivery timelines.
        Flag lead-time conflicts.
        """,
    )

    accountant = OllamaAgent(
        model_name,
        name="Pricing_Optimization_Agent",
        instructions="""
        You are a pricing optimization agent.
        Calculate estimated cost, 15% margin, final quote, and budget fit.
        Use MYR.
        Keep the proposal realistic.
        """,
    )

    monitor = OllamaAgent(
        model_name,
        name="Monitoring_Agent",
        instructions="""
        You are a risk monitoring agent.
        Audit the full catering plan for inconsistencies.
        If there is a serious issue, start your answer with 'RISK: HIGH'.
        Otherwise start with 'RISK: LOW' or 'RISK: MEDIUM'.
        """,
    )

    compliance_officer = OllamaAgent(
        model_name,
        name="Compliance_Agent",
        instructions="""
        You are a Halal and sustainability compliance agent.
        Check Halal suitability and eco-friendly packaging.
        Suggest improvements.
        """,
    )

    feedback_specialist = OllamaAgent(
        model_name,
        name="Feedback_Agent",
        instructions="""
        Review the final catering proposal from a corporate client perspective.
        Comment on clarity, feasibility, value, and professionalism.
        """,
    )

    plan = CateringPlan()

    user_request = (
        "Swinburne Gala Dinner, 100 pax. "
        "Budget RM150/head. High-end seafood theme preferred."
    )

    print(f"Initial Request: {user_request}\n")

    print("[Receptionist] Extracting requirements...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text

    plan.guest_count = extract_number(user_request)
    budget_match = re.search(r"RM\s*(\d+)", user_request, re.I)
    plan.budget_per_head = float(budget_match.group(1)) if budget_match else 120.0
    plan.total_budget = plan.guest_count * plan.budget_per_head

    print(
        f"Setup: {plan.guest_count} guests | "
        f"RM{plan.budget_per_head:.2f}/head | "
        f"Total RM{plan.total_budget:.2f}\n"
    )

    print("[Azure AI Search] Retrieving menu and supplier knowledge...")
    knowledge = search_knowledge(
        f"{plan.event_details} seafood halal suppliers Malaysia shortages packaging"
    )

    print("[Chef] Planning menu...")
    res = await chef.run(
        f"""
        Customer request:
        {plan.event_details}

        Guest count: {plan.guest_count}
        Budget per head: RM{plan.budget_per_head}
        Total budget: RM{plan.total_budget}

        Retrieved Azure AI Search knowledge:
        {knowledge}
        """
    )
    plan.menu = res.text

    print("[Inventory] Checking ingredients and shortages...")
    res = await inventory_manager.run(
        f"""
        Menu:
        {plan.menu}

        Supplier and menu knowledge:
        {knowledge}

        Produce a procurement and shortage report.
        """
    )
    plan.inventory_report = res.text

    print("[Compliance] Checking Halal and sustainability...")
    res = await compliance_officer.run(
        f"""
        Menu:
        {plan.menu}

        Supplier knowledge:
        {knowledge}
        """
    )
    plan.compliance_report = res.text

    print("[Logistics] Creating execution timeline...")
    res = await logistics_expert.run(
        f"""
        Event:
        {plan.event_details}

        Menu:
        {plan.menu}

        Inventory report:
        {plan.inventory_report}

        Supplier knowledge:
        {knowledge}
        """
    )
    plan.logistics_timeline = res.text

    print("[Monitor] Auditing full plan...")
    res = await monitor.run(
        f"""
        Audit this catering plan:

        {plan.model_dump_json(indent=2)}
        """
    )
    plan.risk_assessment = res.text

    max_retries = 2
    retry_count = 0

    while "RISK: HIGH" in plan.risk_assessment.upper() and retry_count < max_retries:
        print(f"[System] High risk detected. Revision attempt {retry_count + 1}...")

        res = await chef.run(
            f"""
            The monitoring agent flagged this risk:
            {plan.risk_assessment}

            Revise the menu to reduce risk.

            Original supplier knowledge:
            {knowledge}
            """
        )
        plan.menu = res.text

        res = await inventory_manager.run(
            f"""
            Re-check the revised menu:
            {plan.menu}

            Supplier knowledge:
            {knowledge}
            """
        )
        plan.inventory_report = res.text

        res = await monitor.run(
            f"""
            Re-audit this revised catering plan:

            {plan.model_dump_json(indent=2)}
            """
        )
        plan.risk_assessment = res.text

        retry_count += 1

    print("[Pricing] Creating quote...")
    res = await accountant.run(
        f"""
        Total budget: RM{plan.total_budget}
        Guest count: {plan.guest_count}
        Budget per head: RM{plan.budget_per_head}

        Menu:
        {plan.menu}

        Inventory report:
        {plan.inventory_report}

        Create a final pricing breakdown with 15% margin.
        """
    )
    plan.pricing_breakdown = res.text

    print("[Feedback] Reviewing final proposal...")
    res = await feedback_specialist.run(
        f"""
        Review this final catering plan:

        {plan.model_dump_json(indent=2)}
        """
    )
    plan.client_feedback = res.text

    print("[Azure Blob Storage] Saving final plan...")
    blob_name = save_plan_to_blob(plan)

    print("\n" + "=" * 60)
    print("COORDINATED CATERING PLAN")
    print("=" * 60)

    print(f"\n[MENU DESIGN]\n{plan.menu}")
    print(f"\n[INVENTORY & PROCUREMENT]\n{plan.inventory_report}")
    print(f"\n[COMPLIANCE]\n{plan.compliance_report}")
    print(f"\n[LOGISTICS]\n{plan.logistics_timeline}")
    print(f"\n[RISK AUDIT]\n{plan.risk_assessment}")
    print(f"\n[FINAL QUOTE]\n{plan.pricing_breakdown}")
    print(f"\n[CLIENT FEEDBACK]\n{plan.client_feedback}")
    print(f"\n[SAVED TO AZURE BLOB]\n{blob_name}")


if __name__ == "__main__":
    asyncio.run(main())