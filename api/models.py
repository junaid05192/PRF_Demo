from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from database import Base


class MmwaveReading(Base):
    __tablename__ = "mmwave_readings"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    bird_count = Column(Integer, nullable=False)
    activity_score = Column(Float, nullable=False)
    clustering_score = Column(Float, nullable=False)
    heatmap = Column(JSONB, nullable=True)


class EnvironmentReading(Base):
    __tablename__ = "environment_readings"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)


class CameraFrame(Base):
    __tablename__ = "camera_frames"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    image_url = Column(String, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
