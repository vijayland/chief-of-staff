# Pin to specific Alpine version and upgrade OS packages to clear known CVEs
FROM node:20-alpine3.21 AS deps
RUN apk upgrade --no-cache
WORKDIR /app
COPY package*.json ./
RUN npm ci

# ── Builder ───────────────────────────────────────────────────────────────────
FROM node:20-alpine3.21 AS builder
RUN apk upgrade --no-cache
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NODE_ENV=production
RUN npm run build

# ── Runner (minimal production image) ────────────────────────────────────────
FROM node:20-alpine3.21 AS runner
RUN apk upgrade --no-cache
WORKDIR /app
ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

COPY --from=builder /app/public                                ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static     ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
