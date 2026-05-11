FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copy project files
COPY . .

# Expose the port (we'll use 8001 to avoid clashing with your other site)
EXPOSE 8001

# Run Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8001", "app:app"]
