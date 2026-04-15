FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/cache /app/tmp && \
    chmod -R 777 /app/logs /app/cache /app/tmp

EXPOSE 8000

CMD ["python", "app.py"]