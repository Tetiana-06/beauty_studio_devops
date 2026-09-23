from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import SessionLocal, Booking, init_db
from fastapi import HTTPException

app = FastAPI(title="Beauty Studio API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookingCreate(BaseModel):
    client_name: str
    service: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    try:
        init_db()
    except Exception:
        pass

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "Beauty Studio API"}

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
    return None