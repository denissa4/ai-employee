# Use a base Python image
FROM python:3.11

WORKDIR /

COPY . /

RUN apt-get update && apt-get install -y \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "server:app"]
