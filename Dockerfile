# === STAGE 1: Build Stage ===
FROM python:3.12-slim as builder

# Install system build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        pkg-config \
        cmake \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-ind \
        libtesseract-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# Install uv first
RUN pip install --upgrade pip
RUN pip install --no-cache-dir uv

# Install dependencies
COPY requirements.txt ./
RUN uv pip install uvicorn --system
RUN uv pip install -r requirements.txt --system

# Copy source code
COPY lib ./lib
COPY llm_engine.py .
COPY main.py .
COPY routes ./routes
COPY dependencies.py .
COPY utils.py .
COPY .env .

# === STAGE 2: Final Runtime Stage ===
FROM python:3.12-slim

WORKDIR /app

# Reinstall runtime system dependencies (excluding build-only ones)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-ind \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy installed Python packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 1234

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1234"]