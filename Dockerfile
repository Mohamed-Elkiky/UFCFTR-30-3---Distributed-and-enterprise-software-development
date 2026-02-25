# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Set Django settings module
ENV DJANGO_SETTINGS_MODULE=brfn.settings.dev

# Entrypoint: waits for DB, runs migrations, loads seed data
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command (overridden by docker-compose)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]