FROM python:3.9-alpine

MAINTAINER Frank Sachsenheim <funkyfuture@riseup.net>

ARG VERSION
ARG SOURCE_COMMIT
ARG BUILD_DATE

LABEL org.opencontainers.image.created=$BUILD_DATE \
      org.opencontainers.image.description="Job scheduler for Docker containers, configured via labels." \
      org.opencontainers.image.documentation="https://deck-chores.readthedocs.org/" \
      org.opencontainers.image.revision=$SOURCE_COMMIT \
      org.opencontainers.image.source="https://github.com/funkyfuture/deck-chores" \
      org.opencontainers.image.title="deck-chores" \
      org.opencontainers.image.version=$VERSION

CMD ["deck-chores"]
ENV PYTHONOPTIMIZE=1
# could be 2 with Cerberus 2

COPY . /src

RUN apk upgrade --no-cache \
 && apk add --no-cache --virtual .build-deps build-base cargo ca-certificates libffi-dev musl-dev openssl-dev python3-dev \
 && apk add --no-cache tzdata \
 && echo "UTC" > /etc/timezone \
 && cd /src \
 && pip install --no-cache-dir /src \
 && rm -rf /root/.cache \
 && apk del .build-deps
