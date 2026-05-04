FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    curl \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Create necessary directories
RUN mkdir -p downloads logs assets/fonts

# Download default font for thumbnail generation
RUN wget -q -O assets/fonts/NotoSans-Bold.ttf \
    "https://github.com/google/fonts/raw/main/ofl/notosans/NotoSans-Bold.ttf" || true

CMD ["python", "bot.py"]
