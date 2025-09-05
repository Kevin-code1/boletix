from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from jose import jwt
from pydantic import BaseModel
from typing import Dict, List, Tuple
import os
from datetime import datetime, timedelta
import asyncio
from itertools import count
from io import BytesIO
import qrcode
from dotenv import load_dotenv

# Cargar variables de entorno desde .env para ejecución local
load_dotenv()
# Clave secreta usada para firmar JWT
SECRET_KEY: str = os.getenv("JWT_SECRET", "changeme")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

app = FastAPI(title="Boletix API", openapi_url="/openapi.json")


class Event(BaseModel):
    id: int
    name: str


class Seat(BaseModel):
    id: int
    number: str
    sold: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class Order(BaseModel):
    id: int
    event_id: int
    seat_id: int


# Datos en memoria para eventos y asientos. Cada evento tiene un listado de asientos.
events_data: Dict[int, Dict[str, List[Seat] or Event]] = {
    1: {
        "event": Event(id=1, name="Rock Concert"),
        "seats": [Seat(id=i, number=f"A{i}", sold=False) for i in range(1, 21)],
    },
    2: {
        "event": Event(id=2, name="Jazz Night"),
        "seats": [Seat(id=i, number=f"B{i}", sold=False) for i in range(1, 16)],
    },
}

# Diccionario para mantener conexiones WebSocket por evento
connections: Dict[int, List[WebSocket]] = {}

# Locks para control de concurrencia por asiento
locks: Dict[Tuple[int, int], asyncio.Lock] = {}

# Almacén simple de órdenes
orders: Dict[int, Order] = {}
order_counter = count(1)

# Intentos de login por IP para rate limiting
login_attempts: Dict[str, List[datetime]] = {}


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Genera un token JWT con expiración."""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/api/login")
async def login(payload: LoginRequest, request: Request):
    """
    Login JSON simple (email/password). Usuario demo: demo@example.com / demo
    con limitación de 5 intentos por minuto por IP.
    """
    ip = request.client.host if request.client else "unknown"
    now = datetime.utcnow()
    attempts = [t for t in login_attempts.get(ip, []) if now - t < timedelta(minutes=1)]
    if len(attempts) >= 5:
        raise HTTPException(status_code=429, detail="Demasiados intentos, intente luego")
    attempts.append(now)
    login_attempts[ip] = attempts

    if payload.email != "demo@example.com" or payload.password != "demo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    access_token = create_access_token(
        data={"sub": payload.email},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/events", response_model=List[Event])
async def get_events():
    """Devuelve la lista de eventos."""
    return [v["event"] for v in events_data.values()]


@app.get("/api/events/{event_id}/seats", response_model=List[Seat])
async def get_seats(event_id: int):
    """Devuelve la lista de asientos de un evento."""
    if event_id not in events_data:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return events_data[event_id]["seats"]


@app.post("/api/events/{event_id}/seats/{seat_id}/purchase")
async def purchase_seat(event_id: int, seat_id: int):
    """Compra de asiento con control de concurrencia y creación de orden."""
    event = events_data.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")

    lock = locks.setdefault((event_id, seat_id), asyncio.Lock())
    async with lock:
        for seat in event["seats"]:
            if seat.id == seat_id:
                if seat.sold:
                    raise HTTPException(status_code=409, detail="Asiento ya vendido")
                seat.sold = True
                order_id = next(order_counter)
                order = Order(id=order_id, event_id=event_id, seat_id=seat_id)
                orders[order_id] = order
                for ws in connections.get(event_id, []):
                    await ws.send_json({"seat_id": seat_id, "sold": True})
                return {"message": "Compra exitosa", "order_id": order_id}
    raise HTTPException(status_code=404, detail="Asiento no encontrado")


@app.get("/api/orders", response_model=List[Order])
async def get_orders():
    """Listado simple de órdenes generadas."""
    return list(orders.values())


@app.get("/tickets/{order_id}/qrcode.png")
async def ticket_qr(order_id: int):
    """Devuelve un PNG con el QR que contiene datos de la orden firmados."""
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    token = jwt.encode(order.dict(), SECRET_KEY, algorithm=ALGORITHM)
    img = qrcode.make(token)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return StreamingResponse(buf, media_type="image/png")


@app.websocket("/ws/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: int):
    """
    Conexión WebSocket para recibir actualizaciones en tiempo real de los asientos.
    El cliente debe enviar cualquier mensaje para mantener la conexión, aunque no se utiliza el contenido.
    """
    await websocket.accept()
    event_id = int(event_id)
    # Añadir la conexión a la lista
    connections.setdefault(event_id, []).append(websocket)
    try:
        while True:
            # mantenemos la conexión abierta
            await websocket.receive_text()
    except WebSocketDisconnect:
        # remover la conexión cuando se desconecta
        connections[event_id].remove(websocket)


# Servir archivos estáticos del frontend
frontend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
