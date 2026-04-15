FROM python:2.7-slim-stretch

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    make \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade "pip<21" "setuptools<45" "wheel<0.35"

COPY . /app

RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

CMD ["python"]