FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libsndfile1-dev \
    curl \
    git \
    fluidsynth \
    fluid-soundfont-gm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch separately with explicit CUDA wheel.
# If cu121 fails later, switch this to cu124.
RUN pip install --no-cache-dir \
    --default-timeout=1000 \
    --retries 10 \
    torch==2.5.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .

# Install remaining dependencies, excluding basic-pitch itself.
RUN pip install --no-cache-dir \
    --default-timeout=1000 \
    --retries 10 \
    -r requirements.txt

# Install Basic Pitch without TensorFlow dependencies.
# Runtime uses ONNX backend via onnxruntime.
RUN pip install --no-cache-dir \
    --default-timeout=1000 \
    --retries 10 \
    --no-deps \
    basic-pitch==0.4.0

# Verify critical dependency chain at build time.
RUN python3 -c "import torch; import librosa; import soundfile; import demucs; import onnxruntime; import basic_pitch; from basic_pitch.inference import predict; print('Dependencies OK')"

COPY . .

RUN mkdir -p /app/data/raw_storage /app/data/processed \
    /app/data/stems /app/data/midi /app/data/exports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
