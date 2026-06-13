FROM mcr.microsoft.com/playwright:v1.44.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

WORKDIR /app

# Install Python and Pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Ensure playwright browsers are installed for the python environment
RUN playwright install chromium

# Copy the application code
COPY . .

# Railway ignores EXPOSE and uses the PORT env var. 
# We use the shell form of CMD to allow variable expansion.
CMD gunicorn --bind 0.0.0.0:$PORT --timeout 120 app:app
