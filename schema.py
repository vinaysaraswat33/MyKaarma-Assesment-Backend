from typing import List, Optional, Literal
from pydantic import BaseModel

# Data Schemas
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