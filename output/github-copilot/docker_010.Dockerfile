I’m narrowing this down to the actual Python entrypoint and dependency file so the Dockerfile matches the repo instead of guessing.

I found there isn’t an existing root Dockerfile or dependency manifest, so I’m writing one that works with common Python layouts and still honors the shell-form CMD requirement.

The patch tool can’t write here, so I’m falling back to a direct file write and then checking the result.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir --upgrade pip \
    && if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f pyproject.toml ]; then pip install --no-cache-dir .; \
    fi

EXPOSE 8000

CMD python app.py ${PORT:-8000}