FROM python:3.11-slim

# ffmpeg is needed to turn browser webm/opus into the 16 kHz wav whisper reads
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data/samples ./data/samples

# writable location for the database and recordings; mount a disk here to keep them
ENV HEALTHSYNC_DATA_DIR=/data
RUN mkdir -p /data

# no GPU on a normal cloud host
ENV HEALTHSYNC_ASR_DEVICE=cpu
ENV HEALTHSYNC_ASR_COMPUTE=int8
ENV HEALTHSYNC_ASR_MODEL=tiny

EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
