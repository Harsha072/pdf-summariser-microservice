# Use Python 3.11 (compatible with PyMuPDF)
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY flask-api/app/requirements.txt ./requirements.txt

# Install packages one by one to reduce memory spikes
# Install lightweight packages first
RUN pip install --no-cache-dir flask==3.0.0 flask-cors==4.0.0 python-dotenv==1.0.0 werkzeug==3.0.1 gunicorn==21.2.0

# Install medium packages
RUN pip install --no-cache-dir requests==2.31.0 openai==1.10.0

# Install numpy (needed by other packages)
RUN pip install --no-cache-dir numpy==1.23.5

# Install heavy ML packages one at a time with memory limits
RUN pip install --no-cache-dir --no-deps scikit-learn==1.2.2
RUN pip install --no-cache-dir --no-deps faiss-cpu==1.7.4
RUN pip install --no-cache-dir fuzzywuzzy==0.18.0 python-levenshtein==0.23.0
RUN pip install --no-cache-dir PyMuPDF==1.24.13

# Install sentence-transformers with minimal dependencies
RUN pip install --no-cache-dir sentence-transformers==2.5.1 huggingface-hub==0.20.3

# Install Firebase
RUN pip install --no-cache-dir firebase-admin==6.3.0

# Install Redis
RUN pip install --no-cache-dir redis==5.0.1

# Copy application code
COPY flask-api/app /app

# Create necessary directories
RUN mkdir -p data/citation_cache logs temp temp_uploads

# Expose the application port
EXPOSE ${PORT:-5000}

# Add environment variable for PORT (Railway compatibility)
ENV PORT=5000

# Add a health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Run with Gunicorn - USE ONLY 1 WORKER for 512MB RAM
CMD gunicorn --bind 0.0.0.0:${PORT:-5000} \
    --workers 1 \
    --threads 1 \
    --timeout 120 \
    --max-requests 100 \
    --max-requests-jitter 10 \
    --worker-class sync \
    --log-level info \
    main:app