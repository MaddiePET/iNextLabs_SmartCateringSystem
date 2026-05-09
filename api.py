import asyncio
import json

from fastapi import FastAPI
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from fastapi.middleware.cors import CORSMiddleware

from app import generate_catering_plan

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

@app.get("/generate-plan-stream")
async def generate_plan_stream(user_request: str):
    async def event_generator():
        progress_queue = asyncio.Queue()

        async def progress_callback(step: str):
            await progress_queue.put(step)

        task = asyncio.create_task(
            generate_catering_plan(user_request, progress_callback)
        )

        while not task.done():
            try:
                step = await asyncio.wait_for(progress_queue.get(), timeout=0.5)
                yield {
                    "event": "progress",
                    "data": json.dumps({"step": step}),
                }
            except asyncio.TimeoutError:
                pass

        plan = await task

        yield {
            "event": "complete",
            "data": json.dumps(plan),
        }

    return EventSourceResponse(event_generator())