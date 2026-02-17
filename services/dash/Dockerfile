FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

# System dependencies for psycopg and SQLAlchemy
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/dash/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/dash/ .

EXPOSE 9000

CMD ["python", "main.py"]
