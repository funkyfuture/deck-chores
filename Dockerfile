FROM docker.io/python:3.9-alpine

MAINTAINER Frank Sachsenheim <funkyfuture@riseup.net>

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
