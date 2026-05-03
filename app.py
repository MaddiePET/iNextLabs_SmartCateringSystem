import asyncio
import os
import re
from typing import List, Dict
from pydantic import BaseModel
from agent_framework.openai import AzureOpenAIChatClient
from agent_framework import Agent

# --- 1. SHARED MEMORY & STRUCTURED DATA ---
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

# --- 2. KNOWLEDGE BASE INTEGRATION ---
def get_external_knowledge():
    try:
        with open("supplier_data.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "No supplier data available."

# --- 3. CONFIGURATION ---
AZURE_ENDPOINT = "https://cwb-catering-ai-mpet.openai.azure.com/"
AZURE_KEY = os.getenv("AZURE_KEY", "")
DEPLOYMENT_NAME = "gpt-4o"

# Helper to extract numbers from AI text strings
def extract_number(text: str) -> int:
    nums = re.findall(r'\d+', text)
    return int(nums[0]) if nums else 0

async def main():
    client = AzureOpenAIChatClient(endpoint=AZURE_ENDPOINT, api_key=AZURE_KEY, deployment_name=DEPLOYMENT_NAME)

    # --- 4. THE AGENT DEFINITIONS ---
    
    receptionist = client.as_agent(
        name="Receptionist", 
        instructions="Extract: Event type, guest count, dietary needs, and budget per head. Return only the extracted values."
    )
    
    chef = client.as_agent(
        name="Chef", 
        instructions=f"Plan a menu within the budget. Reference these suppliers if possible: {SUPPLIER_KNOWLEDGE}"
    )
    
    # Requirement: Demonstrate agent-to-agent communication
    external_data = await get_external_knowledge()  # Simulating an external API call for supplier data
    inventory_manager = client.as_agent(
        name="Inventory_Agent", 
        instructions="Analyze the menu using this supplier data to identify potential shortages: " + external_data
    )
    
    logistics_expert = client.as_agent(
        name="Logistics_Expert", 
        instructions="Plan prep and delivery timelines. Flag if supplier lead times conflict with the event date."
    )
    
    accountant = client.as_agent(
        name="Accountant", 
        instructions="Finalize MYR quote. Maintain a 15% margin while staying under the user's Total Budget."
    )

    monitor = client.as_agent(
        name="Monitoring_Agent", 
        instructions="Red Team. Challenge the other agents. If the Chef chose prawns during a shortage, flag it as a risk."
    )
    
    compliance_officer = client.as_agent(
        name="Compliance_Agent", 
        instructions="Sustainability & Halal Agent. Ensure Halal standards and suggest eco-friendly packaging."
    )

    feedback_specialist = client.as_agent(
        name="Feedback_Agent", 
        instructions="Pitch Quality Agent. Review the final proposal from the perspective of a picky corporate client."
    )

    # --- 5. THE END-TO-END WORKFLOW SIMULATION ---
    
    plan = CateringPlan()
    user_request = "Swinburne Gala Dinner, 100 pax. Budget RM150/head. High-end seafood theme preferred."

    print(f"🚀 Initial Request: {user_request}\n")

    # Step 1: Intake
    print("📞 [Receptionist]...")
    res = await receptionist.run(user_request)
    plan.event_details = res.text
    # Dynamically setting values based on extraction
    plan.guest_count = extract_number(re.search(r'guest|pax|people.*?\d+', res.text, re.I).group() if re.search(r'pax|\d+', res.text) else "80")
    plan.budget_per_head = float(extract_number(re.search(r'budget|RM|head.*?\d+', res.text, re.I).group() if re.search(r'RM|\d+', res.text) else "120"))
    plan.total_budget = plan.guest_count * plan.budget_per_head
    
    print(f"✅ Setup: {plan.guest_count} guests | RM{plan.budget_per_head} per head | Total: RM{plan.total_budget}\n")

    # Step 2: Menu Planning 
    print("🍳 [Chef] Planning menu...")
    res = await chef.run(f"Plan for {plan.guest_count} pax at RM{plan.budget_per_head}/head. Event: {plan.event_details}")
    plan.menu = res.text

    # Step 3: Inventory & Shortage Analysis
    print("📦 [Inventory] Checking supplier status...")
    res = await inventory_manager.run(f"Check this menu against shortages: {plan.menu}. Supplier Data: {SUPPLIER_KNOWLEDGE}")
    plan.inventory_report = res.text

    # Step 4: Compliance Check (Sustainability & Halal) 
    print("🌱 [Compliance] Reviewing standards...")
    res = await compliance_officer.run(f"Review this menu for Halal and Sustainability: {plan.menu}")
    plan.compliance_report = res.text
    
    # Step 5: Logistics Planning (Agent-to-Agent Communication)
    print("🚚 [Logistics] Planning timeline...")
    res = await logistics_expert.run(f"Create timeline for: {plan.menu} with 48hr Cameron Highlands lead time.")
    plan.logistics_timeline = res.text

    # Step 6: Monitoring (Consistency across decisions)
    print("🔍 [Monitor] Auditing agent decisions...")
    # Passing SHARED MEMORY (the whole plan) to the monitor
    res = await monitor.run(f"Audit this plan for inconsistencies: {plan.json()}")
    plan.risk_assessment = res.text

    # THE CORRECTION LOOP
    max_retries = 2
    retry_count = 0
    
    while "RISK: HIGH" in plan.risk_assessment and retry_count < max_retries:
        print(f"🔄 [System] High Risk detected (Attempt {retry_count + 1}). Sending back to Chef...")
        
        # Chef receives the specific risk report to fix the menu
        res = await chef.run(f"CRITICAL: The Monitoring Agent flagged a high risk. Please revise the menu to solve this: {plan.risk_assessment}")
        plan.menu = res.text
        
        # Re-run the inventory and monitoring to see if it's fixed
        print("📦 [Inventory] Re-checking inventory for revised menu...")
        res = await inventory_manager.run(f"Re-analyze shortages for the NEW menu: {plan.menu}")
        plan.inventory_report = res.text
        
        print("🔍 [Monitor] Re-auditing revised plan...")
        res = await monitor.run(f"Audit this NEW plan: {plan.json()}")
        plan.risk_assessment = res.text
        
        retry_count += 1

    if "RISK: HIGH" in plan.risk_assessment:
        print("⚠️ [System] Warning: Could not resolve high risks after retries.")
    else:
        print("✅ [System] Risks resolved or acceptable.")

    # Step 7: Pricing
    print("💰 [Accountant] Generating final quote...")
    res = await accountant.run(f"Total budget is RM{plan.total_budget}. Create quote for: {plan.menu}")
    plan.pricing_breakdown = res.text
    
    # Step 8: Final Feedback
    print("🎭 [Feedback] Generating client perspective...")
    res = await feedback_specialist.run(f"Review this final proposal: {plan.dict()}")
    plan.client_feedback = res.text

    # --- 6. ACTIONABLE OUTPUT ---
    print("\n" + "═"*50)
    print("🏆 COORDINATED CATERING PLAN")
    print("═"*50)
    print(f"\n[MENU DESIGN]\n{plan.menu[:200]}...")
    print(f"\n[INVENTORY & SHORTAGES]\n{plan.inventory_report[:200]}...")
    print(f"\n[RISK AUDIT]\n{plan.risk_assessment[:200]}...")
    print(f"\n[FINAL QUOTE]\n{plan.pricing_breakdown}")
    print(f"\n[CLIENT FEEDBACK]\n{plan.client_feedback}")

if __name__ == "__main__":
    asyncio.run(main())