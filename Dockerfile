# Use a base Python image
FROM python:3.11

# Set the working directory in the container
WORKDIR /main

# Copy all files from the ai-employee directory to /main in the container
COPY . /main/

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies from requirements.txt (ensure requirements.txt includes gunicorn)
COPY requirements.txt /main/
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for the Flask app
EXPOSE 8080

# Run the Flask app using Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "bossman:app"]
