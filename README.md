# Boletix

Boletix es un sistema de boletaje simplificado construido con **FastAPI** para el backend y un frontend estático.  El objetivo principal de este proyecto es demostrar conceptos clave como autenticación con JWT, endpoints REST, actualizaciones en tiempo real vía WebSockets y un flujo básico de compra de asientos para eventos.

## Características

- **API REST** para listar eventos, consultar asientos y comprar boletos.
- **Autenticación JWT** con un usuario demo (`demo/demo`).
- **Actualización en tiempo real** de los asientos mediante WebSockets (`/ws/events/{event_id}`).
- **Dockerfile** y **docker‑compose** para levantar la aplicación con un solo comando.
- **Pruebas unitarias** con `pytest` utilizando `fastapi.testclient`.
- **Workflows de GitHub Actions** para CI y publicación automática de la imagen a GHCR.

## Cómo ejecutar

### Docker

1. Clona este repositorio y ubícate en la raíz del proyecto.
2. Crea un archivo `.env` con la variable `JWT_SECRET` para firmar tokens JWT:

   ```env
   JWT_SECRET=supersecret
   ```

3. Ejecuta los servicios con Docker Compose:

   ```bash
   docker compose up -d
   ```

4. Accede a la aplicación en [http://localhost:8000](http://localhost:8000).  El frontend estático sirve una página mínima que consume la API.

### Local

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

### Endpoints principales

| Método | Endpoint                           | Descripción                             |
|-------:|------------------------------------|-----------------------------------------|
| GET    | `/api/events`                      | Lista de eventos disponibles            |
| GET    | `/api/events/{event_id}/seats`     | Lista de asientos de un evento          |
| POST   | `/api/login`                       | Login con `email` y `password`          |
| POST   | `/api/orders`                      | Crear orden `{event_id, seat_ids}`      |
| WS     | `/ws/events/{event_id}`            | Conexión WebSocket para actualizaciones |

## Pruebas manuales

1. Abrir dos pestañas en el mismo evento. Comprar un asiento en una y verificar que en la otra se deshabilita en tiempo real.
2. Intentar comprar dos veces el mismo asiento; la segunda petición devuelve **409** y se refresca el estado.
3. Tras una compra exitosa, visitar `/tickets/{orderId}/qrcode.png` para ver el código QR del ticket.

### Pruebas de carga

Se incluye un script de ejemplo en `k6/test.js` para ejecutar pruebas de carga con [k6](https://k6.io). Para ejecutarlo vía Docker:

```bash
docker run --rm --network host -i grafana/k6 run - < k6/test.js
```

### Pruebas unitarias

Usa `pytest` para ejecutar las pruebas:

```bash
pip install -r backend/requirements.txt
pytest -q
```

## Licencia

Este proyecto se distribuye bajo la licencia MIT.
