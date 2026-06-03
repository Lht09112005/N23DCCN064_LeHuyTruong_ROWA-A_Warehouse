FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy node source code
COPY node/ /app/

# Ensure data directory exists for volume mounting
RUN mkdir -p /app/data

# Start the Flask app directly
CMD ["python", "app.py"]
