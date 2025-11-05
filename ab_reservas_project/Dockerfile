FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Dependencias del sistema necesarias para compilar psycopg y manejar PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl libpq-dev gcc \
 && rm -rf /var/lib/apt/lists/*

# Instalar Poetry (versión bloqueada)
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

# Copiar archivos de dependencias y resolver con caché
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias
RUN poetry install --no-root

# Copiar el resto del código fuente
COPY . .

EXPOSE 8000

# Ejecutar Uvicorn en modo desarrollo con autoreload
CMD ["poetry", "run", "uvicorn", "ab_reservas_project.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]
