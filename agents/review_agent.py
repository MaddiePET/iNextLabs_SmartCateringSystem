REV_PROMPT = """
    Rate the overall proposal quality.

    Review:
    1. Whether the menu matches the selected theme.
    2. Whether the proposal respects dietary requirements.
    3. Whether the plan is operationally clear.
    4. Whether the proposal sounds professional.

    Do NOT invent non-halal issues.
    Do not upgrade dietary classifications.
    If the client requests Vegetarian, do not discuss Vegan unless the client explicitly requested Vegan.
    Do NOT claim tamari, turmeric, ginger, soy, or miso is non-halal unless alcohol or animal-derived ingredients are explicitly stated.

    If religious rules are followed, say: 'All religious dietary restrictions met.'
"""