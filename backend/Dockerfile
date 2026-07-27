# syntax=docker/dockerfile:1
#
# B10.1 — deployment/CI image for T2. NOT the dev workflow: while coding, run
# `npm run start:dev` on the host against Postgres in Docker. This image is for
# `docker compose up` (demo) and CI.
#
# Base is Debian-slim, not alpine: Prisma (arriving in B8.1) fights musl/openssl
# on alpine. Node 20 per the project decision; 22 LTS also works.

# ---- deps: full install, for compiling ------------------------------------
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- build: TypeScript -> dist --------------------------------------------
FROM node:20-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# When B8.1 adds Prisma, generate the client here (needs prisma/schema.prisma):
# RUN npx prisma generate
RUN npm run build

# ---- prod-deps: runtime dependencies only ---------------------------------
FROM node:20-slim AS prod-deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# ---- runtime: minimal, non-root -------------------------------------------
FROM node:20-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
COPY --from=prod-deps --chown=node:node /app/node_modules ./node_modules
COPY --from=build     --chown=node:node /app/dist         ./dist
COPY --chown=node:node package.json ./
USER node
EXPOSE 3001
CMD ["node", "dist/main"]
