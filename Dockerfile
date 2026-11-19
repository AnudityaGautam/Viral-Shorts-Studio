# ==============================================================================
# Production Dockerfile for Viral Shorts Studio
# Base image: Official Python 3.11 Slim (Debian Bookworm)
# ==============================================================================
FROM python:3.11-slim

# Configure runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=5000 \
    HOST=0.0.0.0 \
    ENVIRONMENT=production \
    OPEN_BROWSER=0

# Install required system packages:
# - ffmpeg & libass: Video extraction, 9:16 layout formatting, and .ass subtitle burn-in
# - nodejs: Runtime required by yt-dlp for YouTube JavaScript signature decryption
# - fontconfig & fonts: Font rendering engine and fonts for 3D kinetic subtitles
# - curl: Health check probing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass9 \
    libass-dev \
    nodejs \
    fontconfig \
    fonts-liberation \
    fonts-dejavu-core \
    fonts-freefont-ttf \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Configure fontconfig aliases for subtitle fonts (Impact and Arial Black)
RUN mkdir -p /etc/fonts/conf.d && \
    printf '<?xml version="1.0"?>\n\
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n\
<fontconfig>\n\
  <match target="pattern">\n\
    <test name="family" qual="any"><string>Impact</string></test>\n\
    <edit name="family" mode="assign" binding="same"><string>DejaVu Sans</string></edit>\n\
    <edit name="weight" mode="assign" binding="same"><const>black</const></edit>\n\
  </match>\n\
  <match target="pattern">\n\
    <test name="family" qual="any"><string>Arial Black</string></test>\n\
    <edit name="family" mode="assign" binding="same"><string>Liberation Sans</string></edit>\n\
    <edit name="weight" mode="assign" binding="same"><const>bold</const></edit>\n\
  </match>\n\
</fontconfig>\n' > /etc/fonts/conf.d/99-viral-shorts-fonts.conf && \
    fc-cache -fv

WORKDIR /app

# Install Python dependencies first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY . .

# Remove Windows executable and create required runtime directories
RUN rm -f ffmpeg.exe && \
    mkdir -p uploads output assets/sfx

# Create non-root application user for container security
RUN useradd -u 1000 -m -s /bin/bash appuser && \
    mkdir -p uploads output assets/sfx /home/appuser/.cache && \
    chown -R appuser:appuser /app /home/appuser/.cache

USER appuser

# Pre-download Faster-Whisper tiny model into image cache for zero cold-start delay
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"

EXPOSE 5000

# Container healthcheck using lightweight dedicated health API endpoint (dynamically evaluates $PORT)
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD sh -c 'curl -f "http://localhost:${PORT:-5000}/api/health" || exit 1'

CMD ["python", "server.py"]
