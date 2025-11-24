# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SKIP_DOTENV=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install production server dependencies
RUN pip install --no-cache-dir gunicorn whitenoise

# Ensure data directories exist inside the image (will be backed by volumes)
RUN mkdir -p /app/data /app/data/media

# Expose port
EXPOSE 8000

# Set entrypoint (script lives in bind-mounted project directory)
ENTRYPOINT ["bash", "/app/docker-entrypoint.sh"]

# Run gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "story_django.wsgi:application"]