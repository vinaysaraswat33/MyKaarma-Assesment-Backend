import os, json
from pathlib import Path
from typing import List, Optional, Literal
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# ===== Load env & configure =====
load_dotenv()
API_KEY = os.getenv("GROQ_API_KEY", "")
if not API_KEY:
    raise RuntimeError("Missing GROQ_API_KEY")

client = Groq(api_key=API_KEY)

# ===== Data Schemas =====
class Display(BaseModel):
    sizeInches: float
    type: str
    refreshHz: int
    resolution: str

class Cameras(BaseModel):
    mainMP: int
    ultraMP: Optional[int] = None
    teleMP: Optional[int] = None
    ois: Optional[bool] = False
    eis: Optional[bool] = False
    selfieMP: Optional[int] = None

class Features(BaseModel):
    fiveG: bool
    nfc: Optional[bool] = False
    wirelessCharging: Optional[bool] = False
    ipRating: Optional[str] = ""

class Dims(BaseModel):
    height: float
    width: float
    thickness: float
    weight: float

class Scores(BaseModel):
    camera: Optional[float] = None
    battery: Optional[float] = None
    performance: Optional[float] = None
    display: Optional[float] = None
    value: Optional[float] = None

class Phone(BaseModel):
    id: str
    name: str
    brand: str
    priceInr: int
    os: str
    soc: str
    ramGB: int
    storageGB: int
    display: Display
    batteryMah: int
    chargingWatt: int
    cameras: Cameras
    features: Features
    dims: Dims
    release: str
    tags: List[str]
    scores: Scores
    image: Optional[str] = None
    url: Optional[str] = None

class ChatMessage(BaseModel):
    role: Literal['user', 'assistant']
    content: str

class ChatContext(BaseModel):
    lastItemIds: Optional[List[str]] = None
    selectedPhoneId: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[ChatContext] = None

class Intent(BaseModel):
    task: Literal['search', 'compare', 'explain', 'details']
    brands: Optional[List[str]] = None
    budgetMin: Optional[int] = None
    budgetMax: Optional[int] = None
    features: Optional[List[str]] = None
    compareNames: Optional[List[str]] = None
    explainTopic: Optional[str] = None
    targetPhoneId: Optional[str] = None
    hardBrandOnly: bool = False

# ===== Load dataset =====
DATA_PATH = Path(__file__).parent / "data" / "phones.json"
CATALOG: List[Phone] = [Phone(**p) for p in json.loads(DATA_PATH.read_text(encoding="utf-8"))]
BRANDS = sorted({p.brand for p in CATALOG})

# ===== Groq helpers =====
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

# ===== Intent parsing =====
def parse_intent(text: str, ctx: Optional[ChatContext]) -> Intent:
    llm_intent = groq_json(f"User query: {text}\nDataset brands: {', '.join(BRANDS)}")
    
    # Default values for optional lists
    brands = llm_intent.get("brands", [])
    features = llm_intent.get("features", [])
    compare_names = llm_intent.get("compareNames", [])
    
    return Intent(
        task=llm_intent.get("task", "search"),
        brands=brands if brands else None,
        budgetMin=llm_intent.get("budgetMin"),
        budgetMax=llm_intent.get("budgetMax"),
        features=features if features else None,
        compareNames=compare_names if compare_names else None,
        explainTopic=llm_intent.get("explainTopic"),
        targetPhoneId=llm_intent.get("targetPhoneId"),
        hardBrandOnly=bool(llm_intent.get("brands")),
    )

# ===== Retrieval engine =====
def score_phone(p: Phone, intent: Intent) -> float:
    s = p.scores
    score = 0.0
    if intent.budgetMax:
        diff = max(0, p.priceInr - intent.budgetMax)
        score += 1.0 if diff <= 0 else 0.4
    if intent.brands and p.brand.lower() in [b.lower() for b in intent.brands]:
        score += 1.0
    if intent.features:
        if "camera" in intent.features: score += (s.camera or 7)/10 * 1.5
        if "battery" in intent.features: score += (s.battery or 7)/10 * 1.3
        if "performance" in intent.features: score += (s.performance or 7)/10 * 1.2
    return score

def retrieve(intent: Intent, catalog: List[Phone]) -> List[Phone]:
    items = list(catalog)
    if intent.budgetMax:
        items = [p for p in items if p.priceInr <= intent.budgetMax + 3000]
    if intent.brands:
        items = [p for p in items if p.brand.lower() in [b.lower() for b in intent.brands]] or items
    items.sort(key=lambda x: score_phone(x, intent), reverse=True)
    return items[:3]

def get_phone_by_id(pid: str, catalog: List[Phone]) -> Optional[Phone]:
    for p in catalog:
        if p.id == pid:
            return p
    return None

# ===== Explanation topics handler =====
def handle_explanation(topic: str) -> str:
    """Handle explanation requests for common smartphone topics."""
    explanations = {
        "ois": (
            "OIS (Optical Image Stabilization) uses physical lens/sensor movement to counteract "
            "camera shake. It's better for low-light photos and video, providing smoother stabilization "
            "without cropping the image. Phones like Google Pixel and Samsung flagships have excellent OIS."
        ),
        "eis": (
            "EIS (Electronic Image Stabilization) uses software and gyroscope data to stabilize video "
            "by cropping and adjusting the frame. It's more common in budget phones and works well for "
            "video but can reduce image quality slightly due to cropping."
        ),
        "ois vs eis": (
            "OIS vs EIS: OIS uses physical hardware (better for photos, no quality loss) while EIS uses "
            "software (good for video, may crop image). Flagship phones often use both - OIS for photos "
            "and hybrid stabilization for video. For photography, OIS is superior."
        ),
        "camera": (
            "Smartphone cameras vary by sensor size, megapixels, and processing. Larger sensors (like in "
            "Google Pixel) capture more light. Megapixels matter for detail but sensor quality is more important. "
            "Look for phones with good OIS, large sensors, and proven computational photography."
        ),
        "battery": (
            "Battery life depends on capacity (mAh), processor efficiency, and software optimization. "
            "Phones with 5000mAh+ batteries like OnePlus Nord CE 4 offer excellent endurance. "
            "Fast charging (67W+) quickly replenishes battery, useful for heavy users."
        ),
        "performance": (
            "Performance is driven by processor (SoC), RAM, and cooling. Snapdragon 8 Gen series and "
            "Dimensity 8000/9000 series offer flagship performance. For gaming, look for phones with "
            "good thermal management and high refresh rate displays."
        ),
        "display": (
            "Display quality depends on type (OLED vs AMOLED), refresh rate (60Hz vs 120Hz+), and "
            "brightness. OLED displays offer better colors and contrast. High refresh rates (120Hz+) "
            "provide smoother scrolling and gaming. Look for good outdoor visibility (high nits brightness)."
        )
    }
    
    topic_lower = topic.lower()
    for key, explanation in explanations.items():
        if key in topic_lower:
            return explanation
    
    # If no predefined explanation, use Groq
    prompt = f"Explain this smartphone topic in simple terms under 150 words: {topic}"
    return groq_answer(prompt) or f"I can explain {topic}. In smartphones, this refers to..."

# ===== Follow-up question handler =====
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
{last_phone.batteryMah}mAh battery, {last_phone.soc} processor

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

# ===== FastAPI setup =====
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

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/chat")
def chat(body: ChatRequest):
    user_msg = next((m.content.strip() for m in reversed(body.messages) if m.role == "user"), "")
    ctx = body.context or ChatContext()

    print(f"Received query: {user_msg}")
    print(f"Context: {ctx}")

    # --- Handle explanation queries first ---
    intent = parse_intent(user_msg, ctx)
    print(f"Parsed intent: {intent}")

    if intent.task == "explain" and intent.explainTopic:
        explanation = handle_explanation(intent.explainTopic)
        return {
            "text": explanation,
            "items": [],
            "intent": intent.model_dump(),
        }

    # --- Handle follow-up questions about last shown phone ---
    last_phone = None
    if ctx.lastItemIds:
        last_phone = get_phone_by_id(ctx.lastItemIds[0], CATALOG) if ctx.lastItemIds else None
    
    follow_up_response = handle_follow_up(user_msg, ctx, last_phone)
    if follow_up_response:
        return follow_up_response

    # --- Handle "tell me more" case when a phone is selected ---
    is_detail_query = any(word in user_msg.lower() for word in ["detail", "spec", "more", "about", "tell me"])
    if ctx.selectedPhoneId and is_detail_query:
        phone = get_phone_by_id(ctx.selectedPhoneId, CATALOG)
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

    # --- Normal search or compare mode ---
    picks = retrieve(intent, CATALOG)
    pick_summaries = [
        f"{p.name} — ₹{p.priceInr}: {p.display.sizeInches}\" {p.display.type}, "
        f"{p.cameras.mainMP}MP main, {p.batteryMah}mAh"
        for p in picks
    ]

    prompt = (
        f"User message: {user_msg}\n"
        f"Intent parsed: {intent.model_dump()}\n"
        f"Phones in dataset: {pick_summaries}\n\n"
        f"Write a short, under‑150‑word PhoneGuide reply suggesting only these phones."
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

# ===== Main entry =====
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
