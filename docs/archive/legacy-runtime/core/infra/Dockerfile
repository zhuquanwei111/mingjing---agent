# Fixed multi-platform index; its amd64 child is the previous P2 image.
FROM docker.io/library/python@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ARG TARGETARCH
WORKDIR /mingjing
COPY requirements/linux-aarch64.lock requirements/linux-x86_64.lock ./requirements/
RUN case "$TARGETARCH" in \
        arm64) lock=requirements/linux-aarch64.lock ;; \
        amd64) lock=requirements/linux-x86_64.lock ;; \
        *) printf 'Unsupported TARGETARCH: %s\n' "$TARGETARCH" >&2; exit 1 ;; \
    esac && \
    python -m pip --isolated --disable-pip-version-check install --require-hashes --only-binary=:all: -r "$lock" \
    && python -m pip check
RUN useradd -m -u 10101 mingjing && install -d -o mingjing -g mingjing /artifacts /evidence
COPY src src
COPY migrations migrations
COPY tests tests
ENV PYTHONPATH=/mingjing/src PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
USER mingjing
