# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9.26

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/gpumon-venv \
    UV_PYTHON_DOWNLOADS=never

COPY --from=uv /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY web ./web

RUN uv sync --frozen --no-dev --no-cache

FROM ${PYTHON_IMAGE} AS runtime

ARG APP_UID=1000
ARG APP_GID=1000

RUN apt-get update \
    && apt-get install --no-install-recommends --yes openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid "${APP_GID}" gpumon \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" \
        --create-home --home-dir /home/gpumon --shell /usr/sbin/nologin gpumon \
    && install -d -m 0755 /state/config \
    && install -d -m 0750 -o gpumon -g gpumon /state/data \
    && install -d -m 0700 -o gpumon -g gpumon /home/gpumon/.ssh

ENV GPUMON_ROOT=/state \
    HOME=/home/gpumon \
    PATH=/opt/gpumon-venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /opt/gpumon-venv /opt/gpumon-venv
COPY --from=builder /app /app

USER gpumon:gpumon

EXPOSE 8848
STOPSIGNAL SIGINT

ENTRYPOINT ["gpumon"]
CMD ["web", "--host", "0.0.0.0", "--port", "8848"]
