FROM python:3.11-slim

# Metadatos del autor
LABEL maintainer="TFM Neurosimbólico Bancario"
LABEL description="Backend FastAPI - Orquestador del sistema neurosimbólico bancario"

# Establecer directorio de trabajo
WORKDIR /app_root

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app_root

# Instalar dependencias del sistema necesarias para pymysql y cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY app/ ./app/
COPY bde.json ./bde.json

# Exponer el puerto de Uvicorn
EXPOSE 8000

# Comando de arranque en modo producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
