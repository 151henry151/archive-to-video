# Archive to YouTube - Web UI
FROM python:3.12-slim

# Install ffmpeg (required for video creation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY backend/ backend/
COPY frontend/ frontend/
COPY config/ config/
COPY upload.py run_web.py VERSION ./

# Create temp directory
RUN mkdir -p temp

# Default port (override with PORT env)
ENV PORT=18765
EXPOSE 18765

# Run the web server
CMD ["python", "run_web.py"]
