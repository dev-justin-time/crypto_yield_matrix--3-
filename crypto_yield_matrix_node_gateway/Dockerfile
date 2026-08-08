FROM node:22-bookworm-slim

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci

COPY tsconfig.json index.ts server.ts agents.ts smoke.ts ./
RUN npm run check

USER node
EXPOSE 3000
CMD ["npm", "start"]
