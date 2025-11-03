import os, json
from pathlib import Path
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from schema import Phone, ChatRequest
from service import ChatService
import uvicorn


# FastAPI setup
app = FastAPI()

origins = [
    "http://localhost:5173",
    "https://mykaarma-assesment-frontend.vercel.app",
    "https://vercel.com/vinay-saraswats-projects/mykaarma-assesment-frontend/GkudFd4kDgYim7MM7H2YMwtCX6Cn"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ChatService once
chat_service = ChatService()

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/chat")
def chat(body: ChatRequest):
    return chat_service.process_chat(body)

# uvicorn entrypoint
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
