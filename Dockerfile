# ==============================================================================
# Challenge 1.2: Zero-Downtime Hybrid Cloud Migration Mission Control
# Full-Stack Container (Clean Architecture Backend + Holographic Web UI)
# ==============================================================================
FROM python:3.11-slim-bullseye

WORKDIR /app

# Set environment defaults for container networking
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    PYTHONPATH=/app

# Install security updates and curl for container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and web assets
COPY . .

# Generate initial dataset if not present
RUN python -c "import os; from data.generate_raw_data import generate_raw_trades; from data.cleanse_data import cleanse_market_data; os.makedirs('data', exist_ok=True); os.path.exists('data/raw_trades.csv') or generate_raw_trades('data/raw_trades.csv', 1000); os.path.exists('data/cleaned_trades.csv') or cleanse_market_data('data/raw_trades.csv', 'data/cleaned_trades.csv')"

# Expose HTTP port
EXPOSE 8080

# Healthcheck to ensure container is healthy
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT:-8080}/api/status || exit 1

# Start full-stack HTTP, SSE and UI server
CMD ["python", "server.py"]
