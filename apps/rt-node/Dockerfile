# Multi-stage build for the real-time gateway.
# Stage 1 installs all deps and compiles TypeScript to dist/.
# Stage 2 ships only prod deps + dist/ for a smaller runtime image.

FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/rt-node/package.json apps/rt-node/package-lock.json ./
RUN npm ci

COPY apps/rt-node/tsconfig.json ./
COPY apps/rt-node/src ./src
RUN npm run build


FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

COPY apps/rt-node/package.json apps/rt-node/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/dist ./dist

EXPOSE 8080

HEALTHCHECK --interval=5s --timeout=3s --retries=6 \
  CMD node -e "fetch('http://127.0.0.1:8080/healthz').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "--enable-source-maps", "dist/server.js"]
