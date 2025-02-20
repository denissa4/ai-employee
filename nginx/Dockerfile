FROM nginx:1.13

WORKDIR /etc/nginx/
COPY ./nginx.conf ./nginx.conf

WORKDIR /var/
RUN mkdir -p log/nginx
WORKDIR /var/www/html/
RUN mkdir -p bot/static
VOLUME /app/api/docsAI/models


CMD ["nginx", "-g", "daemon off;"]