FROM docker.io/library/python@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ARG TARGETARCH
WORKDIR /p1
COPY requirements/linux-aarch64.lock requirements/linux-x86_64.lock /p1/requirements/
RUN case "$TARGETARCH" in \
        arm64) lock=requirements/linux-aarch64.lock ;; \
        amd64) lock=requirements/linux-x86_64.lock ;; \
        *) printf 'Unsupported TARGETARCH: %s\n' "$TARGETARCH" >&2; exit 1 ;; \
    esac && \
    cp "$lock" requirements/platform.lock && \
    python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: -r requirements/platform.lock && python -m pip check
COPY requirements/legacy-plugin.lock /p1/requirements/
RUN python -m venv /opt/legacy && \
    grep -v '^temporalio-langgraph==' requirements/platform.lock > /tmp/legacy.lock && \
    cat requirements/legacy-plugin.lock >> /tmp/legacy.lock && \
    /opt/legacy/bin/python -m pip --isolated install --no-cache-dir --require-hashes --only-binary=:all: -r /tmp/legacy.lock && \
    /opt/legacy/bin/python -m pip check && rm /tmp/legacy.lock
RUN useradd -m -u 10101 probe && mkdir /evidence && chown probe:probe /evidence
COPY src src
COPY tests tests
ENV PYTHONPATH=/p1/src PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
USER probe
