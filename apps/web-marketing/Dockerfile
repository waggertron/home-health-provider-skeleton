# Multi-stage build for the marketing site.

FROM node:20-alpine AS builder

WORKDIR /app

COPY apps/web-marketing/package.json apps/web-marketing/package-lock.json ./
RUN npm ci

COPY apps/web-marketing/ ./
RUN npm run build


FROM node:20-alpine

ENV NODE_ENV=production

WORKDIR /app

COPY apps/web-marketing/package.json apps/web-marketing/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=builder /app/.next ./.next

EXPOSE 3002

HEALTHCHECK --interval=10s --timeout=5s --retries=12 \
  CMD node -e "fetch('http://127.0.0.1:3002').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["npx", "next", "start", "-p", "3002"]
