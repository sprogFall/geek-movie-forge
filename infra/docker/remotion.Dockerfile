FROM node:22-alpine

WORKDIR /app

COPY apps/remotion_renderer/package.json ./package.json
COPY apps/remotion_renderer/server.js ./server.js

RUN npm install

EXPOSE 3100

CMD ["npm", "run", "start"]
