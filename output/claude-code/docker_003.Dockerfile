FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DATABASE_URL=postgresql://admin:DevPass123@db:5432/appdb

EXPOSE 8000

CMD ["python", "app.py"]