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

## Architecture Diagram

Customer
   |
   v
Next.js Frontend
   |
   v
FastAPI Backend
   |
   v
Ollama Multi-Agent Workflow
   |
   +--> Azure AI Search Knowledge Base
   |
   +--> Local Knowledge Files
   |
   v
Generated Catering Plan
   |
   v
System Validation Layer
   |
   v
Azure Blob Storage
   |
   v
Customer Feedback Form
   |
   v
Feedback Analysis Agent
   |
   v
Linked Feedback Saved to Azure Blob Storage