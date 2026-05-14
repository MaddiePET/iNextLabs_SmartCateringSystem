from typing import List
from services.supplier_service import get_supplier_status

def calculate_inventory_from_json(menu_json: List[dict], guest_count: int) -> str:
    buffer = 1.10 if guest_count <= 100 else 1.15

    report = "APPROVED MENU:\n"
    for i, item in enumerate(menu_json, 1):
        report += f"{i}. {item['name']}\n"

    report += "\nPROCUREMENT LIST:\n"

    availability_rows = []
    shortage_detected = False
    unknown_detected = False
    counter = 1

    for item in menu_json:
        ingredients = item.get("ingredient_portions", [])
        
        for ingredient in ingredients:
            name = ingredient["name"]
            amount = ingredient["amount"]
            unit = ingredient["unit"]

            total = amount * guest_count * buffer

            if unit == "g":
                qty = f"{total / 1000:.2f} kg"
            elif unit == "ml":
                qty = f"{total / 1000:.2f} L"
            else:
                qty = f"{total:.2f} {unit}"

            report += f"{counter}. {name}: {qty}\n"

            status, supplier, lead = get_supplier_status(name)
            availability_rows.append((name, status, supplier, lead))
            
            if status == "CRITICAL SHORTAGE":
                shortage_detected = True
            elif status in ["UNKNOWN", "LIMITED"]:
                unknown_detected = True
                
            counter += 1

    report += "\nAVAILABILITY:\n"
    for i, row in enumerate(availability_rows, 1):
        name, status, supplier, lead = row
        report += f"{i}. {name}: {status} | Supplier: {supplier} | Lead Time: {lead}\n"

    report += "\nSHORTAGE DETAILS:\n"
    shortages = [row for row in availability_rows if row[1] == "CRITICAL SHORTAGE"]

    if shortages:
        for row in shortages:
            report += f"- {row[0]} shortage detected\n"
    else:
        report += "- None\n"

    if shortage_detected:
        final_status = "SHORTAGE_DETECTED"
    elif unknown_detected:
        final_status = "NO_CONFIRMED_SHORTAGE"
    else:
        final_status = "NO_SHORTAGE"

    report += f"\nFINAL STATUS:\nFINAL_STATUS: {final_status}"

    return report
