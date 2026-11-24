# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.14-alpine3.23
ARG FLYWAYDB_VERSION=9.20-alpine

# Base image
FROM python:${PYTHON_VERSION} AS api

ARG PULUMI_VERSION=3.266.0

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8 \
    TZ=UTC \
    SLACK_TRIGGER="off" \
    LISTEN_ADDR="0.0.0.0" \
    PATH="/root/.pulumi/bin:${PATH}" \
    WAIT_TIME=10 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore \
    TRIVY_DISABLE_VEX_NOTICE=true

WORKDIR /app

# System packages (rarely change, kept in their own cached layer)
RUN apk add --no-cache gcc python3-dev --virtual .build-deps && \
    apk add --no-cache bash tzdata git curl libpq-dev musl-dev linux-headers libx11 xvfb libxrender libxext fontconfig && \
    echo "https://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories && \
    echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    apk update && \
    apk upgrade && \
    apk add --no-cache sqlite-libs xz-libs --upgrade || true

# Pulumi CLI and providers plugins (in parallel)
RUN curl -fsSL https://get.pulumi.com | sh -s -- --version "${PULUMI_VERSION}" && \
    rm -rf /root/.pulumi/plugins/* && \
    for plugin in aws gcp openstack ovh scaleway cloudflare; do \
      (pulumi plugin install resource "${plugin}" --exact || echo "[warn] pulumi plugin ${plugin} not installed") & \
    done; \
    wait

COPY ./requirements.txt /app/requirements.txt

# Python dependencies: uv installs wheels in parallel (much faster than pip)
RUN --mount=type=cache,target=/root/.cache/uv \
    pip install --no-cache-dir --upgrade pip uv && \
    uv pip install -r requirements.txt && \
    apk del .build-deps

COPY . /app/

EXPOSE 5000

CMD ["python", "src/app.py"]

# Scheduler image
FROM api AS scheduler

CMD ["python", "src/scheduler.py"]

# Consumer image
FROM api AS consumer

RUN mkdir -p /functions && \
    apk add --no-cache nodejs jq && \
    wget https://go.dev/dl/go1.23.4.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.23.4.linux-amd64.tar.gz && \
    rm go1.23.4.linux-amd64.tar.gz

ENV PATH="/usr/local/go/bin:${PATH}"

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

RUN pip install --no-cache-dir bandit

COPY ./bandit.yml /app/bandit.yml

CMD ["bandit", "-c", "/app/bandit.yml", "-r", ".", "-f", "screen"]
