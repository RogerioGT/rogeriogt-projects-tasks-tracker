# syntax=docker/dockerfile:1
# ---- Backend build stage ----
FROM python:3.12-slim AS backend
WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app

# ---- Frontend build stage (populated in Phase 2; placeholder for now) ----
FROM node:20-alpine AS frontend-build
WORKDIR /fe
COPY frontend/ ./
RUN npm install && npm run build

# ---- Final runtime stage ----
FROM python:3.12-slim
WORKDIR /app
COPY --from=backend /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=backend /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY backend/app ./app
COPY --from=frontend-build /fe/dist ./frontend/dist
RUN mkdir -p /app/data
EXPOSE 8787
ENV DATA_DIR=/app/data
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8787"]
