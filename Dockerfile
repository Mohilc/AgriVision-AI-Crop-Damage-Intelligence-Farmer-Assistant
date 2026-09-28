FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install essential system dependencies for Pillow and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Create persistent data directories
RUN mkdir -p data/uploads

# Expose Streamlit web server port
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Default launch command runs the Streamlit Web Control Center
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
