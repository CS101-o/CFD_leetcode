FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and XFoil
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install XFoil
RUN wget https://web.mit.edu/drela/Public/web/xfoil/xfoil6.99.tgz \
    && tar -xzf xfoil6.99.tgz \
    && cd Xfoil \
    && mkdir -p bin \
    && cd plotlib \
    && ./install \
    && cd ../bin \
    && gfortran -o xfoil ../src/*.f -L../plotlib -lPlt \
    && cp xfoil /usr/local/bin/ \
    && cd / \
    && rm -rf Xfoil xfoil6.99.tgz

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads models

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
