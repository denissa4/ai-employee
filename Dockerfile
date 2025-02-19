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

# Install Python dependencies from requirements.txt (make sure requirements.txt is present in ai-employee)
COPY requirements.txt /main/
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for the Flask app
EXPOSE 8000

# Run the Flask app directly with Python
CMD ["python3", "bossman.py"]
