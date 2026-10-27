# Lenguajes del navegador, fuera del contenedor que guarda las claves.
# La red de este servicio es interna: no hay salida en marcha. Node, Java y
# .NET se instalan aquí, durante la construcción.
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/traza \
    HOME=/tmp \
    TRAZA_RUNTIME_DIR=/opt/traza-runtimes \
    TRAZA_RUNTIME_MANIFEST=/opt/traza/deploy/runtimes/manifest.json \
    TRAZA_LANGUAGE_BIND=0.0.0.0 \
    TRAZA_LANGUAGE_PORT=8766

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10003 --create-home --shell /usr/sbin/nologin languages

WORKDIR /opt/traza

COPY language_core ./language_core
COPY runner ./runner
COPY local_host ./local_host
COPY deploy/runtimes/manifest.json ./deploy/runtimes/manifest.json
COPY deploy/language-runtimes.py ./deploy/language-runtimes.py

RUN python deploy/language-runtimes.py \
    && chown -R languages:languages /opt/traza-runtimes

USER languages

EXPOSE 8766

CMD ["python", "-m", "local_host.browser_host"]
