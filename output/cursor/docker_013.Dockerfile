FROM python:3.11-slim

WORKDIR /app

COPY . /app

COPY /uploads /app/uploads

RUN pip install --no-cache-dir -r requirements.txt || true

CMD ["python", "process_files.py"]