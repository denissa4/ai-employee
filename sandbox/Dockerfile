# Dockerfile for the sandbox container (sandbox folder)
FROM python:3.11

# Set the working directory
WORKDIR /sandbox

# Copy the requirements file and install dependencies
COPY requirements.txt /sandbox/requirements.txt
RUN pip install --no-cache-dir -r /sandbox/requirements.txt

# Copy the sandbox server code into the container
COPY . /sandbox

# Run the sandbox server
CMD ["python3", "server.py"]
