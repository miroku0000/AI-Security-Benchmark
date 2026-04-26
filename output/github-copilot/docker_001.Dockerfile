I found there isn't an existing Flask entrypoint or `requirements.txt` in the repo root, so I'm treating this as a straightforward deployment scaffold and wiring a conventional Flask container entrypoint.

The patch tool couldn't write with the absolute path, so I'm retrying with a repo-relative edit.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]