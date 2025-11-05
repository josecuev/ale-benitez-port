# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilar psycopg2 y manejar PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    gcc \
 && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - --version $POETRY_VERSION

# Copiar solo los archivos de dependencias primero (mejor caché)
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias del proyecto (sin instalar el proyecto como paquete)
RUN poetry install --no-root

# Copiar el resto del código fuente
COPY . .

EXPOSE 8000

# Comando por defecto: servidor Django con hot reload
CMD ["poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]
