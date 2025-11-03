from typing import List, Optional, Literal
import os, json
from schema import ChatContext,Phone,ChatRequest
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY", "")
if not API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY")

client = Groq(api_key=API_KEY)

# Groq 
def groq_json(prompt: str) -> dict:
    """Ask Groq to return structured JSON data."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a precise natural‑language parser that converts user questions about "
                "smartphones into structured JSON intents. The JSON must strictly follow:\n"
                "{'task': one of ['search','compare','explain','details'],"
                " 'brands': list of brand names from provided list,"
                " 'budgetMin': int or null, 'budgetMax': int or null,"
                " 'features': list of user priorities (camera, battery, performance, etc.),"
                " 'compareNames': optional list of model names,"
                " 'explainTopic': optional string, 'targetPhoneId': optional string,"
                " 'hardBrandOnly': boolean}"
            ),
        },
        {"role": "user", "content": prompt},
    ]
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    try:
        raw = completion.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        print("Groq parser error:", e)
        return {}

def groq_answer(prompt: str) -> Optional[str]:
    """Generate a concise assistant reply."""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are 'PhoneGuide', an expert smartphone assistant for India. "
                        "Only refer to phones that are explicitly provided in the prompt. "
                        "Be factual, clear, and under 150 words."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=280,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print("Groq answer error:", e)
        return None
    

# Follow-up question 
def handle_follow_up(user_msg: str, ctx: ChatContext, last_phone: Optional[Phone]) -> Optional[dict]:
    """Handle follow-up questions about previously shown phones."""
    if not last_phone:
        return None
    
    follow_up_indicators = [
        "this phone", "that phone", "the phone", "tell me more", "details", 
        "about it", "brief", "explain", "describe", "more info", "like this"
    ]
    
    msg_lower = user_msg.lower()
    is_follow_up = any(indicator in msg_lower for indicator in follow_up_indicators)
    
    if is_follow_up:
        prompt = f"""
            User asked: {user_msg}
            About this phone: {last_phone.name} by {last_phone.brand} - ₹{last_phone.priceInr}
            Key specs: {last_phone.display.sizeInches}" {last_phone.display.type}, {last_phone.cameras.mainMP}MP camera, 
        {  last_phone.batteryMah}mAh battery, {last_phone.soc} processor

            Write a friendly, detailed explanation about this specific phone focusing on:
            - Key features and strengths
            - Who it's best for
            - What makes it stand out
            Keep it under 150 words and only talk about this phone.
        """
        text = groq_answer(prompt) or f"The {last_phone.name} is a great choice with excellent features."
        
        return {
            "text": text,
            "items": [last_phone.model_dump()],
            "intent": {"task": "details", "targetPhoneId": last_phone.id},
        }
    
    return None