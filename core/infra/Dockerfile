FROM docker.io/library/python@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4
WORKDIR /mingjing
COPY requirements/linux-x86_64.lock ./requirements/
RUN python -m pip --isolated --disable-pip-version-check install --require-hashes --only-binary=:all: -r requirements/linux-x86_64.lock \
    && python -m pip check
RUN useradd -m -u 10101 mingjing && install -d -o mingjing -g mingjing /artifacts /evidence
COPY src src
COPY migrations migrations
COPY tests tests
ENV PYTHONPATH=/mingjing/src PYTHONDONTWRITEBYTECODE=1 PYTEST_ADDOPTS="-p no:cacheprovider"
USER mingjing
