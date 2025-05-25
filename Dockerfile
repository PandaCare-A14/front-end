FROM python:3.9-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput || echo "No static files"

# Expose port (Railway uses 8080)
EXPOSE 8080

# Run with Railway's PORT environment variable
CMD gunicorn --bind 0.0.0.0:$PORT pandacare.wsgi:application