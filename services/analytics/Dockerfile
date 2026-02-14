FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including PostgreSQL client libs for psycopg)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY services/analytics/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/analytics/ .

# Expose port
EXPOSE 9000

# Run AgentOS server
CMD ["python", "main.py"]
