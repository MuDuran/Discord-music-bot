# Use Python 3.13 slim image as base
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies including FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create directories for downloads and cookies
RUN mkdir -p downloads cookies

# Create a non-root user for security
RUN useradd -m -s /bin/bash musicbot
RUN chown -R musicbot:musicbot /app
USER musicbot

# Expose port (not strictly necessary for Discord bot, but good practice)
EXPOSE 8080

# Health check (optional - checks if the bot process is running)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD pgrep -f "python main.py" || exit 1

# Run the application
CMD ["python", "main.py"]