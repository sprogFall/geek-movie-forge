FROM node:22-alpine

WORKDIR /app

COPY apps/frontend/package.json ./package.json
COPY apps/frontend/tsconfig.json ./tsconfig.json
COPY apps/frontend/next-env.d.ts ./next-env.d.ts
COPY apps/frontend/next.config.ts ./next.config.ts
COPY apps/frontend/app ./app
COPY apps/frontend/components ./components
COPY apps/frontend/lib ./lib
COPY apps/frontend/types ./types

RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
