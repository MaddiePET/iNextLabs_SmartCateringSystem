LOG_PROMPT = """
    Create an operational timeline. Do NOT calculate exact calendar dates. Structure your response strictly using these headers:
    [PHASE 1: PROCUREMENT] (Lead time for ingredients and eco-packaging)
    [PHASE 2: PREPARATION] (Kitchen prep and Halal-certified cleaning)
    [PHASE 3: EXECUTION] (Day of event, delivery 2 hours before start)
    Only mention alcohol handling if the client explicitly requested alcohol or licensed bar service.
    Do not assume sauces contain alcohol unless explicitly stated.
"""