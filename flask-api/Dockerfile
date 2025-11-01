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

# Add a health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:5000/health || exit 1

# Run with Gunicorn for production (4 workers, 2 threads each)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "main:app"]