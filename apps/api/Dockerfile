FROM python:3.14.7-alpine@sha256:c6ead215bfd31f1e433d968853b7a769989117115b728874824e6c0a27cb96fc AS dependencies
ENV POLARS_MAX_THREADS=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apk add --no-cache libuuid=2.42.3-r1 libcrypto3=3.5.8-r0 libssl3=3.5.8-r0
WORKDIR /app
COPY apps/api/requirements.lock /app/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock
COPY apps/api/src /app/src
COPY apps/api/alembic.ini /app/alembic.ini
COPY apps/api/migrations /app/migrations
ENV PYTHONPATH=/app/src
RUN addgroup -g 10001 platform && adduser -D -u 10001 -G platform platform
RUN mkdir /work && chown 10001:10001 /work
USER 10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "platform_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

FROM dependencies AS test
USER root
COPY apps/api/requirements-test.lock /app/requirements-test.lock
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-test.lock
COPY apps/api/tests /app/tests
COPY apps/api/pyproject.toml /app/pyproject.toml
USER 10001
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "/app/tests"]

# Der Laufzeitcontainer benötigt weder Paketinstallation noch ensurepip-Wheels.
# Der getrennte Test-Stage behält seine gesperrten Testabhängigkeiten.
FROM dependencies AS base
USER root
RUN python -m pip uninstall -y pip \
    && python -c "import shutil; shutil.rmtree('/usr/local/lib/python3.14/ensurepip')"
USER 10001
