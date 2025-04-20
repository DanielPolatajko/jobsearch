FROM python:3.11-slim

# Install git and other essential tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Set up working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy requirements file
COPY ./src/requirements.txt .

# Install dependencies
RUN uv pip install -r requirements.txt --system

# Copy source code
COPY . .

# Install the package in development mode
WORKDIR /workspace/src
RUN uv pip install -e . --system