ARG PYTHON_VERSION=3.13.1-alpine3.21
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
    WAIT_TIME=10 \
    TRIVY_DISABLE_VEX_NOTICE=true

WORKDIR /app

RUN apk add --no-cache gcc python3-dev --virtual .build-deps && \
    apk add --no-cache bash tzdata git curl libpq-dev musl-dev linux-headers libx11 xvfb libxrender libxext fontconfig && \
    echo "https://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories && \
    echo "https://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    apk update && \
    apk upgrade && \
    apk add --no-cache sqlite-libs xz-libs --upgrade || true && \
    curl -fsSL https://get.pulumi.com | PULUMI_VERSION=v3.170.0 sh && \
    rm -rf /root/.pulumi/plugins/* || true && \
    /root/.pulumi/bin/pulumi plugin install resource aws --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource azure-native --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource gcp --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource openstack --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource ovh --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource scaleway --exact || true && \
    /root/.pulumi/bin/pulumi plugin install resource cloudflare --exact || true

COPY ./requirements.txt /app/requirements.txt

RUN find . -name '*.pyc' -type f -delete && \
    pip install --upgrade pip && \
    pip install --no-cache-dir --force-reinstall "Pillow>=11.3.0" && \
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
