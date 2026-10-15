FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/opt/traza \
    HOME=/tmp

WORKDIR /opt/traza

COPY pyproject.toml README.md ./
COPY language_core ./language_core
COPY runner ./runner

RUN pip install --no-cache-dir redis \
    && pip install --no-cache-dir --no-deps . \
    && useradd --uid 10002 --create-home --shell /usr/sbin/nologin runner

USER runner
CMD ["python", "-m", "runner"]
