FROM node:20-slim

WORKDIR /app

COPY package.json ./
RUN npm install --production=false

COPY . .

EXPOSE 4100

CMD ["npx", "tsx", "relay.ts"]
