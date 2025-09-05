FROM python:3.11-slim

# Crear directorio de trabajo
WORKDIR /app

# Copiar y instalar dependencias
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copiar código de backend y frontend
COPY backend /app/backend
COPY frontend /app/frontend

# Exponer puerto de la aplicación
EXPOSE 8000

# Comando por defecto para arrancar la API
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
