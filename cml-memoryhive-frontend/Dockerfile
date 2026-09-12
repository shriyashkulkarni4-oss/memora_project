FROM node:24-alpine AS dependencies

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci


FROM dependencies AS development

COPY . .

EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD wget --quiet --output-document=/dev/null http://127.0.0.1:3000/ || exit 1

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]


FROM dependencies AS build

ARG VITE_API_URL=/api/v1
ARG VITE_GROUNDED_RECALL_ENABLED=false
ARG VITE_SUPPORT_EMAIL=support@memoryhive.example.com
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_GROUNDED_RECALL_ENABLED=$VITE_GROUNDED_RECALL_ENABLED
ENV VITE_SUPPORT_EMAIL=$VITE_SUPPORT_EMAIL

COPY . .
RUN npm run build


FROM nginx:1.30-alpine AS production

RUN apk upgrade --no-cache

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --output-document=/dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
