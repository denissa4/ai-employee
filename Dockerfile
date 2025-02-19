# Base image
FROM python:3.11

# Set the working directory
WORKDIR /main

# Copy all files from the ai-employee directory to /main in the container
COPY . /main/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Expose port
EXPOSE 8000

# Start the app with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "bossman:app"]
