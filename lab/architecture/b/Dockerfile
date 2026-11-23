FROM docker.io/library/python@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4
WORKDIR /lab
COPY linux-amd64.lock /tmp/
RUN python -m pip install --require-hashes --only-binary=:all: --report /opt/installed.json -r /tmp/linux-amd64.lock && python -m pip check
USER 10102:10102

