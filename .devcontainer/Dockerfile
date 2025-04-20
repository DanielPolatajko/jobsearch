FROM python:3.11-slim

# Install git and other essential tools
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/root/.cargo/bin:${PATH}" 