# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY ./app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Copy application code
COPY ./app .

# Expose the application port
EXPOSE 5000

# Add environment variable for PORT (Railway compatibility)
ENV PORT=5000

# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Run with Gunicorn for production (2 workers for Railway/low-memory environments)
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${MAX_WORKERS:-2} --threads 2 --timeout 120 --access-logfile - --error-logfile - main:app