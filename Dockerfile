# Use an official Python runtime as a parent image
FROM python:3.11

# Create and set the working directory
WORKDIR /main

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install supervisor for process management
RUN apt-get update && apt-get install -y supervisor

# Install Python dependencies
COPY requirements.txt /main/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files into the container from ai-employee directory
COPY . /main/

# Copy the supervisor config
COPY ./supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose the necessary port
EXPOSE 8000

# Start supervisor to manage the processes
CMD ["/usr/bin/supervisord"]
