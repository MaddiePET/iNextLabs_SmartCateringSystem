# iNextLabs Smart Catering Operations Planner

An AI-powered multi-agent system for smart catering operations. The system helps catering teams generate structured catering plans by coordinating specialized AI agents for customer intake, menu planning, inventory, compliance, logistics, pricing, risk validation, proposal review, and customer feedback analysis.

## Problem Statement Summary

Catering businesses often manage customer requirements, menu planning, inventory, procurement, logistics, pricing, and risk checks manually. This can lead to poor demand estimation, supplier issues, inconsistent pricing, and communication gaps.

This project solves the problem by using a multi-agent AI workflow that simulates a digital catering operations team.

## Solution Overview

The system allows a customer to enter event details through a Next.js frontend. The request is sent to a FastAPI backend, where multiple Ollama-powered AI agents collaborate to generate a complete catering plan.

The system also uses Azure AI Search as a knowledge base and Azure Blob Storage to store generated plans and customer feedback. Each plan is assigned a `plan_id`, and feedback is linked back to the same plan.

## Tech Stack

- Next.js
- TypeScript
- Tailwind CSS
- FastAPI
- Python
- Ollama
- Azure AI Search
- Azure Blob Storage
- Server-Sent Events
- GitHub

## Features

- Multi-agent catering workflow
- AI menu planning
- Inventory & procurement analysis
- Halal compliance validation
- Allergy conflict detection
- Logistics planning
- Pricing optimization
- Deterministic risk validation
- Customer feedback analysis
- Azure AI Search integration
- Azure Blob Storage persistence
- Real-time SSE workflow updates

## AI Agents

- Receptionist Agent
- Menu Planning Agent
- Inventory & Procurement Agent
- Compliance Agent
- Logistics Planning Agent
- Monitoring Agent
- Pricing Optimization Agent
- Proposal Review Agent
- Feedback Analysis Agent

## System Architecture

<img src="screenshots/architecture_diagram.png" width="1000"/>

## Setup Instructions

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

```env
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=
AZURE_STORAGE_CONNECTION_STRING=
OLLAMA_MODEL=llama3.2:3b
```

## Example Test Cases

### Valid Case (Test Case 1)
- Kuala Lumpur
- 120 pax
- Vegetarian
- RM150/head
- 14-day preparation window

### High Risk Case (Test Case 2)

- London
- Same-day event
- Nut allergy conflict
- RM50/head luxury request

## Future Improvements

- AutoGen migration
- Supplier portal integration
- Live inventory synchronization
- Customer dashboard
- Analytics reporting
- AI-powered menu recommendation engine

## Author

Myat Pan Ei Thu

## Screenshots

![Homepage](screenshots/homepage.png)
