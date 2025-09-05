from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from jose import jwt
from pydantic import BaseModel
from typing import Dict, List
import os
from datetime import datetime, timedelta

# Cargar la clave secreta desde variables de entorno (usada para firmar JWT). Si no existe, usar un valor por defecto.
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


def create_access_token(data: dict, expires_delta: timedelta) -> str:
    """Genera un token JWT con expiración."""
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Endpoint de login. Acepta usuario y contraseña y devuelve un token JWT.
    Actualmente sólo existe un usuario demo (demo/demo).
    """
    username = form_data.username
    password = form_data.password
    # usuario demo
    if username != "demo" or password != "demo":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    access_token = create_access_token(
        data={"sub": username},
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
    """
    Permite comprar un asiento.  Si el asiento ya se vendió devuelve 409.
    Si la compra tiene éxito notifica a los WebSockets conectados.
    """
    event = events_data.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    # buscar asiento
    for seat in event["seats"]:
        if seat.id == seat_id:
            if seat.sold:
                raise HTTPException(status_code=409, detail="Asiento ya vendido")
            seat.sold = True
            # Notificar a los clientes conectados por WebSocket
            for ws in connections.get(event_id, []):
                await ws.send_json({"seat_id": seat_id, "sold": True})
            return {"message": "Compra exitosa"}
    raise HTTPException(status_code=404, detail="Asiento no encontrado")


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
