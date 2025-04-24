# Use a lightweight Python base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements file and install dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ .

# Expose the application port
EXPOSE 7860

# Add a health check (optional)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s CMD curl -f http://localhost:7860 || exit 1

# Default command
CMD ["python", "gradio_interface.py"]