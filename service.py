from model import ChatRequest, ChatContext
from utils import parse_intent, handle_explanation, get_phone_by_id, retrieve
from schema import Phone
from model import handle_follow_up,groq_answer
from pathlib import Path
import os, json
from typing import List

# Load dataset 
DATA_PATH = Path(__file__).parent / "data" / "phones.json"
CATALOG: List[Phone] = [Phone(**p) for p in json.loads(DATA_PATH.read_text(encoding="utf-8"))]
BRANDS = sorted({p.brand for p in CATALOG})

class ChatService:
    def __init__(self):
        self.catalog = CATALOG

    def process_chat(self, body: ChatRequest):
        user_msg = next((m.content.strip() for m in reversed(body.messages) if m.role == "user"), "")
        ctx = body.context or ChatContext()

        print(f"Received query: {user_msg}")
        print(f"Context: {ctx}")

        # Handle explanation queries first 
        intent = parse_intent(user_msg, ctx)
        print(f"Parsed intent: {intent}")

        if intent.task == "explain" and intent.explainTopic:
            explanation = handle_explanation(intent.explainTopic)
            return {
                "text": explanation,
                "items": [],
                "intent": intent.model_dump(),
            }

        #Handle follow-up questions about last phone
        last_phone = None
        if ctx.lastItemIds:
            last_phone = get_phone_by_id(ctx.lastItemIds[0], self.catalog) if ctx.lastItemIds else None

        follow_up_response = handle_follow_up(user_msg, ctx, last_phone)
        if follow_up_response:
            return follow_up_response

        # Handle "tell me more" case when a phone is select
        is_detail_query = any(word in user_msg.lower() for word in ["detail", "spec", "more", "about", "tell me"])
        if ctx.selectedPhoneId and is_detail_query:
            phone = get_phone_by_id(ctx.selectedPhoneId, self.catalog)
            if not phone:
                return {"text": "Sorry, I couldn't find that phone.", "items": [], "intent": {"task": "details"}}

            prompt = f"""
            User asked: {user_msg}
            Selected phone details (from dataset): {phone.model_dump()}
            Write a friendly and factual summary under 150 words.
            Focus only on this phone — key highlights, ideal audience, and unique strengths.
            Do not mention or suggest other models.
            """
            text = groq_answer(prompt) or "Sorry, I couldn't fetch a response."
            return {
                "text": text,
                "items": [phone.model_dump()],
                "intent": {"task": "details", "targetPhoneId": phone.id},
            }

        # Normal search or compare mode 
        picks = retrieve(intent, self.catalog)
        pick_summaries = [
            f"{p.name} — ₹{p.priceInr}: {p.display.sizeInches}\" {p.display.type}, "
            f"{p.cameras.mainMP}MP main, {p.batteryMah}mAh"
            for p in picks
        ]

        prompt = (
            f"User message: {user_msg}\n"
            f"Intent parsed: {intent.model_dump()}\n"
            f"Phones in dataset: {pick_summaries}\n\n"
            f"Write a short, under-150-word PhoneGuide reply suggesting only these phones."
        )

        text = groq_answer(prompt) or "Sorry, I couldn't fetch a response."

        # Update context with new items
        new_context = ChatContext(
            lastItemIds=[p.id for p in picks] if picks else [],
            selectedPhoneId=ctx.selectedPhoneId  # Preserve existing selection
        )

        return {
            "text": text,
            "items": [p.model_dump() for p in picks],
            "intent": intent.model_dump(),
            "context": new_context
        }
