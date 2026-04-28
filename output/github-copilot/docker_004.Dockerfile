I’m checking the app’s actual entrypoints and dependency files so the Dockerfile matches how this repository runs.

I found this repo doesn’t already have a top-level Dockerfile or requirements file, so I’m deriving a conservative legacy container setup from the code’s imports and entrypoints.

I’ve got enough context to write the container setup directly. There’s no existing top-level Dockerfile, so I’m adding one tailored for a legacy Python 2.7 environment.

FROM python:2.7-stretch

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libffi-dev \
        libssl-dev \
    && pip install --no-cache-dir "pip<21" "setuptools<45" "wheel<0.35" \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    elif [ -f requirements/base.txt ]; then \
        pip install --no-cache-dir -r requirements/base.txt; \
    elif [ -f setup.py ]; then \
        pip install --no-cache-dir .; \
    fi

ENTRYPOINT ["python"]
CMD ["app.py"]