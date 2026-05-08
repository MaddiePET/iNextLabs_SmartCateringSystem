import asyncio
import os
import re
import json
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from pydantic import BaseModel
from google import genai

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


class GeminiAgent:
    def __init__(self, client, model: str, name: str, instructions: str):
        self.client = client
        self.model = model
        self.name = name
        self.instructions = instructions

    async def run(self, message: str):
        prompt = f"""
You are {self.name}.

Instructions:
{self.instructions}

User/task:
{message}
"""
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=prompt,
        )

        class Result:
            text = response.text

        return Result()


def extract_number(text: str) -> int:
    nums = re.findall(r"\d+", text or "")
    return int(nums[0]) if nums else 0


def get_local_supplier_data() -> str:
    try:
        with open("supplier_data.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "No supplier data available."


def save_plan_locally(plan: CateringPlan) -> str:
    os.makedirs("outputs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"outputs/catering_plan_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, indent=2)

    return filename


async def main():
    gemini_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not gemini_key:
        raise ValueError("Missing GEMINI_API_KEY in your .env file.")

    client = genai.Client(api_key=gemini_key)

    supplier_knowledge = get_local_supplier_data()

    receptionist = GeminiAgent(
        client,
        model_name,
        "Receptionist Agent",
        """
Extract event type, guest count, dietary needs, theme, and budget per head.
Return concise structured text.
""",
    )

    chef = GeminiAgent(
        client,
        model_name,
        "Menu Planning Agent",
        """
Plan a catering menu within budget.
Use supplier knowledge.
Avoid shortage ingredients.
Suggest suitable substitutions.
""",
    )

    inventory_manager = GeminiAgent(
        client,
        model_name,
        "Inventory and Procurement Agent",
        """
Check the menu against supplier availability.
Identify required ingredients, shortages, substitutions, and procurement actions.
""",
    )

    logistics_expert = GeminiAgent(
        client,
        model_name,
        "Logistics Planning Agent",
        """
Create preparation, procurement, staffing, packaging, and delivery timeline.
Flag lead-time conflicts.
""",
    )

    accountant = GeminiAgent(
        client,
        model_name,
        "Pricing Optimization Agent",
        """
Calculate estimated cost, 15% profit margin, final quote, and budget fit.
Use Malaysian Ringgit.
""",
    )

    monitor = GeminiAgent(
        client,
        model_name,
        "Monitoring Agent",
        """
Audit the full catering plan for inconsistency or risk.
If serious, start with 'RISK: HIGH'.
Otherwise start with 'RISK: LOW' or 'RISK: MEDIUM'.
""",
    )

    compliance_officer = GeminiAgent(
        client,
        model_name,
        "Compliance Agent",
        """
Check Halal suitability and sustainability.
Suggest eco-friendly packaging improvements.
""",
    )

    feedback_specialist = GeminiAgent(
        client,
        model_name,
        "Feedback Agent",
        """
Review the final proposal from a corporate client perspective.
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

    print("[Knowledge Base] Using local supplier data...")
    knowledge = supplier_knowledge

    print("[Chef] Planning menu...")
    res = await chef.run(
        f"""
Customer request:
{plan.event_details}

Guest count: {plan.guest_count}
Budget per head: RM{plan.budget_per_head}
Total budget: RM{plan.total_budget}

Supplier knowledge:
{knowledge}
"""
    )
    plan.menu = res.text

    print("[Inventory] Checking shortages...")
    res = await inventory_manager.run(
        f"""
Menu:
{plan.menu}

Supplier knowledge:
{knowledge}
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

    print("[Logistics] Planning timeline...")
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

    print("[Monitor] Auditing plan...")
    res = await monitor.run(plan.model_dump_json(indent=2))
    plan.risk_assessment = res.text

    retry_count = 0
    max_retries = 2

    while "RISK: HIGH" in plan.risk_assessment.upper() and retry_count < max_retries:
        print(f"[System] High risk detected. Revision attempt {retry_count + 1}...")

        res = await chef.run(
            f"""
The Monitoring Agent found this risk:
{plan.risk_assessment}

Revise the menu to reduce risk.

Supplier knowledge:
{knowledge}
"""
        )
        plan.menu = res.text

        res = await inventory_manager.run(
            f"""
Re-check this revised menu:
{plan.menu}

Supplier knowledge:
{knowledge}
"""
        )
        plan.inventory_report = res.text

        res = await monitor.run(plan.model_dump_json(indent=2))
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
"""
    )
    plan.pricing_breakdown = res.text

    print("[Feedback] Reviewing proposal...")
    res = await feedback_specialist.run(plan.model_dump_json(indent=2))
    plan.client_feedback = res.text

    saved_file = save_plan_locally(plan)

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
    print(f"\n[SAVED LOCALLY]\n{saved_file}")


if __name__ == "__main__":
    asyncio.run(main())