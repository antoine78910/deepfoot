# DeepFoot backend – build context = repo root when using RAILWAY_DOCKERFILE_PATH=backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy backend only (context is repo root)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Railway injects PORT at runtime; use shell so $PORT is expanded
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
