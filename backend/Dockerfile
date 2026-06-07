# ==========================================
# Stage 1: Build dependencies
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compilation tools needed for C-extension wheels if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements or create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install packages
COPY requirements.txt .
# If requirements.txt doesn't exist, we install core modules
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    python-dotenv \
    langchain-core \
    langgraph \
    pdfplumber \
    sqlalchemy \
    psycopg2-binary \
    python-multipart \
    requests \
    reportlab

# ==========================================
# Stage 2: Final runtime container
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Install runtime system libraries (e.g. libpq for postgres, pdf dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Copy source code
COPY app/ ./app/

# Expose port and configure standard runner user for security
EXPOSE 8000
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser

# Start Uvicorn production server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
