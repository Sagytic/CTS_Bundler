# 프로덕션형 정적 빌드 + nginx (docker compose에서 api와 함께 사용)
FROM node:22-alpine AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# 비우면 브라우저가 같은 호스트의 /api 로 요청 → nginx가 api 컨테이너로 프록시
ENV VITE_API_BASE_URL=
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
