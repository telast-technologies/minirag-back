FROM python:3.12-slim AS python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

FROM python-base AS python-build-stage

ARG BUILD_ENV=local

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    postgresql-client \
    gettext \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY pyproject.toml uv.lock ./

RUN uv venv /opt/venv && \
    uv sync --frozen --no-install-project --group dev

COPY . /build

RUN uv sync --frozen --group dev

FROM python-base AS python-run-stage

ARG BUILD_ENV=local
ARG APP_HOME=/app

ENV BUILD_ENV=${BUILD_ENV}

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install --no-install-recommends -y \
    bash \
    curl \
    git \
    nano \
    bash-completion \
    ssh \
    sudo \
    libpq5 \
    postgresql-client \
    gettext \
 && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 dev-user \
 && useradd --uid 1000 --gid dev-user --shell /bin/bash --create-home dev-user \
 && mkdir -p /etc/sudoers.d \
 && echo 'dev-user ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/dev-user \
 && chmod 0440 /etc/sudoers.d/dev-user

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY --from=python-build-stage /opt/venv /opt/venv
RUN chown -R dev-user:dev-user /opt/venv

COPY ./docker/fastapi/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//g' /entrypoint.sh && chmod +x /entrypoint.sh

COPY ./docker/fastapi/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

COPY . ${APP_HOME}
RUN chown -R dev-user:dev-user ${APP_HOME}


# -------------------------------------------------------------------
# celery worker, beat, and flower entrypoint scripts
# -------------------------------------------------------------------

COPY ./docker/fastapi/celery/worker/start /start-celeryworker
RUN sed -i 's/\r$//g' /start-celeryworker \
    && chmod +x /start-celeryworker

COPY ./docker/fastapi/celery/beat/start /start-celerybeat
RUN sed -i 's/\r$//g' /start-celerybeat \
    && chmod +x /start-celerybeat

COPY ./docker/fastapi/celery/flower/start /start-flower
RUN sed -i 's/\r$//g' /start-flower \
    && chmod +x /start-flower


USER dev-user

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/start"]
