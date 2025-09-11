FROM node:20-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
ENV NODE_ENV=production
EXPOSE 3001
USER app
CMD ["node", "server.js"]