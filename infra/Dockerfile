FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["sh", "-c", "exec python -m uvicorn supportjudge_api.api:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
