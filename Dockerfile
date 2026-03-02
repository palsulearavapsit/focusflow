FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Explicitly copy models first to be 100% sure they are there
COPY backend/models/ ./models/

# Copy the rest of the backend files
COPY backend/ .

# Ensure permissions
RUN chmod -R 777 models/

EXPOSE 7860

CMD ["gunicorn", "-w", "2", "--timeout", "120", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:7860"]
