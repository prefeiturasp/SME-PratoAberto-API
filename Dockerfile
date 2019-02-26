FROM python:3.6-alpine3.8
ADD . /code
WORKDIR /code
RUN python -m pip --no-cache install -r requirements.txt


RUN apk update && apk add --no-cache \
      --virtual=.build-dependencies \
      gcc \
      musl-dev \
      postgresql-dev \
      git \
      python3-dev && \
    python -m pip --no-cache install -U pip && \
    python -m pip --no-cache install -r requirements.txt && \
    apk del --purge .build-dependencies