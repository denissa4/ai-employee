# Dockerfile for the main container (app folder)
FROM python:3.11

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the main server code into the container
COPY . /app

# Expose the port for Flask (8000 for this case)
EXPOSE 8000

# Run the main server
CMD ["python3", "bossman.py"]
