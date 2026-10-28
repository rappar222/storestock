# Stage 1: Compile High-Speed Rust Axum Gateway Binary
FROM rust:1.80-slim as rust-builder

WORKDIR /build
COPY rust_server/Cargo.toml rust_server/Cargo.lock* ./
COPY rust_server/countries.json ./
COPY rust_server/src ./src

RUN cargo build --release

# Stage 2: Final Production Container (Rust Gateway + Python Scraper Worker)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=3000

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN useradd -m -u 1000 appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY core/ ./core/
COPY providers/ ./providers/
COPY static/ ./static/
COPY server.py .
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Copy compiled native Rust gateway from builder stage
COPY --from=rust-builder /build/target/release/storestock_server .

RUN touch alerts_db.json && chown -R appuser:appuser /app

USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

CMD ["./docker-entrypoint.sh"]
