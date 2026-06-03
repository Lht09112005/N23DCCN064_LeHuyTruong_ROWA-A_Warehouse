FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy coordinator source code
COPY coordinator/ /app/

# Ensure static and data directories exist for volume mounts
RUN mkdir -p /app/static /app/data

# Start the Coordinator Flask app
CMD ["python", "app.py"]
