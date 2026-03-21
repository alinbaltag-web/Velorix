FROM python:3.11-slim

WORKDIR /app

COPY mobile/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mobile/ ./mobile/

EXPOSE 8080

CMD ["gunicorn", "mobile.api_server:app", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60"]
