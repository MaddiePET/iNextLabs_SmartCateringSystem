COMP_PROMPT = """
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
    - If eco-friendly packaging is requested by the client and addressed elsewhere operationally, mark as ADDRESSED.
"""