FROM node:16-alpine

WORKDIR /app
RUN apk add py3-pip
RUN apk add gcc musl-dev python3-dev libffi-dev openssl-dev cargo make
RUN pip install --upgrade pip
RUN pip install azure-cli

COPY . .
RUN npm install && npm cache clean --force
RUN npm run build

CMD ["npm", "start"]
