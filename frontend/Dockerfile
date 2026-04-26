FROM node:20-alpine AS build

WORKDIR /app

# Copy package.json (required) and yarn.lock (if present)
COPY package.json ./
COPY yarn.lock* ./

# Use frozen-lockfile only if yarn.lock exists, otherwise generate it
RUN if [ -f yarn.lock ]; then \
      yarn install --frozen-lockfile; \
    else \
      echo "WARNING: yarn.lock not found — installing without lockfile (non-reproducible)"; \
      yarn install; \
    fi

COPY . .

# Use production craco config (without Emergent plugins)
RUN cp craco.config.prod.js craco.config.js

# Build arg for backend URL
ARG REACT_APP_BACKEND_URL
ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL

RUN yarn build

# Production — nginx
FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx-spa.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
