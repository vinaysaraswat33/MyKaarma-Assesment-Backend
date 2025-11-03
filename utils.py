from typing import List, Optional, Literal
from schema import ChatContext,Intent,Phone
from model import groq_json
from pathlib import Path
import os, json

# Load dataset 
DATA_PATH = Path(__file__).parent / "data" / "phones.json"
CATALOG: List[Phone] = [Phone(**p) for p in json.loads(DATA_PATH.read_text(encoding="utf-8"))]
BRANDS = sorted({p.brand for p in CATALOG})

# Intent parsing 
def parse_intent(text: str, ctx: Optional[ChatContext]) -> Intent:
    llm_intent = groq_json(f"User query: {text}\nDataset brands: {', '.join(BRANDS)}")
    

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

# Retrieval engine 
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

#Explanation topics 
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
