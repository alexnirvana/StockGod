FROM python:3.12.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend backend
COPY content content
RUN pip install --no-cache-dir --no-deps -e backend && mkdir -p data
COPY scripts scripts
CMD ["python", "-m", "uvicorn", "stock_god.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
