FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /opt/traza

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gcc g++ libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY language_core ./language_core
COPY runner ./runner
COPY server ./server

RUN pip install --no-cache-dir -e ".[server]"

COPY deploy/web-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /opt/traza/server
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
