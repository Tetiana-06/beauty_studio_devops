import json
import os
import random
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import Booking, SessionLocal, init_db
from datetime import UTC, datetime


# Версія застосунку. Міняється вручну перед збіркою нового образу (ЛР-5, 6, 7).
APP_VERSION = "7.0.0"

# Частка штучних помилок (0.0 = вимкнено, 0.5 = 50% помилок для ЛР-7 п. 6b)
FAIL_RATE = float(os.getenv("FAIL_RATE", "0.0"))

# Prometheus метрики (ЛР-7 п. 2a)
# Лічильник запитів з мітками method, endpoint (маршрут), status
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

# Гістограма тривалості запитів з мітками method, endpoint
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception:
        pass
    yield


app = FastAPI(title="Beauty Studio API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_route_path(request: Request) -> str:
    """Нормалізує шлях запиту, щоб уникнути розростання кількості міток (low cardinality)."""
    path = request.url.path
    if path.startswith("/api/bookings/") and len(path.split("/")) > 3:
        return "/api/bookings/{booking_id}"
    return path


@app.middleware("http")
async def monitor_and_log_requests(request: Request, call_next):
    """
    Middleware:
    1. Рахує Prometheus метрики (кількість і тривалість).
    2. Виводить структуровані JSON-логи у stdout (ЛР-7 п. 3).
    3. Симулює помилки за змінною FAIL_RATE (ЛР-7 п. 6b).
    """
    route_path = get_route_path(request)
    start_time = time.time()

    # Симуляція помилок 500 для тестування відкату Rollout (ЛР-7 п. 6b)
    # Пропускаємо /health та /metrics, щоб probes K8s і скрапінг не відмовляли
    if (
        FAIL_RATE > 0.0
        and route_path not in ["/health", "/metrics"]
        and random.random() < FAIL_RATE
    ):
        status_code = 500
        duration = round(time.time() - start_time, 4)

        REQUEST_COUNT.labels(
            method=request.method, endpoint=route_path, status=str(status_code)
        ).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=route_path).observe(
            duration
        )

        log_entry = {
            "time": datetime.now(UTC).isoformat(),
            "level": "ERROR",
            "message": "Simulated error due to FAIL_RATE",
            "method": request.method,
            "route": route_path,
            "status": status_code,
            "duration": duration,
        }
        print(json.dumps(log_entry), flush=True)
        return JSONResponse(
            status_code=500, content={"detail": "Simulated error (FAIL_RATE)"}
        )

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as exc:
        status_code = 500
        raise exc from None
    finally:
        duration = round(time.time() - start_time, 4)
        REQUEST_COUNT.labels(
            method=request.method, endpoint=route_path, status=str(status_code)
        ).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=route_path).observe(
            duration
        )

        level = "ERROR" if status_code >= 500 else ("WARNING" if status_code >= 400 else "INFO")
        log_entry = {
            "time": datetime.now(UTC).isoformat(),
            "level": level,
            "message": f"{request.method} {route_path} completed",
            "method": request.method,
            "route": route_path,
            "status": status_code,
            "duration": duration,
        }
        print(json.dumps(log_entry), flush=True)

    return response


class BookingCreate(BaseModel):
    client_name: str
    service: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Beauty Studio API", "version": APP_VERSION}


@app.get("/version")
def get_version():
    return {"version": APP_VERSION}


@app.get("/metrics")
def get_metrics():
    """Ендпоінт метрик для Prometheus (ЛР-7 п. 2a)."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/slow")
def slow_endpoint(delay: float = 0.5):
    """Повільний ендпоінт для демонстрації затримки на дашборді (ЛР-7 п. 5)."""
    time.sleep(delay)
    return {"status": "delayed", "delay_seconds": delay}


@app.get("/api/bookings")
def get_bookings(db: Session = Depends(get_db)):
    return db.query(Booking).all()


@app.post("/api/bookings", status_code=201)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    new_booking = Booking(client_name=booking.client_name, service=booking.service)
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking


@app.delete("/api/bookings/{booking_id}", status_code=204)
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
