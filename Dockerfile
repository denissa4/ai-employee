# Use a base Python image
FROM python:3.11

RUN apt-get update && \
    apt-get install -y  \
        curl  \
        apt-transport-https \
        gnupg2 && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    curl -fsSL https://deb.nodesource.com/setup_16.x | bash - && \
    apt-get update -y && \
    ACCEPT_EULA=Y apt-get install -y \
        msodbcsql17 \
#        mssql-tools \
        unixodbc-dev \
        libgssapi-krb5-2 \
        nodejs \
        supervisor \
        nginx && \
    apt-get autoremove -y && \
        apt-get clean \
        && rm -rf /var/lib/apt/lists && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile && \
    echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc

WORKDIR /app
COPY . /app/

RUN pip install -r /app/requirements.txt && \
    mkdir -p /var/www/html/bot/static && \
    cp /app/nginx/nginx.conf /etc/nginx/nginx.conf

RUN cd /app/bot && \
npm install && \
npm run build

# Ensure the supervisord configuration is copied
COPY supervisord.conf /app/supervisord.conf

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
