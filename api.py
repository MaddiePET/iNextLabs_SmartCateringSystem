from fastapi import FastAPI
from pydantic import BaseModel
from app import generate_catering_plan
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CateringRequest(BaseModel):
    user_request: str


@app.get("/")
async def root():
    return {"message": "Smart Catering API is running"}


@app.post("/generate-plan")
async def generate_plan(request: CateringRequest):
    plan = await generate_catering_plan(request.user_request)
    return plan