FROM python:alpine3.8

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["deck-chores"]
LABEL org.label-schema.name="deck-chores"
ENV DEBUG=true

RUN apk add --no-cache tini \
 && pip install cerberus~=1.1 docker~=2.4 fasteners~=0.14 APScheduler~=3.3

COPY . /src

RUN python /src/setup.py install
