FROM python:3.11-slim

WORKDIR /app

# Upgrade pip first to avoid compatibility issues
RUN pip install --no-cache-dir --upgrade pip

# Install dependencies with retries for network resilience
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
