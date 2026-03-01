# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend files
COPY backend/ .

# Ensure model directories exist (even if files are ignored by .hfignore)
RUN mkdir -p models/face_detection models/eye_tracking models/emotion_detection

# Expose the port FastAPI will run on
EXPOSE 7860

# Run the backend using Gunicorn and Uvicorn
# We set timeout to 120s to give models time to "not load" if missing
CMD ["gunicorn", "-w", "2", "--timeout", "120", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:7860"]
