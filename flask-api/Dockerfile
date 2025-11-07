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

# CRITICAL: Install numpy 1.x FIRST before any other package
# faiss-cpu 1.7.4 is compiled with NumPy 1.x and WILL CRASH with NumPy 2.x
RUN pip install --no-cache-dir "numpy<2.0.0,>=1.23.0"

# Install lightweight packages
RUN pip install --no-cache-dir flask==3.0.0 flask-cors==4.0.0 python-dotenv==1.0.0 werkzeug==3.0.1 gunicorn==21.2.0

# Install medium packages
RUN pip install --no-cache-dir requests==2.31.0 openai==1.10.0

# Install scikit-learn (will use existing numpy)
RUN pip install --no-cache-dir scikit-learn==1.2.2

# Install faiss-cpu (MUST have numpy<2.0 already installed)
RUN pip install --no-cache-dir faiss-cpu==1.7.4

# Install text processing
RUN pip install --no-cache-dir fuzzywuzzy==0.18.0 python-levenshtein==0.23.0

# Install PyMuPDF
RUN pip install --no-cache-dir PyMuPDF==1.24.13

# Install sentence-transformers with dependencies
RUN pip install --no-cache-dir sentence-transformers==2.5.1 huggingface-hub==0.20.3

# Install Firebase
RUN pip install --no-cache-dir firebase-admin==6.3.0

# Install Redis
RUN pip install --no-cache-dir redis==5.0.1

# Copy application code
COPY flask-api/app /app

# Create necessary directories
RUN mkdir -p data/citation_cache logs temp temp_uploads

# Expose the application port (Render uses dynamic PORT)
EXPOSE 10000

# Run with Gunicorn - USE ONLY 1 WORKER for 512MB RAM
# Increased timeout for slow ML model initialization
# Use $PORT from environment (Render sets this automatically)
CMD gunicorn --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 1 \
    --timeout 300 \
    --graceful-timeout 120 \
    --max-requests 100 \
    --max-requests-jitter 10 \
    --worker-class sync \
    --log-level info \
    --preload \
    --access-logfile - \
    --error-logfile - \
    main:app