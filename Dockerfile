FROM python:3.6.0b4-alpine

ARG BUILD_DATE
ARG COMMIT
ARG VERSION

LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.description="Job scheduler for Docker containers, configured via container labels." \
      org.label-schema.name="deck-chores" \
      org.label-schema.usage="/src/docs/usage.rst" \
      org.label-schema.vcs-url="https://github.com/funkyfuture/deck-chores" \
      org.label-schema.vcs-ref=$COMMIT \
      org.label-schema.version=$VERSION
      # TODO docker.cmd, docker.params, docker.debug

ENTRYPOINT ["dumb-init", "--"]
CMD ["deck-chores"]

COPY . /src

RUN apk add --no-cache --virtual .build-deps ca-certificates build-base \
 && pip install dumb-init \
 && cd src && python setup.py install \
 && cd /root && rm -Rf .cache \
 && apk del .build-deps
