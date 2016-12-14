FROM python:3.6.0rc1-alpine

MAINTAINER Frank Sachsenheim <funkyfuture@riseup.net>

ARG VERSION
ARG SOURCE_COMMIT
ARG BUILD_DATE

LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.description="Job scheduler for Docker containers, configured via labels." \
      org.label-schema.name="deck-chores" \
      org.label-schema.version=$VERSION \
      org.label-schema.usage="/src/docs/usage.rst" \
      org.label-schema.url="http://deck-chores.rtfd.io" \
      org.label-schema.docker.cmd="docker run --rm -d -v /var/run/docker.sock:/var/run/docker.sock funkyfuture/deck-chores" \
      org.label-schema.docker.cmd.debug="docker run --rm -d -e DEBUG=on -v /var/run/docker.sock:/var/run/docker.sock funkyfuture/deck-chores" \
      org.label-schema.vcs-url="https://github.com/funkyfuture/deck-chores" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-ref=$SOURCE_COMMIT

ENTRYPOINT ["dumb-init", "--"]
CMD ["deck-chores"]

COPY . /src

RUN apk add --no-cache --virtual .build-deps ca-certificates build-base \
 && pip install dumb-init \
 && /src/setup.py install \
 && rm -Rf /root/.cache \
 && apk del .build-deps
