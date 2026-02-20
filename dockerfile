FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install uv
RUN pip install --no-cache-dir uv

# Create app user (production safety)
RUN useradd -m appuser

# Create workdir
WORKDIR /proj

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Activate uv virtualenv path
ENV PATH="/proj/.venv/bin:$PATH"

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source
COPY app ./app

# Change ownership
RUN chown -R appuser:appuser /proj
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
