from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

import models
import storage
from database import Base, SessionLocal, engine, get_db
from schemas import (
    EnvironmentReadingIn,
    HistoryPointOut,
    MmwaveReadingIn,
    PenLatestOut,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FlockSense API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/readings/mmwave")
def post_mmwave_reading(reading: MmwaveReadingIn, db: Session = Depends(get_db)):
    row = models.MmwaveReading(
        node_id=reading.node_id,
        timestamp=reading.timestamp or datetime.now(timezone.utc),
        bird_count=reading.bird_count,
        activity_score=reading.activity_score,
        clustering_score=reading.clustering_score,
        heatmap=reading.heatmap,
    )
    db.add(row)
    db.commit()
    return {"status": "ok"}


@app.post("/api/readings/environment")
def post_environment_reading(reading: EnvironmentReadingIn, db: Session = Depends(get_db)):
    row = models.EnvironmentReading(
        node_id=reading.node_id,
        timestamp=reading.timestamp or datetime.now(timezone.utc),
        temperature=reading.temperature,
        humidity=reading.humidity,
    )
    db.add(row)
    db.commit()
    return {"status": "ok"}


@app.post("/api/camera/frame")
async def post_camera_frame(
    node_id: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    image_url = storage.upload_frame(node_id, content, file.content_type or "image/jpeg")
    row = models.CameraFrame(
        node_id=node_id,
        timestamp=datetime.now(timezone.utc),
        image_url=image_url,
    )
    db.add(row)
    db.commit()
    return {"status": "ok", "image_url": image_url}


@app.get("/api/pens/latest", response_model=List[PenLatestOut])
def get_pens_latest(db: Session = Depends(get_db)):
    node_ids = {
        row[0]
        for row in db.query(models.MmwaveReading.node_id).distinct().all()
    } | {
        row[0]
        for row in db.query(models.EnvironmentReading.node_id).distinct().all()
    }

    results = []
    for node_id in sorted(node_ids):
        mmwave = (
            db.query(models.MmwaveReading)
            .filter(models.MmwaveReading.node_id == node_id)
            .order_by(desc(models.MmwaveReading.timestamp))
            .first()
        )
        env = (
            db.query(models.EnvironmentReading)
            .filter(models.EnvironmentReading.node_id == node_id)
            .order_by(desc(models.EnvironmentReading.timestamp))
            .first()
        )
        camera = (
            db.query(models.CameraFrame)
            .filter(models.CameraFrame.node_id == node_id)
            .order_by(desc(models.CameraFrame.timestamp))
            .first()
        )

        results.append(
            PenLatestOut(
                node_id=node_id,
                timestamp=mmwave.timestamp if mmwave else None,
                bird_count=mmwave.bird_count if mmwave else None,
                activity_score=mmwave.activity_score if mmwave else None,
                clustering_score=mmwave.clustering_score if mmwave else None,
                heatmap=mmwave.heatmap if mmwave else None,
                temperature=env.temperature if env else None,
                humidity=env.humidity if env else None,
                camera_url=camera.image_url if camera else None,
            )
        )
    return results


@app.get("/api/pens/history", response_model=List[HistoryPointOut])
def get_pens_history(node_id: str, hours: int = 48, db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    mmwave_rows = (
        db.query(models.MmwaveReading)
        .filter(models.MmwaveReading.node_id == node_id)
        .filter(models.MmwaveReading.timestamp >= since)
        .order_by(models.MmwaveReading.timestamp)
        .all()
    )
    env_rows = (
        db.query(models.EnvironmentReading)
        .filter(models.EnvironmentReading.node_id == node_id)
        .filter(models.EnvironmentReading.timestamp >= since)
        .order_by(models.EnvironmentReading.timestamp)
        .all()
    )

    points = {}
    for r in mmwave_rows:
        points[r.timestamp] = HistoryPointOut(
            timestamp=r.timestamp,
            bird_count=r.bird_count,
            activity_score=r.activity_score,
            clustering_score=r.clustering_score,
        )
    for r in env_rows:
        if r.timestamp in points:
            points[r.timestamp].temperature = r.temperature
            points[r.timestamp].humidity = r.humidity
        else:
            points[r.timestamp] = HistoryPointOut(
                timestamp=r.timestamp,
                temperature=r.temperature,
                humidity=r.humidity,
            )

    return [points[ts] for ts in sorted(points)]


@app.get("/api/camera/latest")
def get_camera_latest(node_id: str, db: Session = Depends(get_db)):
    camera = (
        db.query(models.CameraFrame)
        .filter(models.CameraFrame.node_id == node_id)
        .order_by(desc(models.CameraFrame.timestamp))
        .first()
    )
    if not camera:
        return {"node_id": node_id, "image_url": None, "timestamp": None}
    return {"node_id": node_id, "image_url": camera.image_url, "timestamp": camera.timestamp}


# Serve the FlockSense dashboard frontend
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
if DASHBOARD_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")
