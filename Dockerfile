# ─── Solar Quote Tool ───
# Multi-stage Docker build

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies (WeasyPrint, PostgreSQL, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Production stage ───
FROM base AS production

COPY solar_app/ /app/

# Collect static files
RUN python manage.py collectstatic --noinput || true

# Create non-root user
RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app /app
USER app

EXPOSE 8000

CMD ["gunicorn", "solar_app.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
