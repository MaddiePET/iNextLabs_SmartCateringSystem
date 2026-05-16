COMP_PROMPT = """
    Verify only the actual menu text provided.

    State: 'Food is evaluated under halal-certified, pork-free, and lard-free food standards. Licensed bar service is permitted only as a separately managed add-on.'

    Rules:
    - Food items must not contain pork, lard, ham, bacon, pepperoni, prosciutto, or alcohol-based cooking ingredients.
    - Alcohol is permitted only as separate licensed bar service.
    - Alcohol must not be used in food preparation, sauces, desserts, marinades, or cooking.
    - Do NOT invent ingredients that are not written in the menu.
    - Do NOT assume hidden pork, lard, alcohol, meat, fish, or allergens unless the exact ingredient appears in the menu.
    - Only evaluate restrictions explicitly requested by the client.
    - If alcohol or licensed bar service is requested, state that food remains compliant only if alcohol handling, storage, transport, and serving are separated from food operations.
    - If the menu does not explicitly contain a forbidden item, say LOW RISK.
    - Do not imply absolute certainty unless all sourcing and separation conditions are explicitly confirmed.
    - Keep the report short and evidence-based.
"""