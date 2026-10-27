# Use official lightweight Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000

# Install system dependencies (curl for healthcheck and certificates for TLS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 appuser

# Copy dependency requirements first to take advantage of Docker layer caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY core/ ./core/
COPY providers/ ./providers/
COPY static/ ./static/
COPY server.py .

# Create empty alerts database file and transfer ownership to appuser
RUN touch alerts_db.json && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose default application port
EXPOSE 3000

# Health check to ensure service is actively responding
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Start Uvicorn ASGI server
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT}"]
