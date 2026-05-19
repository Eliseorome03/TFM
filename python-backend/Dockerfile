# Usar una imagen oficial de Python optimizada y ligera
FROM python:3.11-slim

# Metadatos
LABEL maintainer="Desarrollador"
LABEL description="Backend FastAPI para Asistente Bancario Neurosimbólico"

# Prevenir la escritura de archivos .pyc y mostrar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Establecer la carpeta de trabajo dentro del contenedor
WORKDIR /app

# Primero copiamos solo el archivo de requerimientos para aprovechar la caché de capas de Docker
COPY requirements.txt .

# Instalar las dependencias de Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código del backend
COPY . .

# Exponemos el puerto 8000 tal como lo solicitaste
EXPOSE 8000

# Usamos Uvicorn para ejecutar la aplicación que creamos en api_controller.py
# Escuchando en 0.0.0.0 para aceptar conexiones fuera del contenedor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
