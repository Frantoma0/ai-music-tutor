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

COPY requirements.txt .

# Install PyTorch separately with explicit CUDA wheel.
# If cu121 fails later, switch this to cu124.
RUN pip install --no-cache-dir \
    torch==2.5.1 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu121

# Install remaining dependencies.
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/raw_storage /app/data/processed \
    /app/data/stems /app/data/midi /app/data/exports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
