FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default port, can be overridden by cloud platform
ENV PORT=8000

# Start Uvicorn with a single worker to preserve in-memory session state
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
