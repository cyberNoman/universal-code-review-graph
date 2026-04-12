# Universal Code Review Graph - Docker Image
# Usage:
#   docker build -t code-graph .
#   docker run -v $(pwd):/workspace code-graph build /workspace

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY universal-code-graph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY universal-code-graph/ .

# Install the package
RUN pip install -e .

# Set working directory for mounted projects
WORKDIR /workspace

# Default command
ENTRYPOINT ["code-graph-server"]
CMD ["--help"]
