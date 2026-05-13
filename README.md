# iNextLabs Smart Catering Operations Planner (Microsoft Agent Framework)

A hybrid AI and deterministic multi-agent system for intelligent catering workflow automation. The system helps catering teams generate structured catering plans by coordinating specialized AI agents for customer intake, menu planning, inventory, compliance, logistics, pricing, risk validation, proposal review, and customer feedback analysis.


## Problem Statement Summary

Catering businesses often manage customer requirements, menu planning, inventory, procurement, logistics, pricing, and risk checks manually. This can lead to poor demand estimation, supplier issues, inconsistent pricing, and communication gaps.

This project solves the problem by using a multi-agent AI workflow that simulates a digital catering operations team.


## Solution Overview

The system allows a customer to submit catering requirements through a Next.js frontend interface. Requests are processed by a FastAPI backend where a Microsoft Agent Framework workflow orchestrates multiple Ollama-powered AI agents.

The system combines:
- Microsoft Agent Framework workflow orchestration
- AutoGen Assistant Agents for specialized AI behaviors
- Ollama local LLM inference
- Deterministic Python-based pricing and validation
- Azure AI Search knowledge retrieval
- Azure Blob Storage persistence
- Real-time Server-Sent Event (SSE) workflow updates

Unlike purely generative AI systems, this platform separates:
- AI responsibilities (recommendation, proposal generation, optimization)
- deterministic backend logic (pricing, validation, dietary checks, operational constraints)

This hybrid architecture improves reliability, prevents hallucinated pricing, and enforces business rules consistently.


## Tech Stack

- Next.js
- TypeScript
- Tailwind CSS
- FastAPI
- Python
- Ollama
- Microsoft Agent Framework
- Azure AI Search
- Azure Blob Storage
- Server-Sent Events (SSE)
- GitHub


## Features

- Multi-agent catering workflow orchestration
- AI-powered menu planning
- Real-time workflow streaming
- Deterministic pricing engine
- Business rule validation
- Dietary and halal compliance checks
- Logistics and procurement planning
- Azure AI Search knowledge retrieval
- Azure Blob Storage persistence
- Customer feedback analysis


## AI Agents

### 1. Receptionist Agent
Captures customer event requirements and extracts structured operational details.

### 2. Menu Planning Agent
Generates theme-aware catering menus while respecting dietary restrictions and halal requirements.

### 3. Inventory & Procurement Agent
Calculates procurement quantities, checks supplier availability, and estimates ingredient requirements.

### 4. Compliance Agent
Validates halal compliance, dietary compatibility, and operational catering rules.

### 5. Logistics Planning Agent
Generates operational preparation workflows, transport coordination, and execution timelines.

### 6. Monitoring Agent
Audits operational risks, dietary conflicts, and business rule violations.

### 7. Pricing & Optimization Agent
Explains pricing strategies and evaluates whether the proposal aligns with the client budget.

### 8. Proposal Review Agent
Performs final quality review for professionalism, operational clarity, and thematic consistency.

### 9. Feedback Analysis Agent
Analyzes customer feedback sentiment and stores structured feedback records.


## Multi-Agent Workflow Orchestration

The system uses Microsoft Agent Framework to coordinate multiple specialized AI agents through a sequential catering operations workflow.

The workflow maintains shared context between agents and supports revision loops where agents refine proposals based on operational feedback.

### Workflow Pipeline

1. Receptionist Agent captures customer requirements
2. Azure AI Search retrieves operational catering knowledge
3. Menu Planning Agent generates an initial proposal
4. Inventory Agent validates ingredient quantities and shortages
5. Compliance Agent validates halal and dietary rules
6. Logistics Agent generates operational timelines
7. Monitoring Agent audits business and dietary risks
8. Pricing Agent explains pricing strategies and optimization insights
9. Proposal Review Agent evaluates proposal quality
10. Final validation rules are enforced before Azure Blob persistence

### Agent-to-Agent Collaboration

The workflow demonstrates agent collaboration through:
- shared workflow context
- proposal revision loops
- operational validation feedback
- sequential decision refinement

Example:
- Inventory feedback may trigger menu revision
- Compliance validation may trigger dietary substitutions
- Monitoring audits may trigger operational risk adjustments


## Hybrid AI + Deterministic Architecture

The system uses a hybrid architecture where AI agents generate recommendations and operational reasoning, while deterministic Python logic enforces critical business constraints.

### AI Responsibilities
- Menu generation
- Proposal writing
- Procurement reasoning
- Logistics planning
- Risk explanation
- Proposal quality review

### Deterministic Python Responsibilities
- Pricing calculations
- Budget validation
- Dietary conflict validation
- Guest count constraints
- Event timing validation
- Location support validation
- Theme authenticity validation
- Risk enforcement

This architecture prevents common LLM issues such as:
- Hallucinated pricing
- Invalid totals
- Contradictory compliance checks
- Unsupported operational requests


## Real-Time Workflow Execution

The frontend uses Server-Sent Events (SSE) to stream live workflow progress updates while agents coordinate the catering plan generation process.

Displayed workflow stages include:
- Receptionist Agent
- Azure AI Search Retrieval
- Menu Planning
- Inventory Analysis
- Compliance Validation
- Logistics Planning
- Risk Auditing
- Pricing Calculation
- Proposal Review
- Azure Blob Storage Persistence


## Business Rules & Validation

The platform includes deterministic business validation rules enforced through Python.

### Operational Constraints
- Minimum guests: 20 pax
- Maximum guests: 500 pax
- Minimum quality budget: RM70 per head
- Maximum operational budget: RM500 per head

### Validation Checks
- Dietary conflict detection
- Pork prohibition enforcement
- Theme authenticity validation
- Event timing validation
- West Malaysia location support validation
- Pricing sanity validation
- Budget exceedance detection

### Supported Dietary Restrictions
- Vegetarian
- Vegan
- Nut Allergy
- Dairy Free
- Gluten Free


## Supported Catering Themes

- Japanese Fusion
- Traditional Malay
- Chinese Fusion
- Western Corporate
- International Buffet


## Knowledge Base Integration

The system integrates Azure AI Search as an external knowledge retrieval layer.

Knowledge documents include:
- Supplier availability data
- Catering inventory rules
- Theme-specific cuisine guidelines
- Halal compliance standards
- Risk rulebooks
- Dietary substitution recommendations
- Logistics handling rules

The AI agents use this retrieved knowledge to generate more grounded operational decisions.


## System Architecture

<img src="screenshots/architecture_diagram.png" width="1000"/>

### Frontend
- Next.js
- TypeScript
- Tailwind CSS
- Real-time SSE workflow tracking

### Backend
- FastAPI
- Python
- Microsoft Agent Framework
- Ollama local LLM integration

### Cloud Services
- Azure AI Search
- Azure Blob Storage

### AI Workflow
- Multi-agent orchestration
- Shared workflow context
- Agent revision loops
- Deterministic backend validation


## Installation Requirements

Before running the project, ensure the following are installed:

- Python 3.11+
- Node.js 18+
- Ollama
- Git

### Ollama Model Setup

Pull the required Ollama model:

```bash
ollama pull llama3.2:3b
```

Ensure Ollama is running locally before starting the backend:

```bash
ollama serve
```

### AutoGen Installation

Install AutoGen dependencies:

```bash
pip install -U autogen-agentchat "autogen-ext[ollama]"
```


## Setup Instructions

### Python Virtual Environment Setup

Create and activate a Python virtual environment:

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

### Backend
```bash
pip install -r requirements.txt
uvicorn api:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```


## Environment Variables

### Backend Environment Variables

Create a `.env` file in the project root directory:

```env
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=plans
OLLAMA_MODEL=llama3.2:3b
```

### Frontend Environment Variables

Create a `.env.local` file inside the `frontend/` folder:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

IMPORTANT:
- `.env` is used by the FastAPI backend.
- `.env.local` is used by the Next.js frontend.
- Restart both frontend and backend servers after changing environment variables.


## Example Test Cases

### Test Case 1 — Successful Japanese Vegetarian Wedding
- Wedding
- Kuala Lumpur
- 100 pax
- Vegetarian
- RM100/head
- Japanese Fusion
- Eco-friendly packaging

Expected:
- Successful proposal generation
- Final quote within budget
- LOW RISK compliance validation

---

### Test Case 2 — Budget Below Quality Floor
- Corporate Lunch
- 80 pax
- RM50/head
- Western Corporate

Expected:
- Pricing validation warning
- Quality floor enforcement

---

### Test Case 3 — Unsupported Location
- Birthday Party
- Singapore
- 50 pax

Expected:
- West Malaysia validation failure

---

### Test Case 4 — Dietary Conflict Detection
- Vegetarian request
- Notes include chicken dish

Expected:
- Monitoring Agent flags dietary conflict


## Future Improvements

- Real supplier API integration
- Dynamic market-based pricing
- Live inventory synchronization
- Real-time kitchen monitoring
- Multi-language catering support
- Fine-tuned catering-specific LLMs
- Customer analytics dashboard
- Cloud deployment on Azure infrastructure
- Mobile application support
- Advanced recommendation engine


## Screenshots

### Homepage
![Homepage](screenshots/homepage.png)

### Real-Time Workflow Progress
![Workflow Progress](screenshots/progress_visual.png)

### Generated Catering Plan
![Generated Result](screenshots/generated_result.png)

### Terminal Output
![Generated Terminal Output](screenshots/terminal_output.png)

### Proposal Review
![Proposal Review](screenshots/proposal_review.png)

### Customer Feedback
![Feedback UI](screenshots/customer_feedback.png)

### Feedback Submission
![Feedback Saved](screenshots/feedback_saved.png)

### Test Cases
![Test Case 1](screenshots/test_case1.png)

### System Architecture
![Architecture](screenshots/architecture_diagram.jpg)


## Author

Myat Pan Ei Thu

