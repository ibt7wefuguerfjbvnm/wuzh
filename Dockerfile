FROM mcr.microsoft.com/playwright:v1.44.0-jammy

# Environment settings
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

WORKDIR /app

# Install Python and Pip
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy code
COPY . .

# Run Gunicorn with increased timeout for browser launches
CMD gunicorn --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --threads 4 app:app
