from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class MmwaveReadingIn(BaseModel):
    node_id: str
    timestamp: Optional[datetime] = None
    bird_count: int
    activity_score: float
    clustering_score: float
    heatmap: Optional[List[List[float]]] = None


class EnvironmentReadingIn(BaseModel):
    node_id: str
    timestamp: Optional[datetime] = None
    temperature: float
    humidity: float


class CameraFrameOut(BaseModel):
    node_id: str
    timestamp: datetime
    image_url: str

    class Config:
        from_attributes = True


class PenLatestOut(BaseModel):
    node_id: str
    timestamp: Optional[datetime] = None
    bird_count: Optional[int] = None
    activity_score: Optional[float] = None
    clustering_score: Optional[float] = None
    heatmap: Optional[List[List[float]]] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    camera_url: Optional[str] = None


class HistoryPointOut(BaseModel):
    timestamp: datetime
    bird_count: Optional[int] = None
    activity_score: Optional[float] = None
    clustering_score: Optional[float] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
