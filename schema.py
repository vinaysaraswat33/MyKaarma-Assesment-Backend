from typing import List, Optional, Literal
from pydantic import BaseModel, Field



class Display(BaseModel):
    sizeInches: float
    type: str
    refreshHz: int
    resolution: str

from pydantic import BaseModel, field_validator

class Cameras(BaseModel):
    mainMP: int
    ultraMP: Optional[int] = None
    teleMP: Optional[int] = None
    ois: bool = False
    eis: bool = False
    selfieMP: Optional[int] = None

    @field_validator("mainMP", "ultraMP", "teleMP", "selfieMP", mode="before")
    def cast_to_int(cls, v):
        if isinstance(v, float):
            return int(v)
        return v


class Features(BaseModel):
    fiveG: bool
    nfc: bool = False
    wirelessCharging: bool = False
    ipRating: str = ""

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

# =======================
# Main Phone Schema
# =======================

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
    tags: List[str] = Field(default_factory=list)
    scores: Scores
    image: Optional[str] = None
    url: Optional[str] = None


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatContext(BaseModel):
    lastItemIds: Optional[List[str]] = None
    selectedPhoneId: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    context: Optional[ChatContext] = None

class Intent(BaseModel):
    task: Literal["search", "compare", "explain", "details"]
    brands: Optional[List[str]] = None
    budgetMin: Optional[int] = None
    budgetMax: Optional[int] = None
    features: Optional[List[str]] = None
    compareNames: Optional[List[str]] = None
    explainTopic: Optional[str] = None
    targetPhoneId: Optional[str] = None
    hardBrandOnly: bool = False
