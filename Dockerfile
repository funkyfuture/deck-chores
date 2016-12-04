FROM python:3.6.0b4-alpine

LABEL org.label-schema.schema-version="1.0" \
      org.label-schema.description="Job scheduler for Docker containers, configured via container labels." \
      org.label-schema.name="deck-chores" \
      org.label-schema.usage="/src/docs/usage.rst" \
      org.label-schema.vcs-url="https://github.com/funkyfuture/deck-chores" \
      org.label-schema.version="0.1.beta1"
      # TODO https://github.com/docker/hub-feedback/issues/508#issuecomment-243968310
      # TODO docker.cmd, docker.params, docker.debug

ENTRYPOINT ["dumb-init", "--"]
CMD ["deck-chores"]

COPY . /src

RUN apk add --no-cache --virtual .build-deps ca-certificates build-base \
 && pip install dumb-init \
 && /src/setup.py install \
 && rm -Rf /root/.cache \
 && apk del .build-deps
