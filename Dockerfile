ARG PYTHON_VERSION=3.13.1-alpine
ARG FLYWAYDB_VERSION=9.20-alpine

# Base image
FROM python:${PYTHON_VERSION} as api

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    TZ=UTC \
    SLACK_TRIGGER="off" \
    LISTEN_ADDR="0.0.0.0" \
    PATH="/root/.pulumi/bin:${PATH}" \
    WAIT_TIME=10

WORKDIR /app

RUN apk add --no-cache gcc python3-dev --virtual .build-deps && \
    apk add --no-cache bash tzdata git curl libpq-dev musl-dev linux-headers && \
    curl -fsSL https://get.pulumi.com | sh

COPY ./requirements.txt /app/requirements.txt

RUN find . -name '*.pyc' -type f -delete && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps && \
    rm -rf *.tgz

COPY . /app/

EXPOSE 5000

CMD ["python", "src/app.py"]

# Scheduler image
FROM api as scheduler

CMD ["python", "src/scheduler.py"]

# Consumer image
FROM api as consumer

RUN mkdir -p /functions && \
    apk add --no-cache nodejs go jq

CMD ["python", "src/consumer.py"]

# Unit tests image
FROM api AS unit_tests

WORKDIR /app/src

CMD ["python", "-m", "unittest", "discover", "-s", "./tests", "-p", "test_*.py", "-v"]

# Linter image
FROM api AS linter

WORKDIR /app/src

CMD ["ruff", "check", "--fix", "."]

# Scan image
FROM api AS code_scanner

WORKDIR /app/src

RUN pip install bandit

CMD ["bandit", "-r", ".", "-f", "screen"]
