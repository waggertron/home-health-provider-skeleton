# Multi-stage build for the ops console.
# Stage 1 installs deps and runs the Next.js production build.
# Stage 2 ships only what `next start` needs.

FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/web-ops/package.json apps/web-ops/package-lock.json ./
RUN npm ci

COPY apps/web-ops/ ./
RUN npm run build


FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

COPY apps/web-ops/package.json apps/web-ops/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/.next ./.next

EXPOSE 3001

HEALTHCHECK --interval=10s --timeout=5s --retries=12 \
  CMD node -e "fetch('http://127.0.0.1:3001').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npx", "next", "start", "-p", "3001"]
